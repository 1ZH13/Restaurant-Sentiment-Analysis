"""
Unit tests for src/clustering/restaurant_clusterer.py module.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.clustering.restaurant_clusterer import (
    RestaurantClusterer,
    find_optimal_k,
    assign_cluster_names
)


class TestRestaurantClusterer:
    """Tests for RestaurantClusterer class."""

    @pytest.fixture
    def clusterer(self):
        """Create a clusterer instance."""
        return RestaurantClusterer(n_clusters=3, random_state=42)

    def test_init_default_values(self):
        """Test clusterer initialization with defaults."""
        clusterer = RestaurantClusterer()

        assert clusterer.n_clusters == 5
        assert clusterer.random_state == 42

    def test_init_custom_values(self):
        """Test clusterer initialization with custom values."""
        clusterer = RestaurantClusterer(n_clusters=3, random_state=123)

        assert clusterer.n_clusters == 3
        assert clusterer.random_state == 123

    def test_engineer_features_shape(self, clusterer, sample_reviews_df):
        """Feature matrix has one row per restaurant, not per review."""
        features = clusterer.engineer_features(sample_reviews_df)

        assert features.shape[0] == sample_reviews_df["restaurant_id"].nunique()
        assert features.shape[1] > 0

    def test_engineer_features_aggregates_reviews(self, clusterer, sample_reviews_df):
        """A restaurant with several reviews contributes a single row."""
        n_restaurants = sample_reviews_df["restaurant_id"].nunique()
        assert n_restaurants < len(sample_reviews_df), "fixture needs repeated restaurants"

        features = clusterer.engineer_features(sample_reviews_df)

        assert features.shape[0] == n_restaurants
        assert len(clusterer.restaurant_ids) == n_restaurants

    def test_engineer_features_includes_rating(self, clusterer, sample_reviews_df):
        """Test that rating features are included."""
        features = clusterer.engineer_features(sample_reviews_df)

        # Should have at least one feature
        assert features.shape[1] > 0

    def test_engineer_features_handles_missing_columns(self, clusterer):
        """Test that missing columns don't cause errors."""
        df = pd.DataFrame({
            "restaurant_id": ["r1", "r2"],
            "restaurant_name": ["Rest A", "Rest B"]
        })

        features = clusterer.engineer_features(df)
        # Should not crash even with missing columns
        assert isinstance(features, np.ndarray)

    def test_fit_predict_returns_clusters(self, clusterer, sample_reviews_df):
        """Test that fit_predict returns cluster assignments."""
        features = clusterer.engineer_features(sample_reviews_df)
        clusters = clusterer.fit_predict(features)

        assert len(clusters) == sample_reviews_df["restaurant_id"].nunique()
        assert all(0 <= c < clusterer.n_clusters for c in clusters)

    def test_fit_predict_consistent_results(self, clusterer, sample_reviews_df):
        """Test that fit_predict gives consistent results with same random_state."""
        features = clusterer.engineer_features(sample_reviews_df)

        clusters1 = clusterer.fit_predict(features)
        clusters2 = clusterer.fit_predict(features)

        assert np.array_equal(clusters1, clusters2)

    def test_get_cluster_profiles(self, clusterer, sample_reviews_df):
        """Test that cluster profiles are generated correctly."""
        features = clusterer.engineer_features(sample_reviews_df)
        clusters = clusterer.fit_predict(features)
        profiles = clusterer.get_cluster_profiles(sample_reviews_df, clusters)

        assert isinstance(profiles, dict)
        assert len(profiles) <= clusterer.n_clusters

    def test_get_cluster_profiles_has_count(self, clusterer, sample_reviews_df):
        """Test that profiles include count."""
        features = clusterer.engineer_features(sample_reviews_df)
        clusters = clusterer.fit_predict(features)
        profiles = clusterer.get_cluster_profiles(sample_reviews_df, clusters)

        for cluster_id, profile in profiles.items():
            assert "count" in profile

    def test_add_cluster_labels(self, clusterer, sample_reviews_df):
        """Restaurant-level labels are mapped back onto every review."""
        features = clusterer.engineer_features(sample_reviews_df)
        clusters = clusterer.fit_predict(features)
        result = clusterer.add_cluster_labels(sample_reviews_df, clusters)

        assert "cluster" in result.columns
        assert len(result) == len(sample_reviews_df)
        assert result["cluster"].notna().all()

    def test_cluster_is_consistent_per_restaurant(self, clusterer, sample_reviews_df):
        """Every review of a restaurant carries that restaurant's cluster."""
        features = clusterer.engineer_features(sample_reviews_df)
        clusters = clusterer.fit_predict(features)
        result = clusterer.add_cluster_labels(sample_reviews_df, clusters)

        per_restaurant = result.groupby("restaurant_id")["cluster"].nunique()
        assert (per_restaurant == 1).all()


class TestFindOptimalK:
    """Tests for find_optimal_k function."""

    def test_returns_tuple(self, sample_reviews_df):
        """Test that function returns tuple of (k, score)."""
        clusterer = RestaurantClusterer(n_clusters=5)
        features = clusterer.engineer_features(sample_reviews_df)

        result = find_optimal_k(features, k_range=range(2, 4))

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], (int, np.integer))
        assert isinstance(result[1], (float, np.floating))

    def test_k_in_range(self, sample_reviews_df):
        """Test that returned k is in the tested range."""
        clusterer = RestaurantClusterer(n_clusters=5)
        features = clusterer.engineer_features(sample_reviews_df)

        best_k, _ = find_optimal_k(features, k_range=range(2, 4))

        assert 2 <= best_k <= 3

    def test_silhouette_score_reasonable(self, sample_reviews_df):
        """Test that silhouette score is in valid range."""
        clusterer = RestaurantClusterer(n_clusters=5)
        features = clusterer.engineer_features(sample_reviews_df)

        _, score = find_optimal_k(features, k_range=range(2, 4))

        assert -1 <= score <= 1


class TestAssignClusterNames:
    """Tests for assign_cluster_names function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        profiles = {
            0: {"avg_rating": 4.5, "avg_comida_sentiment": 0.8, "avg_servicio_sentiment": 0.7},
            1: {"avg_rating": 3.0, "avg_comida_sentiment": 0.2, "avg_servicio_sentiment": 0.1}
        }

        result = assign_cluster_names(profiles)

        assert isinstance(result, dict)
        assert len(result) == 2

    def test_names_are_unique(self):
        """Names describe what sets a cluster apart, so they must not repeat.

        The previous threshold-based naming labelled 4 of 5 clusters
        "Premium Fine Dining", which told the reader nothing.
        """
        profiles = {
            0: {"avg_rating": 4.9, "avg_price_level": 4.0, "avg_comida_sentiment": 0.9,
                "avg_servicio_sentiment": 0.8, "avg_ambiente_sentiment": 0.7, "review_count": 10},
            1: {"avg_rating": 4.7, "avg_price_level": 3.5, "avg_comida_sentiment": 0.8,
                "avg_servicio_sentiment": 0.9, "avg_ambiente_sentiment": 0.6, "review_count": 40},
            2: {"avg_rating": 4.6, "avg_price_level": 1.2, "avg_comida_sentiment": 0.5,
                "avg_servicio_sentiment": 0.4, "avg_ambiente_sentiment": 0.9, "review_count": 15},
        }

        result = assign_cluster_names(profiles)

        assert len(result) == 3
        assert len(set(result.values())) == 3

    def test_highest_rated_cluster_named_for_rating(self):
        """The cluster that stands out on rating is named after it."""
        profiles = {
            0: {"avg_rating": 4.9, "avg_price_level": 2.0, "review_count": 10},
            1: {"avg_rating": 3.2, "avg_price_level": 2.0, "review_count": 10},
            2: {"avg_rating": 3.3, "avg_price_level": 2.0, "review_count": 10},
        }

        result = assign_cluster_names(profiles)

        assert result[0] == "Mejor calificados"

    def test_cheapest_cluster_not_labelled_high_end(self):
        """A cluster below the average price level is never called 'Alta gama'."""
        profiles = {
            0: {"avg_rating": 4.0, "avg_price_level": 4.0, "review_count": 10},
            1: {"avg_rating": 4.0, "avg_price_level": 1.0, "review_count": 10},
        }

        result = assign_cluster_names(profiles)

        assert result[1] != "Alta gama"

    def test_handles_empty_profile(self):
        """Test that empty profiles don't cause errors."""
        profiles = {
            0: {},
            1: {"avg_rating": 4.0}
        }

        result = assign_cluster_names(profiles)
        assert 0 in result
        assert 1 in result


class TestClusteringIntegration:
    """Integration tests for clustering pipeline."""

    def test_full_clustering_pipeline(self, sample_reviews_df):
        """Test complete clustering pipeline."""
        # Initialize
        clusterer = RestaurantClusterer(n_clusters=3, random_state=42)

        # Engineer features (one row per restaurant)
        n_restaurants = sample_reviews_df["restaurant_id"].nunique()
        features = clusterer.engineer_features(sample_reviews_df)
        assert features.shape[0] == n_restaurants

        # Fit predict
        clusters = clusterer.fit_predict(features)
        assert len(clusters) == n_restaurants

        # Get profiles
        profiles = clusterer.get_cluster_profiles(sample_reviews_df, clusters)
        assert len(profiles) > 0

        # Add labels
        result = clusterer.add_cluster_labels(sample_reviews_df, clusters)
        assert "cluster" in result.columns
