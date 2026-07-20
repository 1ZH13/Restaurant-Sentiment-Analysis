"""
Shared filtering controls for the dashboard.

Every page previously built its own filter widgets, and the Overview page even
computed a filtered frame that no chart ever used. Centralising the controls
here means a filter is applied exactly once, to the frame every chart on the
page reads from.
"""

from typing import List, Optional

import pandas as pd
import streamlit as st

ALL = "Todos"


def _options(df: pd.DataFrame, column: str) -> List[str]:
    """Sorted unique non-null values of a column, as strings."""
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str)
    values = values[values.str.lower() != "nan"]
    return sorted(values.unique().tolist())


def search_restaurants(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter by a free-text query against restaurant name and category."""
    if not query or not query.strip():
        return df

    needle = query.strip().lower()
    haystack = df["restaurant_name"].fillna("").astype(str).str.lower()
    if "category" in df.columns:
        haystack = haystack + " " + df["category"].fillna("").astype(str).str.lower()

    return df[haystack.str.contains(needle, regex=False)]


def render_filters(df: pd.DataFrame, key_prefix: str,
                   show_cluster: bool = True) -> pd.DataFrame:
    """Render the filter bar and return the filtered DataFrame.

    The returned frame is what the caller must use for *all* of its charts and
    tables, so what the user selects is what the user sees.
    """
    st.markdown("### Filtros y busqueda")

    query = st.text_input(
        "Buscar restaurante",
        key=f"{key_prefix}_search",
        placeholder="Escribe un nombre o tipo de cocina...",
    )

    col1, col2, col3, col4 = st.columns(4)

    category_col = "category_primary" if "category_primary" in df.columns else "category"
    price_col = "price_band" if "price_band" in df.columns else "price_range"

    with col1:
        categories = [ALL] + _options(df, category_col)
        selected_category = st.selectbox("Cocina", categories, key=f"{key_prefix}_cat")

    with col2:
        prices = [ALL] + _options(df, price_col)
        selected_price = st.selectbox("Rango de precio", prices, key=f"{key_prefix}_price")

    with col3:
        zones = [ALL] + _options(df, "location")
        selected_zone = st.selectbox("Zona", zones, key=f"{key_prefix}_zone")

    with col4:
        if show_cluster and "cluster" in df.columns:
            cluster_labels = _cluster_labels(df)
            selected_cluster = st.selectbox(
                "Grupo", [ALL] + list(cluster_labels.values()), key=f"{key_prefix}_cluster"
            )
        else:
            cluster_labels, selected_cluster = {}, ALL

    min_rating = st.slider(
        "Calificacion minima", 0.0, 5.0, 0.0, 0.1, key=f"{key_prefix}_rating"
    )

    filtered = search_restaurants(df, query)

    if selected_category != ALL:
        filtered = filtered[filtered[category_col].astype(str) == selected_category]
    if selected_price != ALL:
        filtered = filtered[filtered[price_col].astype(str) == selected_price]
    if selected_zone != ALL:
        filtered = filtered[filtered["location"].astype(str) == selected_zone]
    if selected_cluster != ALL and cluster_labels:
        inverse = {label: cid for cid, label in cluster_labels.items()}
        filtered = filtered[filtered["cluster"] == inverse[selected_cluster]]
    if min_rating > 0 and "overall_rating" in filtered.columns:
        filtered = filtered[filtered["overall_rating"] >= min_rating]

    _render_summary(df, filtered)
    return filtered


def _cluster_labels(df: pd.DataFrame) -> dict:
    """Map cluster id -> display label, preferring the descriptive name."""
    labels = {}
    for cid in sorted(df["cluster"].dropna().unique()):
        name = None
        if "cluster_name" in df.columns:
            names = df.loc[df["cluster"] == cid, "cluster_name"].dropna()
            if len(names):
                name = str(names.iloc[0])
        labels[cid] = f"{int(cid)} - {name}" if name else f"Grupo {int(cid)}"
    return labels


def _render_summary(full: pd.DataFrame, filtered: pd.DataFrame) -> None:
    """Tell the user exactly how much data the charts below are based on."""
    n_reviews, n_restaurants = len(filtered), filtered["restaurant_id"].nunique()

    if n_reviews == 0:
        st.warning("Ningun restaurante coincide con estos filtros. Prueba a relajarlos.")
        return

    pct = n_reviews / len(full) * 100 if len(full) else 0
    st.caption(
        f"Mostrando **{n_restaurants} restaurantes** y **{n_reviews} resenas** "
        f"({pct:.0f}% del total de {len(full)})."
    )
