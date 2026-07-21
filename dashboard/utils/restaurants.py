"""
Restaurant-level view of the reviews table.

Pages that offer a restaurant selector need exactly one row per restaurant.
Grouping by ``["restaurant_id", "restaurant_name"]`` does not guarantee that:
when the same venue is listed by both sources under slightly different names
("El Trapiche (Bella Vista)" and "Restaurante El Trapiche Bella Vista"), the
cross-source unification gives them one canonical id but keeps both names, so
the group-by yields two rows sharing an id. Indexing by that id then returns a
DataFrame instead of a row and the selector raises
"The truth value of a Series is ambiguous".
"""

import pandas as pd


def restaurant_directory(df: pd.DataFrame) -> pd.DataFrame:
    """One row per restaurant: id, display name, rating and review count.

    The display name is the most frequent spelling among the restaurant's
    reviews, so the label stays stable regardless of source.
    """
    if df.empty:
        return pd.DataFrame(columns=["restaurant_id", "restaurant_name", "rating", "resenas"])

    grouped = df.groupby("restaurant_id", sort=False)

    directory = pd.DataFrame({
        "restaurant_id": list(grouped.groups.keys()),
    })

    names = grouped["restaurant_name"].agg(
        lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else "Sin nombre"
    )
    directory["restaurant_name"] = directory["restaurant_id"].map(names)

    if "overall_rating" in df.columns:
        directory["rating"] = directory["restaurant_id"].map(grouped["overall_rating"].mean())
    else:
        directory["rating"] = pd.NA

    directory["resenas"] = directory["restaurant_id"].map(grouped.size())

    for column in ("category", "price_range", "price_band", "location"):
        if column in df.columns:
            directory[column] = directory["restaurant_id"].map(grouped[column].first())

    return directory.sort_values("restaurant_name").reset_index(drop=True)


def format_restaurant_label(row: pd.Series, show_reviews: bool = False) -> str:
    """Build a selector label, tolerating restaurants without a rating."""
    rating = f"{row['rating']:.1f}" if pd.notna(row.get("rating")) else "s/c"
    label = f"{rating} - {row['restaurant_name']}"
    if show_reviews and pd.notna(row.get("resenas")):
        label += f" ({int(row['resenas'])} reseñas)"
    return label
