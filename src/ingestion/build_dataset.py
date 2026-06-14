"""
Combine the two real data sources (Degusta + RestaurantGuru) into a single
unified raw dataset and attach aspect-level sentiment.

Output: data/raw/raw_reviews.csv  (input to the ETL pipeline / cleaner.py)

Sentiment is produced with the no-API-key Spanish/English lexicon analyzer
(src.sentiment.fallback_classifier.SpanishLexiconAnalyzer). If a working Gemini
API key is configured it can be swapped in, but the project does not depend on
one.
"""

from pathlib import Path

import pandas as pd

from src.sentiment.fallback_classifier import SpanishLexiconAnalyzer

RAW_DIR = Path("data/raw")
SOURCES = ["degusta_reviews.csv", "restaurantguru_reviews.csv"]

COLUMNS = [
    "restaurant_id", "restaurant_name", "category", "location", "price_range",
    "overall_rating", "food_rating", "service_rating", "ambiance_rating",
    "review_text", "review_date", "reviewer_name", "source", "aspect_sentiments",
]


def load_sources() -> pd.DataFrame:
    frames = []
    for name in SOURCES:
        path = RAW_DIR / name
        if path.exists():
            df = pd.read_csv(path)
            if not df.empty:
                frames.append(df)
                print(f"  {name}: {len(df)} reviews, {df['restaurant_id'].nunique()} restaurants")
        else:
            print(f"  {name}: missing (skipped)")
    if not frames:
        raise FileNotFoundError("No source review files found. Run the scrapers first.")
    return pd.concat(frames, ignore_index=True)


def add_aspect_sentiments(df: pd.DataFrame) -> pd.DataFrame:
    analyzer = SpanishLexiconAnalyzer()
    df["aspect_sentiments"] = [
        str(analyzer.analyze_review(t)) for t in df["review_text"].fillna("")
    ]
    return df


def main():
    print("Combining real data sources...")
    df = load_sources()

    # Drop rows without usable review text and obvious duplicates
    df = df[df["review_text"].notna() & (df["review_text"].astype(str).str.len() >= 10)]
    df = df.drop_duplicates(subset=["restaurant_id", "review_text"])

    print(f"Tagging aspect sentiment for {len(df)} reviews (lexicon, no API key)...")
    df = add_aspect_sentiments(df)

    # Ensure all expected columns exist and order them
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[COLUMNS]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "raw_reviews.csv"
    df.to_csv(out, index=False)

    print(f"\nSaved {len(df)} reviews to {out}")
    print("Source breakdown:")
    print(df["source"].value_counts().to_string())
    print(f"Restaurants: {df['restaurant_id'].nunique()}")


if __name__ == "__main__":
    main()
