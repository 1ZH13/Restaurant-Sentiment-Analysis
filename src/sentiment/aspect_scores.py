"""
Helpers to derive numeric aspect-sentiment columns from the ``aspect_sentiments``
field stored as a dict-string in the review datasets.

This is the single source of truth used both by the data pipeline
(``src.clustering.restaurant_clusterer``) and by the dashboard loader so the
``sentiment_<aspect>`` / ``sentiment_<aspect>_score`` columns are always
consistent.
"""

import ast
from typing import Dict

import pandas as pd

ASPECTS = ("comida", "servicio", "precio", "ambiente")

# Maps the categorical label to a numeric score used by charts and clustering.
SENTIMENT_SCORE_MAP = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def parse_aspect_sentiments(value) -> Dict[str, str]:
    """Parse a single ``aspect_sentiments`` cell into a dict of aspect -> label.

    Accepts a dict-string (e.g. ``"{'comida': 'positive', ...}"``) or an actual
    dict. Falls back to all-``neutral`` for missing or malformed values.
    """
    neutral = {aspect: "neutral" for aspect in ASPECTS}

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return neutral
    if isinstance(value, dict):
        parsed = value
    else:
        try:
            parsed = ast.literal_eval(str(value))
        except (ValueError, SyntaxError):
            return neutral
        if not isinstance(parsed, dict):
            return neutral

    return {aspect: str(parsed.get(aspect, "neutral")).lower() for aspect in ASPECTS}


def derive_aspect_sentiment_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``sentiment_<aspect>`` and ``sentiment_<aspect>_score`` columns.

    Idempotent: if the score columns already exist they are left untouched.
    Returns the same DataFrame (mutated in place) for convenience.
    """
    score_cols = [f"sentiment_{aspect}_score" for aspect in ASPECTS]
    if all(col in df.columns for col in score_cols):
        return df

    if "aspect_sentiments" not in df.columns:
        return df

    parsed = df["aspect_sentiments"].apply(parse_aspect_sentiments)

    for aspect in ASPECTS:
        labels = parsed.apply(lambda d, a=aspect: d[a])
        df[f"sentiment_{aspect}"] = labels
        df[f"sentiment_{aspect}_score"] = labels.map(SENTIMENT_SCORE_MAP).fillna(0.0)

    return df
