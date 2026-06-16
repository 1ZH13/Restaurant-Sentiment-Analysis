"""
Data loader utility for the dashboard.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import json


DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"


def load_raw_data(source: str = "degusta") -> pd.DataFrame:
    """Load raw scraped data."""
    file_path = RAW_DIR / f"{source}_reviews.csv"
    if file_path.exists():
        return pd.read_csv(file_path)
    return pd.DataFrame()


def load_processed_data() -> pd.DataFrame:
    """Load processed data."""
    file_path = PROCESSED_DIR / "restaurants_clustered.csv"
    if not file_path.exists():
        file_path = PROCESSED_DIR / "normalized_reviews.csv"
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


def load_sentiment_cache() -> dict:
    """Load sentiment analysis cache."""
    cache_path = CACHE_DIR / "sentiment_cache.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}


def save_sentiment_result(review_hash: str, result: dict):
    """Save a sentiment result to cache."""
    cache_path = CACHE_DIR / "sentiment_cache.json"
    cache = {}

    if cache_path.exists():
        with open(cache_path, "r") as f:
            cache = json.load(f)

    cache[review_hash] = result

    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def get_data_summary() -> dict:
    """Get summary of available data."""
    summary = {
        "raw_degusta": 0,
        "raw_tripadvisor": 0,
        "processed": 0,
        "sentiment_cache": 0
    }

    degusta_path = RAW_DIR / "degusta_reviews.csv"
    tripadvisor_path = RAW_DIR / "tripadvisor_reviews.csv"
    processed_path = PROCESSED_DIR / "restaurants_clustered.csv"

    if degusta_path.exists():
        summary["raw_degusta"] = len(pd.read_csv(degusta_path))

    if tripadvisor_path.exists():
        summary["raw_tripadvisor"] = len(pd.read_csv(tripadvisor_path))

    if processed_path.exists():
        summary["processed"] = len(pd.read_csv(processed_path))

    cache_path = CACHE_DIR / "sentiment_cache.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            summary["sentiment_cache"] = len(json.load(f))

    return summary


if __name__ == "__main__":
    summary = get_data_summary()
    print("Resumen de datos:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
