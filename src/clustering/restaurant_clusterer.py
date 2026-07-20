"""
Restaurant clustering module using K-Means.

Clustering happens at the *restaurant* level. The reviews table is aggregated to
one row per restaurant first; previously the feature matrix was built with
``groupby(...).transform(...)``, which produced one row per review with the same
values repeated for every review of a restaurant. That inflated the silhouette
score (identical points sit at distance zero from each other) and made a
restaurant with 5 reviews count five times as much as one with a single review.
Cluster labels are mapped back onto the reviews table at the end.
"""

import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

try:
    from sklearn.decomposition import PCA
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False


# Price encoding lives in the cleaner so the pipeline and the dashboard agree on
# a single definition of what "$$$" means.
from src.preprocessing.cleaner import encode_price  # noqa: E402

SENTIMENT_COLUMNS = [
    "sentiment_comida_score", "sentiment_servicio_score",
    "sentiment_precio_score", "sentiment_ambiente_score",
]


class RestaurantClusterer:
    """K-Means clustering of restaurants based on aggregated review features."""

    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.restaurant_ids: List = []

    def aggregate_by_restaurant(self, df: pd.DataFrame) -> pd.DataFrame:
        """Collapse the reviews table into one row per restaurant."""
        if "restaurant_id" not in df.columns:
            raise KeyError("aggregate_by_restaurant requires a 'restaurant_id' column")

        grouped = df.groupby("restaurant_id", sort=True)
        features = pd.DataFrame(index=grouped.size().index)

        if "overall_rating" in df.columns:
            features["avg_rating"] = grouped["overall_rating"].mean()

        for col in SENTIMENT_COLUMNS:
            if col in df.columns:
                features[col.replace("_score", "_avg")] = grouped[col].mean()

        if "review_text" in df.columns:
            features["review_count"] = grouped["review_text"].count()

        if "word_count" in df.columns:
            features["avg_word_count"] = grouped["word_count"].mean()

        # Prefer the canonical level the cleaner already computed.
        if "price_level" in df.columns:
            features["price_level"] = grouped["price_level"].mean()
        elif "price_range" in df.columns:
            price_levels = df.assign(_price=df["price_range"].apply(encode_price))
            features["price_level"] = price_levels.groupby("restaurant_id")["_price"].mean()

        # Columns that are entirely empty carry no signal and would become NaN
        # after mean-imputation, so drop them before filling.
        features = features.dropna(axis=1, how="all")
        return features.fillna(features.mean())

    def engineer_features(self, df: pd.DataFrame) -> np.ndarray:
        """Build the clustering matrix: one row per restaurant."""
        features = self.aggregate_by_restaurant(df)
        self.feature_names = features.columns.tolist()
        self.restaurant_ids = features.index.tolist()
        return features.values

    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        """Fit the model and predict a cluster per restaurant."""
        features_scaled = self.scaler.fit_transform(features)
        return self.model.fit_predict(features_scaled)

    def get_cluster_profiles(self, df: pd.DataFrame, clusters: np.ndarray,
                             restaurant_ids: Optional[List] = None) -> Dict:
        """Describe each cluster using the reviews of its restaurants.

        ``counts`` are reported both per restaurant and per review so callers do
        not confuse the two.
        """
        restaurant_ids = restaurant_ids if restaurant_ids is not None else self.restaurant_ids
        mapping = dict(zip(restaurant_ids, clusters))

        df_with_clusters = df.copy()
        df_with_clusters["cluster"] = df_with_clusters["restaurant_id"].map(mapping)

        profiles: Dict = {}
        for cluster_id in sorted(set(int(c) for c in clusters)):
            cluster_data = df_with_clusters[df_with_clusters["cluster"] == cluster_id]
            if len(cluster_data) == 0:
                continue

            profile = {
                "count": cluster_data["restaurant_id"].nunique(),
                "review_count": len(cluster_data),
                "avg_rating": cluster_data["overall_rating"].mean()
                if "overall_rating" in cluster_data else None,
            }

            for aspect in ["comida", "servicio", "precio", "ambiente"]:
                col = f"sentiment_{aspect}_score"
                if col in cluster_data.columns:
                    profile[f"avg_{aspect}_sentiment"] = cluster_data[col].mean()

            if "price_range" in cluster_data.columns:
                levels = cluster_data["price_range"].apply(encode_price).dropna()
                profile["avg_price_level"] = levels.mean() if len(levels) else None
                profile["price_distribution"] = cluster_data["price_range"].value_counts().to_dict()

            if "category" in cluster_data.columns:
                profile["top_categories"] = cluster_data["category"].value_counts().head(3).to_dict()

            profiles[cluster_id] = profile

        return profiles

    def add_cluster_labels(self, df: pd.DataFrame, clusters: np.ndarray,
                           restaurant_ids: Optional[List] = None) -> pd.DataFrame:
        """Map restaurant-level cluster labels back onto the reviews table."""
        restaurant_ids = restaurant_ids if restaurant_ids is not None else self.restaurant_ids
        mapping = dict(zip(restaurant_ids, clusters))

        df = df.copy()
        df["cluster"] = df["restaurant_id"].map(mapping)
        return df


def find_optimal_k(features: np.ndarray, k_range: range = range(2, 10),
                   verbose: bool = True) -> Tuple[int, float]:
    """Find the number of clusters with the best silhouette score.

    ``k`` is capped at ``n_samples - 1`` so small datasets do not raise.
    """
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    n_samples = features_scaled.shape[0]
    usable = [k for k in k_range if 2 <= k < n_samples]
    if not usable:
        return 2, -1.0

    best_k, best_score = usable[0], -1.0
    for k in usable:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features_scaled)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(features_scaled, labels)
        if verbose:
            print(f"  k={k}: silhouette_score={score:.4f}")
        if score > best_score:
            best_score, best_k = score, k

    return best_k, best_score


def visualize_clusters_pca(features: np.ndarray, clusters: np.ndarray,
                           labels: Optional[List[str]] = None) -> np.ndarray:
    """Reduce dimensionality using PCA for visualization."""
    if not PCA_AVAILABLE:
        raise ImportError("PCA not available from sklearn")

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    return PCA(n_components=2).fit_transform(features_scaled)


# Profile metric -> label used when that metric is what sets a cluster apart.
NAME_BY_METRIC = {
    "avg_rating": "Mejor calificados",
    "avg_price_level": "Alta gama",
    "avg_comida_sentiment": "Destacan por la comida",
    "avg_servicio_sentiment": "Destacan por el servicio",
    "avg_ambiente_sentiment": "Destacan por el ambiente",
    "avg_precio_sentiment": "Buena relacion precio",
    "review_count": "Los mas comentados",
}
LOW_PRICE_NAME = "Economicos"


def assign_cluster_names(profiles: Dict) -> Dict[int, str]:
    """Name each cluster after what actually distinguishes it from the others.

    The previous version applied absolute thresholds ("premium if any review has
    a rating >= 4.5"), which labelled almost every cluster "Premium Fine Dining".
    Here each metric is standardised across clusters and a cluster is named after
    the metric on which it stands out most, with collisions resolved by falling
    back to its next most distinctive metric.
    """
    if not profiles:
        return {}

    metrics = list(NAME_BY_METRIC.keys())
    table = pd.DataFrame(
        {m: {cid: p.get(m) for cid, p in profiles.items()} for m in metrics}
    ).astype(float)
    table = table.dropna(axis=1, how="all")

    # Standardise so metrics on different scales are comparable.
    spread = table.std(ddof=0).replace(0, np.nan)
    z_scores = (table - table.mean()) / spread
    z_scores = z_scores.dropna(axis=1, how="all").fillna(0.0)

    if z_scores.empty:
        return {int(cid): f"Grupo {cid}" for cid in profiles}

    # Rank each cluster's metrics from most to least distinctive.
    ranked = {cid: list(row.sort_values(ascending=False).index) for cid, row in z_scores.iterrows()}

    names: Dict[int, str] = {}
    used: set = set()
    for cid in sorted(profiles):
        chosen = None
        for metric in ranked.get(cid, []):
            value = z_scores.loc[cid, metric]
            if metric == "avg_price_level" and value < 0:
                continue
            name = NAME_BY_METRIC[metric]
            if name not in used:
                chosen = name
                break

        if chosen is None:
            # Everything distinctive is taken; fall back to the price axis or a
            # plain numbered label so names stay unique.
            if "avg_price_level" in z_scores.columns and \
                    z_scores.loc[cid, "avg_price_level"] < 0 and LOW_PRICE_NAME not in used:
                chosen = LOW_PRICE_NAME
            else:
                chosen = f"Grupo {cid}"

        names[int(cid)] = chosen
        used.add(chosen)

    return names


def main():
    """Run restaurant-level clustering over the normalized reviews."""
    df = pd.read_csv("data/processed/normalized_reviews.csv")

    # Derive numeric aspect-sentiment columns so clustering can use them and the
    # dashboard's canonical file ships with them.
    from src.sentiment.aspect_scores import derive_aspect_sentiment_scores
    df = derive_aspect_sentiment_scores(df)

    clusterer = RestaurantClusterer()

    print("Agregando features por restaurante...")
    features = clusterer.engineer_features(df)
    print(f"  matriz: {features.shape[0]} restaurantes x {features.shape[1]} features")
    print(f"  features: {', '.join(clusterer.feature_names)}")

    print("\nBuscando k optimo (silhouette)...")
    best_k, best_score = find_optimal_k(features)
    print(f"  mejor k={best_k} (silhouette={best_score:.4f})")

    # Use the k that the data actually supports instead of a hardcoded value.
    clusterer.n_clusters = best_k
    clusterer.model = KMeans(n_clusters=best_k, random_state=clusterer.random_state, n_init=10)

    print(f"\nAjustando modelo con k={best_k}...")
    clusters = clusterer.fit_predict(features)

    profiles = clusterer.get_cluster_profiles(df, clusters)
    cluster_names = assign_cluster_names(profiles)

    print("\nPerfiles de cluster:")
    for cluster_id, profile in profiles.items():
        print(f"  Cluster {cluster_id} [{cluster_names.get(cluster_id, '')}]: "
              f"{profile['count']} restaurantes / {profile['review_count']} resenas, "
              f"rating={profile['avg_rating']:.2f}"
              if profile.get("avg_rating") is not None else
              f"  Cluster {cluster_id}: {profile['count']} restaurantes")

    df_with_clusters = clusterer.add_cluster_labels(df, clusters)
    # Persist the names so the dashboard can show them instead of "Grupo 3".
    df_with_clusters["cluster_name"] = df_with_clusters["cluster"].map(cluster_names)

    df_with_clusters.to_csv("data/processed/restaurants_clustered.csv", index=False)
    print("\nResultados guardados en data/processed/restaurants_clustered.csv")


if __name__ == "__main__":
    main()
