"""
Aspect-sentiment helpers for the dashboard.

A review that never mentions the price is not evidence that the price is
average. Averaging its 0 alongside real opinions dragged every aspect towards
zero and produced charts that showed almost nothing. These helpers average only
the reviews that actually discussed an aspect and report the coverage alongside,
so a bar is always labelled with how many reviews it stands on.
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd

ASPECTS = ("comida", "servicio", "precio", "ambiente")
ASPECT_LABELS = {
    "comida": "Comida",
    "servicio": "Servicio",
    "precio": "Precio",
    "ambiente": "Ambiente",
}


def mention_mask(df: pd.DataFrame, aspect: str) -> pd.Series:
    """Boolean mask of rows whose review actually discussed ``aspect``.

    Datasets produced before mention tracking existed have no flag column; those
    fall back to "every row counts", preserving the old behaviour.
    """
    column = f"mentions_{aspect}"
    if column not in df.columns:
        return pd.Series(True, index=df.index)

    values = df[column]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])


def aspect_summary(df: pd.DataFrame, aspect: str) -> Optional[Dict]:
    """Mean sentiment for one aspect plus the coverage behind it."""
    score_col = f"sentiment_{aspect}_score"
    if score_col not in df.columns or len(df) == 0:
        return None

    mask = mention_mask(df, aspect)
    mentioned = df.loc[mask, score_col].dropna()
    if len(mentioned) == 0:
        return {
            "aspect": aspect,
            "label": ASPECT_LABELS.get(aspect, aspect.capitalize()),
            "mean": None,
            "mentions": 0,
            "total": len(df),
            "coverage": 0.0,
        }

    return {
        "aspect": aspect,
        "label": ASPECT_LABELS.get(aspect, aspect.capitalize()),
        "mean": float(mentioned.mean()),
        "mentions": int(len(mentioned)),
        "total": int(len(df)),
        "coverage": float(len(mentioned) / len(df)),
    }


def all_aspect_summaries(df: pd.DataFrame) -> List[Dict]:
    """Summaries for every aspect that has data, in a stable order."""
    summaries = []
    for aspect in ASPECTS:
        summary = aspect_summary(df, aspect)
        if summary is not None and summary["mentions"] > 0:
            summaries.append(summary)
    return summaries


def overall_sentiment(df: pd.DataFrame) -> pd.Series:
    """Per-review overall sentiment, averaging only the aspects it mentioned.

    Returned as a new Series so callers never mutate the cached DataFrame.
    """
    score_cols = [f"sentiment_{a}_score" for a in ASPECTS if f"sentiment_{a}_score" in df.columns]
    if not score_cols:
        return pd.Series(dtype=float, index=df.index)

    scores = df[score_cols].astype(float)
    weights = pd.DataFrame(
        {f"sentiment_{a}_score": mention_mask(df, a).astype(float)
         for a in ASPECTS if f"sentiment_{a}_score" in df.columns},
        index=df.index,
    )

    weighted_sum = (scores * weights).sum(axis=1)
    counts = weights.sum(axis=1)
    # Reviews that mention nothing fall back to a plain average of all aspects.
    result = weighted_sum.div(counts.where(counts > 0))
    return result.fillna(scores.mean(axis=1))


def sentiment_category(scores: pd.Series) -> pd.Series:
    """Bucket numeric sentiment into Positivo / Neutral / Negativo."""
    return scores.apply(
        lambda x: "Positivo" if x > 0.1 else "Negativo" if x < -0.1 else "Neutral"
    )


def coverage_note(summaries: List[Dict]) -> str:
    """One-line caption stating how many reviews back each aspect."""
    if not summaries:
        return ""
    parts = [f"{s['label']} {s['mentions']}" for s in summaries]
    total = summaries[0]["total"]
    return (f"Promedios calculados solo sobre las reseñas que mencionan cada aspecto "
            f"(de {total}): " + " · ".join(parts) + ".")
