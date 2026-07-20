"""
Overview Page - Dashboard homepage with KPIs and summary statistics.

Filters live at the top and every KPI, chart and table below is computed from
the filtered frame. Previously the filters sat at the bottom of the page and
only printed a row count, so selecting a category changed nothing on screen.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.aspects import all_aspect_summaries, coverage_note, overall_sentiment, sentiment_category
from dashboard.utils.filters import render_filters

TRANSPARENT = "rgba(0,0,0,0)"


def _base_layout(**kwargs) -> dict:
    """Shared Plotly layout so every chart looks the same."""
    layout = dict(
        plot_bgcolor=TRANSPARENT,
        paper_bgcolor=TRANSPARENT,
        font=dict(color="#FAFAFA"),
        showlegend=False,
    )
    layout.update(kwargs)
    return layout


def _kpi_card(value: str, label: str, color: str) -> str:
    return f"""
    <div style="background-color: #1E2530; padding: 20px; border-radius: 12px;
                text-align: center; border: 1px solid #2D3748;">
        <h1 style="margin: 0; color: {color}; font-size: 36px;">{value}</h1>
        <p style="margin: 8px 0 0 0; color: #A0AEC0;">{label}</p>
    </div>
    """


def render(df: pd.DataFrame):
    """Render the Overview page."""

    filtered = render_filters(df, key_prefix="overview")
    if len(filtered) == 0:
        return

    st.markdown("---")
    _render_kpis(filtered)

    st.markdown("---")
    _render_rating_charts(filtered)

    st.markdown("---")
    _render_distribution_charts(filtered)

    st.markdown("---")
    _render_sentiment_charts(filtered)


def _render_kpis(df: pd.DataFrame) -> None:
    st.markdown("### Metricas clave")
    col1, col2, col3, col4 = st.columns(4)

    ratings = df["overall_rating"].dropna() if "overall_rating" in df.columns else pd.Series(dtype=float)
    avg_rating = ratings.mean() if len(ratings) else None

    sentiment = overall_sentiment(df)
    avg_sentiment = sentiment.mean() if len(sentiment.dropna()) else 0.0

    with col1:
        st.markdown(_kpi_card(f"{df['restaurant_id'].nunique()}", "Restaurantes", "#FF6B6B"),
                    unsafe_allow_html=True)
    with col2:
        st.markdown(_kpi_card(f"{len(df)}", "Resenas", "#4ECDC4"), unsafe_allow_html=True)
    with col3:
        if avg_rating is None:
            st.markdown(_kpi_card("s/d", "Calificacion promedio", "#A0AEC0"), unsafe_allow_html=True)
        else:
            color = "#28a745" if avg_rating >= 4.5 else "#ffc107" if avg_rating >= 4 else "#dc3545"
            st.markdown(_kpi_card(f"{avg_rating:.2f}", "Calificacion promedio", color),
                        unsafe_allow_html=True)
            # State the coverage so the number is never read as covering everything.
            if len(ratings) < len(df):
                st.caption(f"basado en {len(ratings)} de {len(df)} resenas con calificacion")
    with col4:
        label = "Positivo" if avg_sentiment > 0.1 else "Neutral" if avg_sentiment > -0.1 else "Negativo"
        color = "#28a745" if avg_sentiment > 0.1 else "#ffc107" if avg_sentiment > -0.1 else "#dc3545"
        st.markdown(_kpi_card(label, "Sentimiento general", color), unsafe_allow_html=True)


def _render_rating_charts(df: pd.DataFrame) -> None:
    st.markdown("### Mejores restaurantes y distribucion de calificaciones")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 10 mejores por calificacion")
        top = (
            df.dropna(subset=["overall_rating"])
              .groupby(["restaurant_id", "restaurant_name"], as_index=False)["overall_rating"]
              .mean()
              .sort_values("overall_rating", ascending=False)
              .head(10)
        )

        if top.empty:
            st.info("No hay calificaciones disponibles con estos filtros.")
        else:
            fig = go.Figure(go.Bar(
                x=top["overall_rating"],
                y=top["restaurant_name"],
                orientation="h",
                marker_color="#4ECDC4",
                text=[f"{v:.2f}" for v in top["overall_rating"]],
                textposition="outside",
                hovertemplate="%{y}<br>Calificacion: %{x:.2f}<extra></extra>",
            ))
            fig.update_layout(**_base_layout(
                height=450,
                yaxis=dict(autorange="reversed", title=""),
                xaxis=dict(title="Calificacion", range=[0, 5.4]),
                margin=dict(l=10, r=10, t=10, b=10),
            ))
            st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Distribucion de calificaciones")
        ratings = df["overall_rating"].dropna()
        if ratings.empty:
            st.info("No hay calificaciones disponibles con estos filtros.")
        else:
            fig = go.Figure(go.Histogram(
                x=ratings,
                nbinsx=20,
                marker_color="#FF6B6B",
                opacity=0.85,
                hovertemplate="Calificacion: %{x:.1f}<br>Resenas: %{y}<extra></extra>",
            ))
            fig.update_layout(**_base_layout(
                height=450,
                xaxis_title="Calificacion",
                yaxis_title="Cantidad de resenas",
                margin=dict(l=10, r=10, t=10, b=10),
            ))
            st.plotly_chart(fig, width="stretch")


def _render_distribution_charts(df: pd.DataFrame) -> None:
    st.markdown("### Distribucion por cocina, precio y zona")
    col1, col2 = st.columns(2)

    category_col = "category_primary" if "category_primary" in df.columns else "category"

    with col1:
        st.markdown("#### Cocinas mas frecuentes")
        if category_col in df.columns:
            counts = df[category_col].dropna().value_counts().head(10)
            if counts.empty:
                st.info("Sin datos de cocina.")
            else:
                fig = go.Figure(go.Bar(
                    x=counts.values,
                    y=counts.index,
                    orientation="h",
                    marker_color="#45B7D1",
                    text=counts.values,
                    textposition="outside",
                ))
                fig.update_layout(**_base_layout(
                    height=400,
                    yaxis=dict(autorange="reversed", title=""),
                    xaxis_title="Resenas",
                    margin=dict(l=10, r=10, t=10, b=10),
                ))
                st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("#### Rango de precio")
        price_col = "price_band" if "price_band" in df.columns else "price_range"
        if price_col in df.columns:
            counts = df[price_col].dropna().value_counts().sort_index()
            if counts.empty:
                st.info("Sin datos de precio.")
            else:
                fig = go.Figure(go.Bar(
                    x=counts.index,
                    y=counts.values,
                    marker_color="#96CEB4",
                    text=counts.values,
                    textposition="auto",
                ))
                fig.update_layout(**_base_layout(
                    height=400,
                    xaxis_title="Rango de precio",
                    yaxis_title="Resenas",
                    margin=dict(l=10, r=10, t=10, b=10),
                ))
                st.plotly_chart(fig, width="stretch")

    if "location" in df.columns:
        st.markdown("#### Zonas con mas resenas")
        zones = df["location"].dropna().value_counts().head(12)
        if not zones.empty:
            fig = go.Figure(go.Bar(
                x=zones.index,
                y=zones.values,
                marker_color="#DDA0DD",
                text=zones.values,
                textposition="auto",
            ))
            fig.update_layout(**_base_layout(
                height=350,
                xaxis_title="Zona",
                yaxis_title="Resenas",
                margin=dict(l=10, r=10, t=10, b=10),
            ))
            st.plotly_chart(fig, width="stretch")


def _render_sentiment_charts(df: pd.DataFrame) -> None:
    summaries = all_aspect_summaries(df)
    if not summaries:
        return

    st.markdown("### Analisis de sentimiento por aspecto")
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
                          "<br>%{customdata[0]} resenas lo mencionan (%{customdata[1]:.0f}%)<extra></extra>",
        ))
        fig.update_layout(**_base_layout(
            height=400,
            yaxis=dict(title="Sentimiento promedio", range=[-1, 1]),
            xaxis_title="Aspecto",
            margin=dict(l=10, r=10, t=10, b=10),
        ))
        st.plotly_chart(fig, width="stretch")
        st.caption(coverage_note(summaries))

    with col2:
        st.markdown("#### Cuantas resenas hablan de cada aspecto")
        fig = go.Figure(go.Bar(
            x=[s["label"] for s in summaries],
            y=[s["coverage"] * 100 for s in summaries],
            marker_color="#4ECDC4",
            text=[f"{s['coverage']*100:.0f}%" for s in summaries],
            textposition="auto",
            hovertemplate="%{x}<br>%{y:.0f}% de las resenas<extra></extra>",
        ))
        fig.update_layout(**_base_layout(
            height=400,
            yaxis=dict(title="% de resenas que lo mencionan", range=[0, 100]),
            xaxis_title="Aspecto",
            margin=dict(l=10, r=10, t=10, b=10),
        ))
        st.plotly_chart(fig, width="stretch")
        st.caption("El precio se comenta mucho menos que la comida: por eso su promedio "
                   "se calcula sobre menos resenas.")

    st.markdown("#### Distribucion general del sentimiento")
    categories = sentiment_category(overall_sentiment(df)).value_counts()
    palette = {"Positivo": "#28a745", "Neutral": "#ffc107", "Negativo": "#dc3545"}
    fig = go.Figure(go.Pie(
        labels=categories.index,
        values=categories.values,
        hole=0.5,
        marker=dict(colors=[palette.get(c, "#4ECDC4") for c in categories.index]),
    ))
    fig.update_layout(**_base_layout(height=380, showlegend=True,
                                     margin=dict(l=10, r=10, t=10, b=10)))
    st.plotly_chart(fig, width="stretch")
