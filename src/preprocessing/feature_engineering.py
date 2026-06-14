"""
Feature engineering module for restaurant analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List


def calculate_restaurant_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate aggregated statistics per restaurant."""
    if "review_text" not in df.columns:
        raise ValueError("DataFrame must have 'review_text' column")

    # Group by restaurant
    restaurant_stats = df.groupby(["restaurant_id", "restaurant_name"]).agg({
        "review_text": "count",
        "overall_rating": "mean",
        "word_count": "mean",
        "char_count": "mean"
    }).reset_index()

    restaurant_stats.columns = [
        "restaurant_id",
        "restaurant_name",
        "review_count",
        "avg_rating",
        "avg_word_count",
        "avg_char_count"
    ]

    # Round ratings
    restaurant_stats["avg_rating"] = restaurant_stats["avg_rating"].round(2)
    restaurant_stats["avg_word_count"] = restaurant_stats["avg_word_count"].round(2)
    restaurant_stats["avg_char_count"] = restaurant_stats["avg_char_count"].round(2)

    return restaurant_stats


def encode_categorical_features(df: pd.DataFrame, categories: List[str] = None) -> pd.DataFrame:
    """Encode categorical features for ML models."""
    df_encoded = df.copy()

    # Price range encoding
    price_mapping = {
        "$": 1,
        "$$ - $$$": 2,
        "$$$ - $$$$": 3,
        "$$$$": 4,
        "Cheap Eats": 1,
        "Mid-range": 2,
        "Fine Dining": 4
    }

    if "price_range" in df_encoded.columns:
        df_encoded["price_range_encoded"] = df_encoded["price_range"].map(price_mapping).fillna(2)

    # Category encoding (simple one-hot for top categories)
    if categories is None and "category" in df_encoded.columns:
        # Get top 10 most common categories
        categories = df_encoded["category"].value_counts().head(10).index.tolist()

    if categories:
        for cat in categories:
            col_name = f"cat_{cat.lower().replace(' ', '_')[:20]}"
            df_encoded[col_name] = df_encoded["category"].str.lower().str.contains(cat.lower(), na=False).astype(int)

    return df_encoded


def create_sentiment_features(df: pd.DataFrame, sentiment_columns: List[str] = None) -> pd.DataFrame:
    """Create features based on sentiment analysis results."""
    df_features = df.copy()

    if sentiment_columns is None:
        sentiment_columns = ["sentiment_comida", "sentiment_servicio", "sentiment_precio", "sentiment_ambiente"]

    # Check if sentiment columns exist
    existing_sentiment_cols = [col for col in sentiment_columns if col in df_features.columns]

    if existing_sentiment_cols:
        # Calculate aggregate sentiment score
        sentiment_map = {"positive": 1, "neutral": 0, "negative": -1}
        for col in existing_sentiment_cols:
            if df_features[col].dtype == object:
                df_features[f"{col}_score"] = df_features[col].map(sentiment_map)

        # Overall sentiment score (average of aspect sentiments)
        sentiment_score_cols = [f"{col}_score" for col in existing_sentiment_cols]
        if all(col in df_features.columns for col in sentiment_score_cols):
            df_features["overall_sentiment_score"] = df_features[sentiment_score_cols].mean(axis=1)

        # Positive/negative counts
        df_features["positive_aspect_count"] = (df_features[sentiment_score_cols] > 0).sum(axis=1)
        df_features["negative_aspect_count"] = (df_features[sentiment_score_cols] < 0).sum(axis=1)

    return df_features


def create_clustering_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create features suitable for clustering."""
    df_cluster = df.copy()

    # Numerical features for clustering
    numerical_cols = ["overall_rating", "avg_word_count", "price_range_encoded"]

    # One-hot encoded categories
    category_cols = [col for col in df_cluster.columns if col.startswith("cat_")]

    # Sentiment features
    sentiment_cols = ["overall_sentiment_score", "positive_aspect_count", "negative_aspect_count"]

    # Combine all feature columns
    feature_cols = numerical_cols + category_cols + [c for c in sentiment_cols if c in df_cluster.columns]
    feature_cols = [c for c in feature_cols if c in df_cluster.columns]

    # Fill missing values with column means
    for col in feature_cols:
        if df_cluster[col].dtype in [np.float64, np.int64]:
            df_cluster[col] = df_cluster[col].fillna(df_cluster[col].mean())

    return df_cluster, feature_cols


def main(input_path: str = "data/processed/normalized_reviews.csv",
         output_path: str = "data/processed/restaurant_features.csv"):
    """Main feature engineering pipeline."""
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)

    print(f"Processing {len(df)} records...")

    # Calculate restaurant stats
    restaurant_stats = calculate_restaurant_stats(df)
    print(f"Calculated stats for {len(restaurant_stats)} restaurants")

    # Merge back to main dataframe
    df = df.merge(restaurant_stats, on=["restaurant_id", "restaurant_name"], how="left")

    # Encode categorical features
    df = encode_categorical_features(df)

    # Create sentiment features (if sentiment columns exist)
    df = create_sentiment_features(df)

    df.to_csv(output_path, index=False)
    print(f"Feature engineering complete. Saved to {output_path}")

    return df


if __name__ == "__main__":
    main()
