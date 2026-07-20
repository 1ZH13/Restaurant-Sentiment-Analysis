"""
Combine the two real data sources (Degusta + RestaurantGuru) into a single
unified raw dataset and attach aspect-level sentiment.

Output: data/raw/raw_reviews.csv  (input to the ETL pipeline / cleaner.py)

Two kinds of duplication are resolved here:

1. *Restaurant identity*: the same restaurant is listed by both sources under
   different ids (Degusta uses a numeric id, RestaurantGuru a URL slug hash).
   Names are normalised into a ``restaurant_key`` and every source id mapping to
   the same key collapses onto one canonical ``restaurant_id``.

2. *Review duplication*: the same review text can appear twice, either within a
   source or because both sources aggregate the same underlying Google review.
   Reviews are deduplicated on the normalised text within a restaurant.

Metadata (category, price, location, ratings) is merged across sources so a
field missing in one source can be filled from the other.

Sentiment is produced with the no-API-key Spanish/English lexicon analyzer
(src.sentiment.fallback_classifier.SpanishLexiconAnalyzer).
"""

import hashlib
import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.sentiment.fallback_classifier import SpanishLexiconAnalyzer

RAW_DIR = Path("data/raw")
SOURCES = ["degusta_reviews.csv", "restaurantguru_reviews.csv"]

COLUMNS = [
    "restaurant_id", "restaurant_key", "restaurant_name", "category", "location",
    "address", "price_range", "overall_rating", "review_rating",
    "food_rating", "service_rating", "ambiance_rating",
    "review_text", "review_date", "reviewer_name", "source", "source_restaurant_id",
    "aspect_sentiments", "aspect_mentions",
]

# Metadata columns merged across sources: first non-null value per restaurant wins.
META_COLUMNS = [
    "restaurant_name", "category", "location", "address", "price_range",
    "overall_rating", "food_rating", "service_rating", "ambiance_rating",
]


def normalize_name(name: str) -> str:
    """Normalise a restaurant name into a comparable key.

    Lowercases, strips accents and punctuation, and collapses whitespace so
    "Salsipuedes Restaurant" and "Salsipuedes  Restaurante" compare equal.
    Branch names are deliberately left intact - two Sugoi branches are two
    different restaurants, not a duplicate.
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"\b(restaurante?|resto|bar|grill|cafe)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_review_text(text: str) -> str:
    """Normalise review text for duplicate detection."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def canonical_id(key: str) -> str:
    """Build a stable canonical restaurant id from its normalised name key."""
    return "r_" + hashlib.md5(key.encode("utf-8")).hexdigest()[:10]


def load_sources() -> pd.DataFrame:
    frames = []
    for name in SOURCES:
        path = RAW_DIR / name
        if not path.exists():
            print(f"  {name}: no encontrado (omitido)")
            continue
        df = pd.read_csv(path)
        if df.empty:
            print(f"  {name}: vacio (omitido)")
            continue
        frames.append(df)
        print(f"  {name}: {len(df)} resenas, {df['restaurant_id'].nunique()} restaurantes")
    if not frames:
        raise FileNotFoundError("No hay archivos de fuentes. Corre los scrapers primero.")
    return pd.concat(frames, ignore_index=True)


def unify_restaurants(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-source restaurant ids onto one canonical id per restaurant."""
    df = df.copy()
    df["source_restaurant_id"] = df["restaurant_id"]
    df["restaurant_key"] = df["restaurant_name"].apply(normalize_name)

    # Rows whose name could not be normalised keep their own identity.
    blank = df["restaurant_key"] == ""
    df.loc[blank, "restaurant_key"] = df.loc[blank, "source_restaurant_id"].astype(str)

    df["restaurant_id"] = df["restaurant_key"].apply(canonical_id)

    merged = df.groupby("restaurant_key")["source_restaurant_id"].nunique()
    multi = merged[merged > 1]
    if len(multi) > 0:
        print(f"  {len(multi)} restaurantes aparecian en ambas fuentes y se unificaron:")
        for key in multi.index[:10]:
            names = df.loc[df["restaurant_key"] == key, "restaurant_name"].unique()
            print(f"    - {' | '.join(str(n) for n in names[:3])}")
    return df


def merge_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Fill each restaurant's metadata with the first non-null value available.

    A field missing in one source (Degusta has no price for some venues,
    RestaurantGuru has no per-review rating) is completed from the other.
    """
    df = df.copy()
    for col in META_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
            continue
        filled = df.groupby("restaurant_id")[col].transform(
            lambda s: s.ffill().bfill()
        )
        df[col] = filled
    return df


def deduplicate_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Drop repeated reviews within a restaurant, comparing normalised text."""
    df = df.copy()
    df["_text_key"] = df["review_text"].apply(normalize_review_text)

    before = len(df)
    df = df[df["_text_key"].str.len() >= 10]
    print(f"  {before - len(df)} resenas descartadas por texto vacio o muy corto")

    before = len(df)
    df = df.drop_duplicates(subset=["restaurant_id", "_text_key"], keep="first")
    print(f"  {before - len(df)} resenas duplicadas eliminadas")

    return df.drop(columns=["_text_key"])


def add_aspect_sentiments(df: pd.DataFrame) -> pd.DataFrame:
    """Attach aspect labels plus which aspects the review actually discussed.

    ``aspect_mentions`` is what lets the dashboard average only the reviews that
    really talked about an aspect, instead of counting silence as "neutral".
    """
    analyzer = SpanishLexiconAnalyzer()
    df = df.copy()

    details = [analyzer.get_aspect_details(t) for t in df["review_text"].fillna("")]
    df["aspect_sentiments"] = [
        str({a: d["label"] for a, d in detail.items()}) for detail in details
    ]
    df["aspect_mentions"] = [
        str({a: d["mentioned"] for a, d in detail.items()}) for detail in details
    ]
    return df


def main():
    print("Combinando fuentes reales...")
    df = load_sources()

    print("\nUnificando identidad de restaurantes...")
    df = unify_restaurants(df)

    print("\nEliminando duplicados...")
    df = deduplicate_reviews(df)

    print("\nCompletando metadatos entre fuentes...")
    df = merge_metadata(df)

    print(f"\nEtiquetando sentimiento por aspecto para {len(df)} resenas (lexicon, sin API key)...")
    df = add_aspect_sentiments(df)

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[COLUMNS]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "raw_reviews.csv"
    df.to_csv(out, index=False)

    print(f"\nGuardadas {len(df)} resenas en {out}")
    print("Por fuente:")
    print(df["source"].value_counts().to_string())
    print(f"Restaurantes unicos: {df['restaurant_id'].nunique()}")
    print("\nCobertura de campos:")
    for col in ["category", "price_range", "location", "overall_rating",
                "review_rating", "review_date", "food_rating"]:
        pct = df[col].notna().mean() * 100 if col in df.columns else 0
        print(f"  {col:16s} {df[col].notna().sum():4d}/{len(df)}  ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
