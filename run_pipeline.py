"""
One-command ETL + ML pipeline.

Runs every stage in order, starting from the scraped source files
(data/raw/degusta_reviews.csv and data/raw/restaurantguru_reviews.csv):

    combine sources -> clean -> normalize -> feature engineering -> clustering

It does NOT scrape (scraping is live/rate-limited). To refresh the raw sources
first, run the scrapers:

    python -m src.ingestion.degusta_scraper
    python -m src.ingestion.restaurantguru_scraper

Then:

    python run_pipeline.py
"""

from src.ingestion import build_dataset
from src.preprocessing import cleaner, normalizer, feature_engineering
from src.clustering import restaurant_clusterer


STAGES = [
    ("Combine sources + aspect sentiment", build_dataset.main),
    ("Clean", cleaner.main),
    ("Normalize", normalizer.main),
    ("Feature engineering", feature_engineering.main),
    ("Clustering", restaurant_clusterer.main),
]


def main():
    for i, (label, fn) in enumerate(STAGES, 1):
        print(f"\n{'=' * 60}\n[{i}/{len(STAGES)}] {label}\n{'=' * 60}")
        fn()
    print("\nPipeline complete. Launch the dashboard with:")
    print("    streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
