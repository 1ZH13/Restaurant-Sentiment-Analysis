"""
Clustering Page - Visualize restaurant clusters.

Clusters are a property of restaurants, not of reviews, so every count on this
page is reported per restaurant and the review count is shown separately. The
descriptive cluster names produced by the pipeline are used instead of bare
"Grupo 3" labels.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.config import CLUSTER_COLORS
from dashboard.utils.aspects import ASPECTS, ASPECT_LABELS, mention_mask, overall_sentiment
from dashboard.utils.restaurants import restaurant_directory

TRANSPARENT = "rgba(0,0,0,0)"


def _layout(**kwargs) -> dict:
    base = dict(plot_bgcolor=TRANSPARENT, paper_bgcolor=TRANSPARENT,
                font=dict(color="#FAFAFA"), showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10))
    base.update(kwargs)
    return base


def _cluster_name(df: pd.DataFrame, cluster_id) -> str:
    if "cluster_name" not in df.columns:
        return f"Grupo {int(cluster_id)}"
    names = df.loc[df["cluster"] == cluster_id, "cluster_name"].dropna()
    return str(names.iloc[0]) if len(names) else f"Grupo {int(cluster_id)}"


def _color(cluster_id) -> str:
    return CLUSTER_COLORS[int(cluster_id) % len(CLUSTER_COLORS)]


def render(df: pd.DataFrame):
    """Render the Clustering page."""

    if "cluster" not in df.columns or df["cluster"].isna().all():
        st.warning("El agrupamiento aun no se ha ejecutado. Corre `python run_pipeline.py`.")
        return

    data = df[df["cluster"].notna()].copy()
    cluster_ids = sorted(data["cluster"].unique())

    st.markdown("### Grupos de restaurantes")
    st.caption("El agrupamiento (K-Means) se calcula por restaurante a partir de su "
               "calificacion, sentimiento por aspecto, nivel de precio y volumen de resenas.")

    _render_cards(data, cluster_ids)
    st.markdown("---")
    _render_overview_charts(data, cluster_ids)
    st.markdown("---")
    _render_profiles(data, cluster_ids)
    st.markdown("---")
    _render_members(data, cluster_ids)
    st.markdown("---")
    _render_scatter(data)


def _render_cards(data: pd.DataFrame, cluster_ids) -> None:
    columns = st.columns(len(cluster_ids))
    for col, cid in zip(columns, cluster_ids):
        subset = data[data["cluster"] == cid]
        n_restaurants = subset["restaurant_id"].nunique()
        noun = "restaurante" if n_restaurants == 1 else "restaurantes"
        with col:
            st.markdown(f"""
            <div style="background-color: #1E2530; padding: 16px; border-radius: 12px;
                        border: 1px solid {_color(cid)}; text-align: center; height: 100%;">
                <h4 style="margin: 0; color: {_color(cid)};">{_cluster_name(data, cid)}</h4>
                <p style="margin: 8px 0 0 0; font-size: 24px; color: #FAFAFA;">{n_restaurants}</p>
                <p style="margin: 0; color: #A0AEC0;">{noun}</p>
                <p style="margin: 4px 0 0 0; color: #718096; font-size: 13px;">
                    {len(subset)} resenas</p>
            </div>
            """, unsafe_allow_html=True)


def _render_overview_charts(data: pd.DataFrame, cluster_ids) -> None:
    col1, col2 = st.columns(2)
    names = [_cluster_name(data, cid) for cid in cluster_ids]
    colors = [_color(cid) for cid in cluster_ids]

    with col1:
        st.markdown("#### Restaurantes por grupo")
        counts = [data[data["cluster"] == cid]["restaurant_id"].nunique() for cid in cluster_ids]
        fig = go.Figure(go.Pie(labels=names, values=counts, hole=0.5,
                               marker=dict(colors=colors)))
        fig.update_traces(hovertemplate="%{label}<br>%{value} restaurantes<extra></extra>")
        fig.update_layout(**_layout(height=400, showlegend=True,
                                    legend=dict(orientation="h", y=-0.15)))
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Calificacion promedio por grupo")
        ratings = [data[data["cluster"] == cid]["overall_rating"].mean() for cid in cluster_ids]
        fig = go.Figure(go.Bar(
            x=names, y=ratings, marker_color=colors,
            text=[f"{r:.2f}" if pd.notna(r) else "s/d" for r in ratings],
            textposition="auto",
        ))
        fig.update_layout(**_layout(height=400, yaxis=dict(range=[0, 5.4],
                                                           title="Calificacion promedio")))
        st.plotly_chart(fig, width="stretch")


def _render_profiles(data: pd.DataFrame, cluster_ids) -> None:
    st.markdown("#### Perfiles de grupo")

    rows = []
    for cid in cluster_ids:
        subset = data[data["cluster"] == cid]
        row = {
            "Grupo": _cluster_name(data, cid),
            "Restaurantes": subset["restaurant_id"].nunique(),
            "Resenas": len(subset),
            "Calificacion": round(subset["overall_rating"].mean(), 2)
            if subset["overall_rating"].notna().any() else None,
        }
        if "price_level" in subset.columns and subset["price_level"].notna().any():
            row["Nivel de precio"] = round(subset["price_level"].mean(), 2)

        for aspect in ASPECTS:
            score_col = f"sentiment_{aspect}_score"
            if score_col in subset.columns:
                mask = mention_mask(subset, aspect)
                values = subset.loc[mask, score_col].dropna()
                row[ASPECT_LABELS[aspect]] = round(float(values.mean()), 2) if len(values) else None
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("Los valores de sentimiento van de -1 a +1 y promedian solo las resenas "
               "que mencionan cada aspecto. El nivel de precio va de 1 ($) a 4 ($$$$).")


def _render_members(data: pd.DataFrame, cluster_ids) -> None:
    st.markdown("#### Restaurantes de cada grupo")

    selected = st.selectbox(
        "Selecciona un grupo:",
        options=cluster_ids,
        format_func=lambda cid: _cluster_name(data, cid),
        key="clustering_group",
    )

    subset = data[data["cluster"] == selected]
    query = st.text_input("Buscar dentro del grupo", key="clustering_search",
                          placeholder="Nombre del restaurante...")
    if query.strip():
        mask = subset["restaurant_name"].astype(str).str.lower().str.contains(
            query.strip().lower(), regex=False)
        subset = subset[mask]

    if subset.empty:
        st.info("Ningun restaurante coincide con esa busqueda.")
        return

    # restaurant_directory collapses the two spellings a unified restaurant can
    # have, so it is not listed twice.
    members = (
        restaurant_directory(subset)
        .rename(columns={"restaurant_name": "Restaurante", "rating": "Calificacion",
                         "resenas": "Resenas"})
        .sort_values("Calificacion", ascending=False)
    )[["Restaurante", "Calificacion", "Resenas"]]

    st.dataframe(
        members, width="stretch", hide_index=True,
        column_config={"Calificacion": st.column_config.NumberColumn(format="%.2f")},
    )
    st.caption(f"{len(members)} restaurantes en este grupo.")


def _render_scatter(data: pd.DataFrame) -> None:
    st.markdown("#### Mapa de restaurantes: calificacion vs. sentimiento")

    if "overall_rating" not in data.columns:
        return

    scatter_source = data.copy()
    scatter_source["_sentiment"] = overall_sentiment(scatter_source)

    points = (
        scatter_source.groupby(["restaurant_id", "restaurant_name", "cluster"], as_index=False)
                      .agg(rating=("overall_rating", "mean"),
                           sentiment=("_sentiment", "mean"),
                           resenas=("review_text", "size"))
                      .dropna(subset=["rating", "sentiment"])
    )

    if points.empty:
        st.info("No hay datos suficientes para el mapa.")
        return

    # cluster is numeric; casting to string makes Plotly treat it as a category
    # so the discrete cluster palette is actually applied.
    points["Grupo"] = points["cluster"].apply(lambda cid: _cluster_name(data, cid))

    fig = px.scatter(
        points,
        x="rating",
        y="sentiment",
        color="Grupo",
        size="resenas",
        size_max=22,
        hover_name="restaurant_name",
        hover_data={"rating": ":.2f", "sentiment": ":.2f", "resenas": True,
                    "Grupo": True, "cluster": False},
        color_discrete_sequence=CLUSTER_COLORS,
        labels={"rating": "Calificacion promedio", "sentiment": "Sentimiento promedio"},
    )
    fig.update_layout(
        plot_bgcolor=TRANSPARENT, paper_bgcolor=TRANSPARENT,
        font=dict(color="#FAFAFA"), height=520,
        xaxis_title="Calificacion promedio", yaxis_title="Sentimiento promedio",
        legend_title="Grupo", margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Cada punto es un restaurante; el tamano refleja cuantas resenas tiene.")
