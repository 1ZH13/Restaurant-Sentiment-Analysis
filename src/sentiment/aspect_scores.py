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


def parse_aspect_mentions(value) -> Dict[str, bool]:
    """Parse an ``aspect_mentions`` cell into a dict of aspect -> bool.

    Datasets produced before mention tracking existed have no such column; those
    fall back to True so their behaviour is unchanged.
    """
    default = {aspect: True for aspect in ASPECTS}

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    parsed = value
    if not isinstance(parsed, dict):
        try:
            parsed = ast.literal_eval(str(value))
        except (ValueError, SyntaxError):
            return default
        if not isinstance(parsed, dict):
            return default

    return {aspect: bool(parsed.get(aspect, True)) for aspect in ASPECTS}


def derive_aspect_sentiment_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``sentiment_<aspect>``, ``sentiment_<aspect>_score`` and
    ``mentions_<aspect>`` columns.

    The ``mentions_`` flags mark whether the review actually discussed the
    aspect, so averages can exclude reviews that simply never brought it up.

    Idempotent: if the score columns already exist they are left untouched.
    Returns the same DataFrame (mutated in place) for convenience.
    """
    score_cols = [f"sentiment_{aspect}_score" for aspect in ASPECTS]
    have_scores = all(col in df.columns for col in score_cols)
    have_mentions = all(f"mentions_{aspect}" in df.columns for aspect in ASPECTS)

    if have_scores and have_mentions:
        return df

    if "aspect_sentiments" not in df.columns:
        return df

    if not have_scores:
        parsed = df["aspect_sentiments"].apply(parse_aspect_sentiments)
        for aspect in ASPECTS:
            labels = parsed.apply(lambda d, a=aspect: d[a])
            df[f"sentiment_{aspect}"] = labels
            df[f"sentiment_{aspect}_score"] = labels.map(SENTIMENT_SCORE_MAP).fillna(0.0)

    if not have_mentions:
        mentions_col = df["aspect_mentions"] if "aspect_mentions" in df.columns else None
        if mentions_col is None:
            for aspect in ASPECTS:
                df[f"mentions_{aspect}"] = True
        else:
            parsed_mentions = mentions_col.apply(parse_aspect_mentions)
            for aspect in ASPECTS:
                df[f"mentions_{aspect}"] = parsed_mentions.apply(lambda d, a=aspect: d[a])

    return df
