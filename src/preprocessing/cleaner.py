"""
Data cleaning module for restaurant reviews.
"""

import pandas as pd
import re
from typing import List, Optional

# RestaurantGuru publishes relative dates ("hace 2 años", "hace un mes").
# pd.to_datetime cannot parse those, so they are converted first.
RELATIVE_DATE_RE = re.compile(
    r"hace\s+(un|una|unos|unas|\d+)\s*(d[ií]as?|semanas?|mes(?:es)?|a[ñn]os?|horas?|minutos?)",
    re.IGNORECASE,
)
# Matched by prefix so singular and plural both resolve. Stripping a trailing
# "s" does not work here: "mes" would become "me" and fail to match, so
# "hace un mes" silently produced no date while "hace 2 meses" worked.
RELATIVE_UNIT_PREFIXES = (
    ("minuto", "minutes"),
    ("hora", "hours"),
    ("dia", "days"),
    ("día", "days"),
    ("semana", "weeks"),
    ("mes", "months"),
    ("año", "years"),
    ("ano", "years"),
)


def parse_relative_date(value, reference: Optional[pd.Timestamp] = None) -> Optional[pd.Timestamp]:
    """Convert a Spanish relative date ("hace 3 meses") into a timestamp.

    Returns None when the value is not a relative date, so callers can fall
    back to normal date parsing.
    """
    if pd.isna(value):
        return None

    match = RELATIVE_DATE_RE.search(str(value))
    if not match:
        return None

    amount_raw, unit_raw = match.group(1).lower(), match.group(2).lower()
    amount = 1 if amount_raw in ("un", "una", "unos", "unas") else int(amount_raw)

    offset_unit = next(
        (offset for prefix, offset in RELATIVE_UNIT_PREFIXES if unit_raw.startswith(prefix)),
        None,
    )
    if offset_unit is None:
        return None

    reference = reference if reference is not None else pd.Timestamp.today().normalize()
    return reference - pd.DateOffset(**{offset_unit: amount})


def standardize_dates(series: pd.Series, reference: Optional[pd.Timestamp] = None) -> pd.Series:
    """Parse a date column that mixes absolute and relative Spanish dates."""
    relative = pd.to_datetime(
        series.apply(lambda v: parse_relative_date(v, reference)), errors="coerce"
    )
    absolute = pd.to_datetime(series, errors="coerce", format="mixed")
    # combine_first on mixed inputs yields object dtype, so coerce back.
    return pd.to_datetime(relative.combine_first(absolute), errors="coerce")


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

    # Degusta separates cuisines with "·", which clean_text would drop and
    # silently merge into one label ("Española · Argentina" -> "Española Argentina").
    if "category" in df_clean.columns:
        df_clean["category"] = df_clean["category"].apply(
            lambda x: re.sub(r"\s*[·/|]\s*", ", ", str(x)) if pd.notna(x) else x
        )

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

    # Standardize date formats (handles both ISO dates and "hace 2 meses")
    if "review_date" in df_clean.columns:
        df_clean["review_date"] = standardize_dates(df_clean["review_date"])

    # Unify the two sources' price vocabularies and simplify compound cuisines.
    df_clean = add_price_band(df_clean)
    df_clean = add_primary_category(df_clean)

    return df_clean


# The two sources describe price differently ("Desde $15 hasta $25" vs "$$").
# Both are mapped onto one ordinal scale so filters and charts speak a single
# vocabulary instead of showing seven overlapping labels.
PRICE_LEVELS = {
    "hasta $15": 1, "menos de $15": 1, "$": 1,
    "desde $15 hasta $25": 2, "$$": 2, "$$ - $$$": 2,
    "desde $25 hasta $35": 3, "$$$": 3, "$$$ - $$$$": 3,
    "mas de $35": 4, "más de $35": 4, "$$$$": 4,
    "cheap eats": 1, "mid-range": 2, "fine dining": 4,
}

PRICE_BANDS = {
    1: "$ (hasta $15)",
    2: "$$ ($15-$25)",
    3: "$$$ ($25-$35)",
    4: "$$$$ (mas de $35)",
}


def encode_price(value) -> Optional[float]:
    """Map any source's price label onto an ordinal level from 1 to 4."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip().lower()
    if not text or text == "nan":
        return None
    if text in PRICE_LEVELS:
        return float(PRICE_LEVELS[text])

    # Fall back to counting dollar signs, which covers "$$"-style labels.
    dollars = text.count("$")
    return float(min(dollars, 4)) if dollars else None


def add_price_band(df: pd.DataFrame) -> pd.DataFrame:
    """Add the canonical ``price_level`` (1-4) and ``price_band`` label."""
    df = df.copy()
    if "price_range" not in df.columns:
        return df
    df["price_level"] = df["price_range"].apply(encode_price)
    df["price_band"] = df["price_level"].map(PRICE_BANDS)
    return df


def add_primary_category(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``category_primary``: the first cuisine of a compound category.

    Categories arrive as "Italiana, Pizzeria" or "Fusion, Mediterranea", which
    produces ~100 near-unique labels. The leading cuisine is what charts and
    filters should group on.
    """
    df = df.copy()
    if "category" not in df.columns:
        return df
    df["category_primary"] = (
        df["category"].astype(str).str.split(",").str[0].str.strip().replace({"nan": None, "": None})
    )
    return df


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
