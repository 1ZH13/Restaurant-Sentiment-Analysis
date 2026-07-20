"""
Sentiment Analysis Page.

Averages here count only the reviews that actually discussed an aspect. Counting
silence as "neutral" pulled every aspect towards zero - price in particular was
neutral in 87% of rows simply because most reviews never mention it, which made
the chart look like nobody had an opinion about anything.

This page also no longer assigns columns onto the incoming DataFrame: that frame
comes from st.cache_data and writing to it leaks state across pages.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.aspects import (
    ASPECTS,
    ASPECT_LABELS,
    all_aspect_summaries,
    coverage_note,
    mention_mask,
    overall_sentiment,
    sentiment_category,
)
from dashboard.utils.filters import render_filters

TRANSPARENT = "rgba(0,0,0,0)"


def _layout(**kwargs) -> dict:
    base = dict(plot_bgcolor=TRANSPARENT, paper_bgcolor=TRANSPARENT,
                font=dict(color="#FAFAFA"), showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10))
    base.update(kwargs)
    return base


def render(df: pd.DataFrame):
    """Render the Sentiment Analysis page."""

    if not any(f"sentiment_{a}_score" in df.columns for a in ASPECTS):
        st.warning("El analisis de sentimiento aun no se ha ejecutado.")
        return

    filtered = render_filters(df, key_prefix="sentimiento")
    if len(filtered) == 0:
        return

    # Work on a local copy so the cached frame is never modified.
    data = filtered.copy()
    data["_sentiment"] = overall_sentiment(data)
    data["_category"] = sentiment_category(data["_sentiment"])

    st.markdown("---")
    _render_kpis(data)

    st.markdown("---")
    _render_aspect_charts(data)

    st.markdown("---")
    _render_heatmap(data)

    st.markdown("---")
    _render_extreme_reviews(data)


def _render_kpis(data: pd.DataFrame) -> None:
    st.markdown("### Resumen de sentimiento")
    counts = data["_category"].value_counts()
    total = len(data)

    cards = [
        ("Positivo", counts.get("Positivo", 0), "#28a745"),
        ("Neutral", counts.get("Neutral", 0), "#ffc107"),
        ("Negativo", counts.get("Negativo", 0), "#dc3545"),
    ]

    columns = st.columns(4)
    for col, (label, count, color) in zip(columns, cards):
        pct = (count / total * 100) if total else 0
        with col:
            st.markdown(f"""
            <div style="background-color: {color}26; padding: 16px; border-radius: 12px;
                        border-left: 4px solid {color};">
                <h2 style="margin: 0; color: {color};">{pct:.1f}%</h2>
                <p style="margin: 4px 0 0 0; color: #A0AEC0;">{label} ({count} resenas)</p>
            </div>
            """, unsafe_allow_html=True)

    avg = data["_sentiment"].mean()
    color = "#28a745" if avg > 0.1 else "#ffc107" if avg > -0.1 else "#dc3545"
    with columns[3]:
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 16px; border-radius: 12px;
                    border-left: 4px solid {color};">
            <h2 style="margin: 0; color: {color};">{avg:+.2f}</h2>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">Puntaje promedio</p>
        </div>
        """, unsafe_allow_html=True)


def _render_aspect_charts(data: pd.DataFrame) -> None:
    summaries = all_aspect_summaries(data)
    if not summaries:
        st.info("No hay aspectos con datos suficientes.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Sentimiento promedio por aspecto")
        colors = ["#28a745" if s["mean"] > 0.1 else "#ffc107" if s["mean"] > -0.1 else "#dc3545"
                  for s in summaries]
        fig = go.Figure(go.Bar(
            x=[s["label"] for s in summaries],
            y=[s["mean"] for s in summaries],
            marker_color=colors,
            text=[f"{s['mean']:.2f}" for s in summaries],
            textposition="auto",
            customdata=[[s["mentions"], s["coverage"] * 100] for s in summaries],
            hovertemplate="%{x}<br>Promedio: %{y:.2f}"
                          "<br>%{customdata[0]} resenas (%{customdata[1]:.0f}%)<extra></extra>",
        ))
        fig.update_layout(**_layout(height=400, yaxis=dict(title="Sentimiento", range=[-1, 1])))
        st.plotly_chart(fig, width="stretch")
        st.caption(coverage_note(summaries))

    with col2:
        st.markdown("#### Desglose de opiniones por aspecto")
        # A stacked breakdown shows how many positives/neutrals/negatives sit
        # behind each average, rather than only the average itself.
        fig = go.Figure()
        for label, color in (("Positivo", "#28a745"), ("Neutral", "#ffc107"), ("Negativo", "#dc3545")):
            values = []
            for summary in summaries:
                aspect = summary["aspect"]
                mask = mention_mask(data, aspect)
                scores = data.loc[mask, f"sentiment_{aspect}_score"]
                bucket = sentiment_category(scores)
                values.append(int((bucket == label).sum()))
            fig.add_trace(go.Bar(name=label, x=[s["label"] for s in summaries],
                                 y=values, marker_color=color))

        fig.update_layout(**_layout(height=400, barmode="stack", showlegend=True,
                                    yaxis_title="Resenas", legend=dict(orientation="h", y=-0.2)))
        st.plotly_chart(fig, width="stretch")


def _render_heatmap(data: pd.DataFrame) -> None:
    category_col = "category_primary" if "category_primary" in data.columns else "category"
    if category_col not in data.columns:
        return

    st.markdown("### Sentimiento por tipo de cocina")

    # Only cuisines with enough reviews produce a meaningful average.
    min_reviews = 5
    counts = data[category_col].dropna().value_counts()
    cuisines = counts[counts >= min_reviews].head(12).index.tolist()

    if not cuisines:
        st.info(f"Ninguna cocina alcanza {min_reviews} resenas con estos filtros.")
        return

    matrix, labels, hover = [], [], []
    for cuisine in cuisines:
        subset = data[data[category_col] == cuisine]
        row, hover_row = [], []
        for aspect in ASPECTS:
            score_col = f"sentiment_{aspect}_score"
            if score_col not in subset.columns:
                row.append(None)
                hover_row.append("sin datos")
                continue
            mask = mention_mask(subset, aspect)
            values = subset.loc[mask, score_col].dropna()
            row.append(float(values.mean()) if len(values) else None)
            hover_row.append(f"{len(values)} resenas")
        matrix.append(row)
        hover.append(hover_row)
        labels.append(f"{cuisine} ({len(subset)})")

    fig = px.imshow(
        matrix,
        x=[ASPECT_LABELS[a] for a in ASPECTS],
        y=labels,
        color_continuous_scale="RdYlGn",
        range_color=[-1, 1],
        labels=dict(x="Aspecto", y="Cocina", color="Sentimiento"),
        text_auto=".2f",
        aspect="auto",
    )
    fig.update_traces(customdata=hover,
                      hovertemplate="%{y}<br>%{x}: %{z:.2f}<br>%{customdata}<extra></extra>")
    fig.update_layout(plot_bgcolor=TRANSPARENT, paper_bgcolor=TRANSPARENT,
                      font=dict(color="#FAFAFA"), height=460,
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Solo se muestran cocinas con al menos {min_reviews} resenas. "
               "Entre parentesis, el numero de resenas de cada cocina.")


def _render_extreme_reviews(data: pd.DataFrame) -> None:
    st.markdown("### Resenas destacadas")
    col1, col2 = st.columns(2)

    def _cards(subset: pd.DataFrame, color: str, empty_message: str) -> None:
        if subset.empty:
            st.info(empty_message)
            return
        for _, row in subset.iterrows():
            name = row.get("restaurant_name", "Desconocido")
            score = row.get("_sentiment", 0)
            text = str(row.get("review_text", ""))
            preview = text[:220] + ("..." if len(text) > 220 else "")
            st.markdown(f"""
            <div style="background-color: {color}1A; padding: 12px; border-radius: 8px;
                        margin-bottom: 8px; border-left: 3px solid {color};">
                <strong style="color: {color};">{name}</strong>
                <span style="color: #A0AEC0; float: right;">{score:+.2f}</span>
                <p style="margin: 8px 0 0 0; color: #FAFAFA;">{preview}</p>
            </div>
            """, unsafe_allow_html=True)

    with col1:
        st.markdown("#### Mas positivas")
        _cards(data.nlargest(5, "_sentiment"), "#28a745", "Sin resenas positivas destacadas.")

    with col2:
        st.markdown("#### Mas negativas")
        negatives = data[data["_sentiment"] < 0].nsmallest(5, "_sentiment")
        _cards(negatives, "#dc3545",
               "No hay resenas negativas con estos filtros. "
               "Las resenas de estas fuentes son mayoritariamente positivas.")
