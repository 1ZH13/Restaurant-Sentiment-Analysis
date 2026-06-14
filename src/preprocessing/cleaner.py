"""
Data cleaning module for restaurant reviews.
"""

import pandas as pd
import re
from typing import List, Optional


def remove_duplicates(df: pd.DataFrame, subset: List[str] = None) -> pd.DataFrame:
    """Remove duplicate records based on restaurant_id and review_text."""
    if subset is None:
        subset = ["restaurant_id", "review_text"]

    before_count = len(df)
    df_clean = df.drop_duplicates(subset=subset, keep="first")
    after_count = len(df_clean)

    print(f"Removed {before_count - after_count} duplicate records")
    return df_clean


def clean_text(text: str) -> str:
    """Clean review text by removing special characters and extra whitespace."""
    if pd.isna(text) or text is None:
        return ""

    text = str(text)

    # Remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove special characters but keep accented characters and basic punctuation
    text = re.sub(r"[^\w\sáéíóúñüÁÉÍÓÚÑÜ.,!?¡¿]", "", text)

    return text


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning operations to the dataframe."""
    df_clean = df.copy()

    # Remove rows with missing essential fields
    essential_fields = ["restaurant_id", "restaurant_name"]
    before_count = len(df_clean)
    df_clean = df_clean.dropna(subset=[f for f in essential_fields if f in df_clean.columns])
    print(f"Removed {before_count - len(df_clean)} rows with missing essential fields")

    # Clean text fields
    text_fields = ["review_text", "restaurant_name", "category", "location"]
    for field in text_fields:
        if field in df_clean.columns:
            df_clean[field] = df_clean[field].apply(clean_text)

    # Standardize rating columns
    rating_fields = ["overall_rating", "food_rating", "service_rating", "ambiance_rating", "rating"]
    for field in rating_fields:
        if field in df_clean.columns:
            df_clean[field] = pd.to_numeric(df_clean[field], errors="coerce")

    # Clean price range
    if "price_range" in df_clean.columns:
        df_clean["price_range"] = df_clean["price_range"].apply(
            lambda x: x.strip() if pd.notna(x) else None
        )

    # Standardize date formats
    if "review_date" in df_clean.columns:
        df_clean["review_date"] = pd.to_datetime(df_clean["review_date"], errors="coerce")

    return df_clean


def validate_schema(df: pd.DataFrame) -> bool:
    """Validate that dataframe has required columns."""
    required_columns = [
        "restaurant_id",
        "restaurant_name",
        "source"
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        print(f"Missing required columns: {missing}")
        return False

    print("Schema validation passed")
    return True


def main(input_path: str = "data/raw/raw_reviews.csv", output_path: str = "data/processed/cleaned_reviews.csv"):
    """Main cleaning pipeline."""
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)

    print(f"Original records: {len(df)}")

    df = remove_duplicates(df)
    df = clean_dataframe(df)

    if validate_schema(df):
        df.to_csv(output_path, index=False)
        print(f"Cleaned data saved to {output_path}")
        print(f"Final records: {len(df)}")
    else:
        print("Schema validation failed. Data not saved.")


if __name__ == "__main__":
    main()
