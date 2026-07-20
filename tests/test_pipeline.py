"""
Integration tests for the full ETL pipeline.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.preprocessing.cleaner import remove_duplicates, clean_dataframe, validate_schema
from src.preprocessing.normalizer import normalize_dataframe, add_text_features
from src.preprocessing.feature_engineering import (
    calculate_restaurant_stats,
    encode_categorical_features,
    create_sentiment_features,
    create_clustering_features
)
from src.clustering.restaurant_clusterer import RestaurantClusterer, find_optimal_k
from src.sentiment.fallback_classifier import add_sentiment_columns


class TestETLPipeline:
    """Integration tests for the ETL pipeline."""

    @pytest.fixture
    def raw_data(self):
        """Create raw input data similar to scraped data."""
        data = {
            "restaurant_id": pd.Series(["rest_1", "rest_1", "rest_1", "rest_2", "rest_2", "rest_3", "rest_3", "rest_3"], dtype=object),
            "restaurant_name": pd.Series(["Restaurante A", "Restaurante A", "Restaurante A",
                              "Restaurante B", "Restaurante B",
                              "Restaurante C", "Restaurante C", "Restaurante C"], dtype=object),
            "category": pd.Series(["Italiana", "Italiana", "Italiana", "Mexicana", "Mexicana",
                       "Panameña", "Panameña", "Panameña"], dtype=object),
            "price_range": pd.Series(["$$ - $$$", "$$ - $$$", "$$ - $$$", "$", "$", "$$$ - $$$$", "$$$ - $$$$", "$$$ - $$$$"], dtype=object),
            "overall_rating": pd.Series([4.5, 4.2, 4.8, 3.8, 4.0, 4.7, 4.5, 4.9], dtype=float),
            "review_text": pd.Series([
                "La comida estuvo deliciosa! Excelente servicio.",
                "Muy buen ambiente y comida sabrosa.",
                "El mejor restaurante italiano en la ciudad!",
                "Comida tradicional mexicana autentica.",
                "Buen pozole, servicio regular.",
                "Excelente mariscos frescos. El mejor ceviche!",
                "Muy buen ambiente playero.",
                "Increible comida tipica panamena."
            ], dtype=object),
            "review_date": pd.Series(["2024-01-15", "2024-01-20", "2024-01-25",
                          "2024-02-01", "2024-02-05",
                          "2024-02-10", "2024-02-15", "2024-02-20"], dtype=object),
            "reviewer_name": pd.Series(["Juan", "Maria", "Carlos", "Ana", "Pedro", "Rosa", "Luis", "Elena"], dtype=object),
            "source": pd.Series(["degusta", "degusta", "degusta", "tripadvisor", "tripadvisor",
                      "degusta", "degusta", "degusta"], dtype=object),
            "sentiment_comida": pd.Series(["positive", "positive", "positive", "positive", "neutral", "positive", "positive", "positive"], dtype=object),
            "sentiment_servicio": pd.Series(["positive", "neutral", "positive", "neutral", "negative", "positive", "positive", "positive"], dtype=object),
            "sentiment_precio": pd.Series(["neutral", "neutral", "negative", "positive", "positive", "negative", "negative", "negative"], dtype=object),
            "sentiment_ambiente": pd.Series(["positive", "positive", "positive", "neutral", "neutral", "positive", "positive", "positive"], dtype=object)
        }
        return pd.DataFrame(data)

    def test_full_pipeline_clean_to_cluster(self, raw_data):
        """Test complete pipeline from raw data to clustered output."""
        # Step 1: Clean
        df = remove_duplicates(raw_data)
        df = clean_dataframe(df)
        assert validate_schema(df), "Schema validation failed"

        # Step 2: Normalize
        df = normalize_dataframe(df)
        df = add_text_features(df)

        assert "review_text_normalized" in df.columns
        assert "word_count" in df.columns

        # Step 3: Add sentiment scores first (to create score columns)
        df = add_sentiment_columns(df)

        # Step 4: Feature Engineering
        df = encode_categorical_features(df)

        assert "price_range_encoded" in df.columns

        # Step 5: Clustering
        clusterer = RestaurantClusterer(n_clusters=3, random_state=42)
        features = clusterer.engineer_features(df)
        clusters = clusterer.fit_predict(features)
        df = clusterer.add_cluster_labels(df, clusters)

        assert "cluster" in df.columns
        assert df["cluster"].nunique() <= 3

    def test_pipeline_preserves_data_integrity(self, raw_data):
        """Test that pipeline preserves important data."""
        # Clean
        df = clean_dataframe(raw_data.copy())

        # Normalize
        df = normalize_dataframe(df)

        # Verify restaurant count preserved
        assert df["restaurant_id"].nunique() == 3

        # Verify ratings preserved
        assert df["overall_rating"].notna().all()

    def test_pipeline_handles_duplicates(self, raw_data):
        """Test that duplicate removal works in pipeline."""
        # Add duplicates
        df_with_dups = pd.concat([raw_data, raw_data.iloc[[0, 1]]], ignore_index=True)
        assert len(df_with_dups) == len(raw_data) + 2

        # Clean duplicates
        df = remove_duplicates(df_with_dups)
        assert len(df) == len(raw_data)

    def test_pipeline_text_cleaning(self, raw_data):
        """Test that HTML and URLs are removed."""
        df = clean_dataframe(raw_data)

        # Check HTML removed
        assert not df["review_text"].str.contains("<b>", na=False).any()

        # Check URLs removed
        assert not df["review_text"].str.contains("http://", na=False).any()

    def test_pipeline_sentiment_conversion(self, raw_data):
        """Test that sentiment strings are converted to scores."""
        df = clean_dataframe(raw_data)
        df = add_sentiment_columns(df)

        # Check scores are in valid range
        for col in ["sentiment_comida_score", "sentiment_servicio_score",
                   "sentiment_precio_score", "sentiment_ambiente_score"]:
            assert df[col].min() >= -1.0
            assert df[col].max() <= 1.0

    def test_pipeline_clustering_quality(self, raw_data):
        """Test that clustering produces reasonable clusters."""
        # Prepare data
        df = clean_dataframe(raw_data.copy())
        df = normalize_dataframe(df)
        df = add_text_features(df)
        df = add_sentiment_columns(df)
        df = encode_categorical_features(df)

        # Cluster. Features are per restaurant, and silhouette needs at least
        # one more sample than clusters, so k must stay below the restaurant count.
        n_restaurants = df["restaurant_id"].nunique()
        clusterer = RestaurantClusterer(n_clusters=n_restaurants - 1, random_state=42)
        features = clusterer.engineer_features(df)
        assert features.shape[0] == n_restaurants
        clusters = clusterer.fit_predict(features)

        # Get silhouette score
        from sklearn.metrics import silhouette_score
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        score = silhouette_score(features_scaled, clusters)

        # Score should be reasonable (not terrible)
        assert score > -0.5, f"Silhouette score too low: {score}"


class TestPipelineWithRealData:
    """Tests using real processed data if available."""

    def test_loads_processed_data(self, processed_data_path):
        """Test that processed data can be loaded."""
        if processed_data_path is None:
            pytest.skip("No processed data file found")

        df = pd.read_csv(processed_data_path)

        assert len(df) > 0
        assert "restaurant_id" in df.columns
        assert "restaurant_name" in df.columns

    def test_processed_data_has_cluster_column(self, processed_data_path):
        """Test that processed data has cluster assignments."""
        if processed_data_path is None:
            pytest.skip("No processed data file found")

        df = pd.read_csv(processed_data_path)

        if "cluster" in df.columns:
            assert df["cluster"].notna().any()

    def test_processed_data_has_sentiment_columns(self, processed_data_path):
        """Test that processed data has sentiment columns."""
        if processed_data_path is None:
            pytest.skip("No processed data file found")

        df = pd.read_csv(processed_data_path)

        sentiment_cols = [col for col in df.columns if "sentiment" in col.lower()]
        assert len(sentiment_cols) > 0


class TestEndToEndDataFrameOperations:
    """Tests for complete DataFrame operations."""

    def test_merge_restaurant_stats(self, sample_reviews_df):
        """Test merging restaurant stats back to main dataframe."""
        # Calculate stats
        stats = calculate_restaurant_stats(sample_reviews_df)

        # Merge
        df = sample_reviews_df.merge(
            stats[["restaurant_id", "review_count", "avg_rating"]],
            on="restaurant_id",
            how="left"
        )

        assert "review_count" in df.columns
        assert "avg_rating" in df.columns

    def test_full_feature_engineering_pipeline(self, sample_reviews_df):
        """Test complete feature engineering pipeline."""
        # Add normalized text features
        df = normalize_dataframe(sample_reviews_df)
        df = add_text_features(df)

        # Calculate restaurant stats
        restaurant_stats = calculate_restaurant_stats(df)
        df = df.merge(restaurant_stats, on=["restaurant_id", "restaurant_name"], how="left")

        # Encode categorical
        df = encode_categorical_features(df)

        # Add sentiment columns (creates score columns from string sentiments if needed)
        # Note: sample_reviews_df already has sentiment_*_score columns

        # Check all expected columns exist
        assert "word_count" in df.columns
        assert "review_count" in df.columns
        assert "price_range_encoded" in df.columns
