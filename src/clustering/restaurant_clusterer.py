"""
Restaurant clustering module using K-Means algorithm.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import silhouette_score
from typing import Dict, List, Tuple, Optional
import warnings

try:
    from sklearn.decomposition import PCA
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False


class RestaurantClusterer:
    """K-Means clustering for restaurants based on features."""

    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []

    def engineer_features(self, df: pd.DataFrame) -> np.ndarray:
        """Create feature matrix for clustering from restaurant dataframe."""
        features = pd.DataFrame()

        # Rating features
        if "overall_rating" in df.columns:
            features["avg_rating"] = df.groupby("restaurant_id")["overall_rating"].transform("mean")

        # Sentiment features (if available)
        sentiment_cols = ["sentiment_comida_score", "sentiment_servicio_score",
                         "sentiment_precio_score", "sentiment_ambiente_score"]
        for col in sentiment_cols:
            if col in df.columns:
                features[col.replace("_score", "_avg")] = df.groupby("restaurant_id")[col].transform("mean")

        # Review count
        if "review_text" in df.columns:
            features["review_count"] = df.groupby("restaurant_id")["review_text"].transform("count")

        # Word count average
        if "word_count" in df.columns:
            features["avg_word_count"] = df.groupby("restaurant_id")["word_count"].transform("mean")

        # Price range encoding
        if "price_range" in df.columns:
            price_map = {"$": 1, "$$ - $$$": 2, "$$$ - $$$$": 3, "$$$$": 4,
                        "Cheap Eats": 1, "Mid-range": 2, "Fine Dining": 4}
            features["price_encoded"] = df.groupby("restaurant_id")["price_range"].transform(
                lambda x: x.map(price_map).fillna(2)
            )

        # Fill NaN with column means
        features = features.fillna(features.mean())

        # Store feature names
        self.feature_names = features.columns.tolist()

        return features.values

    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        """Fit the model and predict clusters."""
        # Scale features
        features_scaled = self.scaler.fit_transform(features)

        # Fit and predict
        clusters = self.model.fit_predict(features_scaled)

        return clusters

    def get_cluster_profiles(self, df: pd.DataFrame, clusters: np.ndarray) -> Dict:
        """Generate descriptive profiles for each cluster."""
        df_with_clusters = df.copy()
        df_with_clusters["cluster"] = clusters

        profiles = {}

        for cluster_id in range(self.n_clusters):
            cluster_data = df_with_clusters[df_with_clusters["cluster"] == cluster_id]

            if len(cluster_data) == 0:
                continue

            profile = {
                "count": len(cluster_data),
                "avg_rating": cluster_data["overall_rating"].mean() if "overall_rating" in cluster_data else None,
                "avg_review_count": len(cluster_data),
            }

            # Sentiment averages
            for aspect in ["comida", "servicio", "precio", "ambiente"]:
                col = f"sentiment_{aspect}_score"
                if col in cluster_data.columns:
                    profile[f"avg_{aspect}_sentiment"] = cluster_data[col].mean()

            # Most common categories
            if "category" in cluster_data.columns:
                profile["top_categories"] = cluster_data["category"].value_counts().head(3).to_dict()

            # Price distribution
            if "price_range" in cluster_data.columns:
                profile["price_distribution"] = cluster_data["price_range"].value_counts().to_dict()

            profiles[cluster_id] = profile

        return profiles

    def add_cluster_labels(self, df: pd.DataFrame, clusters: np.ndarray) -> pd.DataFrame:
        """Add cluster labels to the original dataframe."""
        df = df.copy()
        df["cluster"] = clusters
        return df


def find_optimal_k(features: np.ndarray, k_range: range = range(2, 10)) -> Tuple[int, float]:
    """
    Find optimal number of clusters using silhouette score.

    Returns:
        Tuple of (best_k, best_silhouette_score)
    """
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    best_k = 2
    best_score = -1

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features_scaled)

        score = silhouette_score(features_scaled, labels)
        print(f"k={k}: silhouette_score={score:.4f}")

        if score > best_score:
            best_score = score
            best_k = k

    return best_k, best_score


def visualize_clusters_pca(features: np.ndarray, clusters: np.ndarray,
                          labels: Optional[List[str]] = None) -> np.ndarray:
    """Reduce dimensionality using PCA for visualization."""
    if not PCA_AVAILABLE:
        raise ImportError("PCA not available from sklearn")

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    pca = PCA(n_components=2)
    features_2d = pca.fit_transform(features_scaled)

    return features_2d


def assign_cluster_names(profiles: Dict) -> Dict[int, str]:
    """Assign human-readable names to clusters based on their profiles."""
    cluster_names = {}

    for cluster_id, profile in profiles.items():
        # Determine cluster type based on characteristics
        avg_rating = profile.get("avg_rating", 0) or 0
        avg_comida = profile.get("avg_comida_sentiment", 0) or 0
        avg_servicio = profile.get("avg_servicio_sentiment", 0) or 0
        price_dist = profile.get("price_distribution", {})

        # Determine dominant characteristics
        is_premium = avg_rating >= 4.5 or (price_dist.get("$$$$", 0) + price_dist.get("Fine Dining", 0)) > 0
        is_economic = price_dist.get("$", 0) + price_dist.get("Cheap Eats", 0) > 0
        has_good_food = avg_comida > 0.3
        has_good_service = avg_servicio > 0.3

        if is_premium:
            name = "Premium Fine Dining"
        elif is_economic:
            name = "Budget-Friendly"
        elif has_good_food and has_good_service:
            name = "Best Overall"
        elif has_good_food:
            name = "Foodie's Choice"
        elif has_good_service:
            name = "Best Service"
        else:
            name = f"Cluster {cluster_id}"

        cluster_names[cluster_id] = name

    return cluster_names


def main():
    """Example usage."""
    # Load processed data
    df = pd.read_csv("data/processed/normalized_reviews.csv")

    # Derive numeric aspect-sentiment columns so clustering can use them and the
    # dashboard's canonical file (restaurants_clustered.csv) ships with them.
    from src.sentiment.aspect_scores import derive_aspect_sentiment_scores
    df = derive_aspect_sentiment_scores(df)

    # Initialize clusterer
    clusterer = RestaurantClusterer(n_clusters=5)

    # Engineer features
    print("Engineering features...")
    features = clusterer.engineer_features(df)
    print(f"Feature matrix shape: {features.shape}")

    # Find optimal k
    print("\nFinding optimal k...")
    best_k, best_score = find_optimal_k(features)
    print(f"Best k={best_k} with silhouette_score={best_score:.4f}")

    # Fit model
    print(f"\nFitting model with k={clusterer.n_clusters}...")
    clusters = clusterer.fit_predict(features)

    # Get profiles
    profiles = clusterer.get_cluster_profiles(df, clusters)
    print("\nCluster profiles:")
    for cluster_id, profile in profiles.items():
        print(f"  Cluster {cluster_id}: {profile['count']} restaurants")

    # Assign names
    cluster_names = assign_cluster_names(profiles)
    print("\nCluster names:")
    for cluster_id, name in cluster_names.items():
        print(f"  Cluster {cluster_id}: {name}")

    # Save results
    df_with_clusters = clusterer.add_cluster_labels(df, clusters)
    df_with_clusters.to_csv("data/processed/restaurants_clustered.csv", index=False)
    print("\nResults saved to data/processed/restaurants_clustered.csv")


if __name__ == "__main__":
    main()
