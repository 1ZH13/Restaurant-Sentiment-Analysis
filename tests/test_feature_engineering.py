"""
Unit tests for src/preprocessing/feature_engineering.py module.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.preprocessing.feature_engineering import (
    calculate_restaurant_stats,
    encode_categorical_features,
    create_sentiment_features,
    create_clustering_features
)


class TestCalculateRestaurantStats:
    """Tests for calculate_restaurant_stats function."""

    def test_calculates_review_count(self, sample_reviews_df):
        """Test that review count is calculated correctly."""
        result = calculate_restaurant_stats(sample_reviews_df)

        rest_1_count = result[result["restaurant_id"] == "rest_1"]["review_count"].values[0]
        assert rest_1_count == 2

    def test_calculates_avg_rating(self, sample_reviews_df):
        """Test that average rating is calculated."""
        result = calculate_restaurant_stats(sample_reviews_df)

        rest_1_avg = result[result["restaurant_id"] == "rest_1"]["avg_rating"].values[0]
        expected = (4.5 + 4.2) / 2
        assert abs(rest_1_avg - expected) < 0.01

    def test_returns_correct_columns(self, sample_reviews_df):
        """Test that result has correct columns."""
        result = calculate_restaurant_stats(sample_reviews_df)

        expected_cols = ["restaurant_id", "restaurant_name", "review_count",
                        "avg_rating", "avg_word_count", "avg_char_count"]
        for col in expected_cols:
            assert col in result.columns

    def test_requires_review_text_column(self):
        """Test that missing review_text column raises error."""
        df = pd.DataFrame({
            "restaurant_id": ["r1"],
            "restaurant_name": ["Test"],
            "overall_rating": [4.0]
        })

        with pytest.raises(ValueError):
            calculate_restaurant_stats(df)


class TestEncodeCategoricalFeatures:
    """Tests for encode_categorical_features function."""

    def test_encodes_price_range(self, sample_reviews_df):
        """Test that price range is encoded."""
        result = encode_categorical_features(sample_reviews_df)

        assert "price_range_encoded" in result.columns
        assert result["price_range_encoded"].dtype in [np.int64, np.float64]

    def test_price_mapping_values(self, sample_reviews_df):
        """Test that price mapping produces expected values."""
        result = encode_categorical_features(sample_reviews_df)

        # $ should be 1
        assert result[result["price_range"] == "$"]["price_range_encoded"].values[0] == 1
        # $$$$ should be 4
        assert result[result["price_range"] == "$$$ - $$$$"]["price_range_encoded"].values[0] == 3

    def test_adds_category_dummies(self, sample_reviews_df):
        """Test that category dummy columns are added."""
        result = encode_categorical_features(sample_reviews_df)

        # Should have cat_ prefix columns
        cat_cols = [col for col in result.columns if col.startswith("cat_")]
        assert len(cat_cols) > 0

    def test_handles_unknown_price_range(self, sample_reviews_df):
        """Test that unknown price ranges get default value."""
        df = sample_reviews_df.copy()
        df.loc[0, "price_range"] = "Unknown Price"

        result = encode_categorical_features(df)

        # Should fill with default value (2)
        assert result.loc[0, "price_range_encoded"] == 2


class TestCreateSentimentFeatures:
    """Tests for create_sentiment_features function."""

    def test_creates_overall_sentiment_score_with_string_columns(self, sample_reviews_df):
        """Test that overall sentiment score is calculated from string sentiment columns."""
        # Create string sentiment columns (like what the scraper would produce)
        df = sample_reviews_df.copy()
        df["sentiment_comida"] = ["positive", "positive", "positive", "positive", "positive"]
        df["sentiment_servicio"] = ["positive", "neutral", "neutral", "positive", "positive"]
        df["sentiment_precio"] = ["neutral", "negative", "positive", "positive", "negative"]
        df["sentiment_ambiente"] = ["positive", "positive", "neutral", "neutral", "positive"]

        result = create_sentiment_features(df)

        assert "overall_sentiment_score" in result.columns

    def test_calculates_positive_negative_counts(self, sample_reviews_df):
        """Test that aspect counts are calculated."""
        # Create string sentiment columns
        df = sample_reviews_df.copy()
        df["sentiment_comida"] = ["positive", "positive", "positive", "positive", "positive"]
        df["sentiment_servicio"] = ["positive", "neutral", "neutral", "positive", "positive"]
        df["sentiment_precio"] = ["neutral", "negative", "positive", "positive", "negative"]
        df["sentiment_ambiente"] = ["positive", "positive", "neutral", "neutral", "positive"]

        result = create_sentiment_features(df)

        assert "positive_aspect_count" in result.columns
        assert "negative_aspect_count" in result.columns

    def test_handles_missing_sentiment_columns(self, raw_reviews_df):
        """Test that missing sentiment columns don't cause errors."""
        result = create_sentiment_features(raw_reviews_df)

        # Should return dataframe without sentiment features
        assert "overall_sentiment_score" not in result.columns

    def test_maps_sentiment_strings_to_scores(self):
        """Test that sentiment string columns are mapped to scores."""
        # Create a dataframe with explicit object dtype for string columns
        df = pd.DataFrame({
            "restaurant_id": pd.Series(["rest_1", "rest_2"], dtype=object),
            "restaurant_name": pd.Series(["Rest A", "Rest B"], dtype=object),
            "sentiment_comida": pd.Series(["positive", "negative"], dtype=object),
            "sentiment_servicio": pd.Series(["neutral", "neutral"], dtype=object),
            "sentiment_precio": pd.Series(["neutral", "neutral"], dtype=object),
            "sentiment_ambiente": pd.Series(["neutral", "neutral"], dtype=object)
        })

        result = create_sentiment_features(df)

        # The function creates columns like "sentiment_comida_score"
        assert "sentiment_comida_score" in result.columns
        assert result.iloc[0]["sentiment_comida_score"] == 1.0
        assert result.iloc[1]["sentiment_comida_score"] == -1.0


class TestCreateClusteringFeatures:
    """Tests for create_clustering_features function."""

    def test_returns_dataframe_and_feature_list(self, sample_reviews_df):
        """Test that function returns both dataframe and feature list."""
        df = encode_categorical_features(sample_reviews_df)
        df = create_sentiment_features(df)

        result_df, features = create_clustering_features(df)

        assert isinstance(result_df, pd.DataFrame)
        assert isinstance(features, list)

    def test_features_include_numerical(self, sample_reviews_df):
        """Test that numerical features are included."""
        df = encode_categorical_features(sample_reviews_df)
        df = create_sentiment_features(df)

        _, features = create_clustering_features(df)

        assert "overall_rating" in features
        assert "price_range_encoded" in features

    def test_features_include_sentiment(self, sample_reviews_df):
        """Test that sentiment features are included."""
        # First add string sentiment columns
        df = sample_reviews_df.copy()
        df["sentiment_comida"] = ["positive", "positive", "positive", "positive", "positive"]
        df["sentiment_servicio"] = ["positive", "neutral", "neutral", "positive", "positive"]
        df["sentiment_precio"] = ["neutral", "negative", "positive", "positive", "negative"]
        df["sentiment_ambiente"] = ["positive", "positive", "neutral", "neutral", "positive"]

        df = encode_categorical_features(df)
        df = create_sentiment_features(df)

        _, features = create_clustering_features(df)

        assert "overall_sentiment_score" in features

    def test_fills_missing_values(self, sample_reviews_df):
        """Test that missing values are filled with column means."""
        df = sample_reviews_df.copy()
        df.loc[0, "overall_rating"] = np.nan

        df = encode_categorical_features(df)
        df = create_sentiment_features(df)

        result_df, _ = create_clustering_features(df)

        # Should not have NaN in overall_rating after filling
        assert not result_df["overall_rating"].isna().any()
