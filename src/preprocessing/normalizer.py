"""
Text normalization module for restaurant reviews.
"""

import pandas as pd
import re
import unicodedata
from typing import List, Optional

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    nltk.download("stopwords", quiet=True)
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    STOPWORDS = set(stopwords.words("spanish"))
except Exception:
    STOPWORDS = set()


def normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove accents, etc."""
    if pd.isna(text) or text is None:
        return ""

    text = str(text).lower()

    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def remove_stopwords(text: str, lang: str = "spanish") -> str:
    """Remove stopwords from text."""
    if not text or not STOPWORDS:
        return text

    words = text.split()
    words = [w for w in words if w.lower() not in STOPWORDS]
    return " ".join(words)


def tokenize(text: str) -> List[str]:
    """Tokenize text into words."""
    if not text:
        return []

    try:
        return word_tokenize(text)
    except Exception:
        return text.split()


def detect_language(text: str) -> str:
    """Simple language detection (Spanish vs English)."""
    if not text:
        return "unknown"

    spanish_indicators = ["el", "la", "los", "las", "un", "una", "de", "del", "en", "que", "es", "por", "con", "para"]
    english_indicators = ["the", "a", "an", "is", "was", "were", "are", "be", "have", "has", "had", "and", "or", "but"]

    text_lower = text.lower()
    spanish_count = sum(1 for word in spanish_indicators if word in text_lower)
    english_count = sum(1 for word in english_indicators if word in text_lower)

    if spanish_count > english_count:
        return "spanish"
    elif english_count > spanish_count:
        return "english"
    else:
        return "mixed"


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all normalization operations to dataframe."""
    df_norm = df.copy()

    # Normalize text fields
    if "review_text" in df_norm.columns:
        df_norm["review_text_normalized"] = df_norm["review_text"].apply(normalize_text)
        df_norm["review_text_normalized"] = df_norm["review_text_normalized"].apply(
            lambda x: remove_stopwords(x)
        )

    if "restaurant_name" in df_norm.columns:
        df_norm["restaurant_name_normalized"] = df_norm["restaurant_name"].apply(normalize_text)

    if "category" in df_norm.columns:
        df_norm["category_normalized"] = df_norm["category"].apply(normalize_text)

    # Detect language
    if "review_text" in df_norm.columns:
        df_norm["review_language"] = df_norm["review_text"].apply(detect_language)

    return df_norm


def add_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add text-based features."""
    df_features = df.copy()

    if "review_text" in df_features.columns:
        df_features["word_count"] = df_features["review_text"].apply(
            lambda x: len(str(x).split()) if pd.notna(x) else 0
        )
        df_features["char_count"] = df_features["review_text"].apply(
            lambda x: len(str(x)) if pd.notna(x) else 0
        )
        df_features["avg_word_length"] = df_features["review_text"].apply(
            lambda x: sum(len(w) for w in str(x).split()) / max(len(str(x).split()), 1) if pd.notna(x) else 0
        )

    return df_features


def main(input_path: str = "data/processed/cleaned_reviews.csv",
         output_path: str = "data/processed/normalized_reviews.csv"):
    """Main normalization pipeline."""
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)

    print(f"Processing {len(df)} records...")

    df = normalize_dataframe(df)
    df = add_text_features(df)

    df.to_csv(output_path, index=False)
    print(f"Normalized data saved to {output_path}")


if __name__ == "__main__":
    main()
