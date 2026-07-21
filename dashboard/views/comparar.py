"""
Comparison Page - Compare multiple restaurants side by side - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from dashboard.utils.aspects import ASPECT_LABELS, mention_mask
from dashboard.utils.restaurants import format_restaurant_label, restaurant_directory


def _hex_to_rgba(hex_color: str, alpha: float = 0.2) -> str:
    """Convert a #RRGGBB hex string to an rgba() string with the given alpha."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def render(df: pd.DataFrame):
    """Render the Comparison page with enhanced UI."""

    st.markdown("### Selecciona restaurantes para comparar")

    # One row per restaurant, even when a restaurant carries two spellings from
    # the two sources.
    restaurants = restaurant_directory(df)

    # Narrow the (long) selector list before choosing.
    query = st.text_input("Buscar restaurante", key="comparar_search",
                          placeholder="Escribe parte del nombre o la cocina...")
    if query.strip():
        needle = query.strip().lower()
        haystack = restaurants["restaurant_name"].fillna("").astype(str).str.lower()
        if "category" in restaurants.columns:
            haystack = haystack + " " + restaurants["category"].fillna("").astype(str).str.lower()
        restaurants = restaurants[haystack.str.contains(needle, regex=False)]

    if restaurants.empty:
        st.warning("Ningún restaurante coincide con esa búsqueda.")
        return

    lookup = restaurants.set_index("restaurant_id")

    def _format(rid):
        return format_restaurant_label(lookup.loc[rid])

    # Restaurant selector with better UI
    selected_restaurants = st.multiselect(
        "Elige restaurantes para comparar (2-5):",
        options=restaurants["restaurant_id"].tolist(),
        format_func=_format,
        max_selections=5,
        placeholder="Selecciona restaurantes"
    )

    if len(selected_restaurants) < 2:
        st.info("Selecciona al menos 2 restaurantes para comparar.")
        return

    # Filter data for selected restaurants
    compare_df = df[df["restaurant_id"].isin(selected_restaurants)]

    # Restaurant info cards
    st.markdown("#### Información de restaurantes")

    info_cols = ["restaurant_name", "category", "price_range", "overall_rating"]
    info_df = compare_df.groupby("restaurant_id")[info_cols].first().reset_index()[info_cols]
    info_df.columns = ["Nombre", "Categoría", "Rango de precio", "Calificación"]

    st.dataframe(
        info_df,
        width="stretch",
        hide_index=True,
        column_config={"Calificación": st.column_config.NumberColumn(format="%.2f ")}
    )

    # Charts
    st.markdown("---")
    st.markdown("#### Comparación de calificaciones")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Calificación general")

        ratings = compare_df.groupby("restaurant_id")["overall_rating"].mean().reset_index()
        ratings = ratings.merge(
            restaurants[["restaurant_id", "restaurant_name"]],
            on="restaurant_id"
        )

        fig = go.Figure()

        for _, row in ratings.iterrows():
            color = "#28a745" if row["overall_rating"] >= 4.5 else "#ffc107" if row["overall_rating"] >= 4 else "#dc3545"

            fig.add_trace(go.Bar(
                x=[row["restaurant_name"]],
                y=[row["overall_rating"]],
                marker_color=color,
                text=f"{row['overall_rating']:.2f}",
                textposition='auto',
                name=row["restaurant_name"]
            ))

        fig.update_layout(
            showlegend=False,
            height=350,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            yaxis=dict(range=[0, 5.5]),
            yaxis_title="Calificación"
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.markdown("##### Calificación por aspecto (radar)")

        aspects = ["comida", "servicio", "precio", "ambiente"]
        sentiment_cols = [f"sentiment_{a}_score" for a in aspects]
        available_cols = [col for col in sentiment_cols if col in compare_df.columns]

        if available_cols:
            # Average only the reviews that mention each aspect, so a restaurant
            # nobody discussed the price of does not look "neutral on price".
            radar_rows = []
            for rid, group in compare_df.groupby("restaurant_id"):
                row = {"restaurant_id": rid}
                for col in available_cols:
                    aspect = col.replace("sentiment_", "").replace("_score", "")
                    mask = mention_mask(group, aspect)
                    values = group.loc[mask, col].dropna()
                    row[col] = float(values.mean()) if len(values) else 0.0
                radar_rows.append(row)

            radar_data = pd.DataFrame(radar_rows).merge(
                restaurants[["restaurant_id", "restaurant_name"]],
                on="restaurant_id"
            )

            fig = go.Figure()

            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']

            for i, (_, row) in enumerate(radar_data.iterrows()):
                values = [row[col] if pd.notna(row[col]) else 0 for col in available_cols]
                labels = [col.replace("sentiment_", "").replace("_score", "") for col in available_cols]

                fig.add_trace(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=labels + [labels[0]],
                    name=row["restaurant_name"][:20],
                    fill="toself",
                    fillcolor=_hex_to_rgba(colors[i % len(colors)], 0.2),
                    line=dict(color=colors[i % len(colors)], width=2)
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[-1, 1],
                        tickfont=dict(color='#FAFAFA')
                    ),
                    bgcolor='rgba(0,0,0,0)'
                ),
                showlegend=True,
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FAFAFA'),
                legend=dict(orientation="h", yanchor="bottom", y=-0.4)
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No hay datos de sentimiento disponibles para el gráfico de radar.")

    # Review count
    st.markdown("---")
    st.markdown("#### Cantidad de reseñas")

    review_counts = compare_df.groupby("restaurant_id").size().reset_index(name="review_count")
    review_counts = review_counts.merge(
        restaurants[["restaurant_id", "restaurant_name"]],
        on="restaurant_id"
    )

    fig = go.Figure()

    for _, row in review_counts.iterrows():
        fig.add_trace(go.Bar(
            x=[row["restaurant_name"]],
            y=[row["review_count"]],
            marker_color='#4ECDC4',
            text=f"{row['review_count']}",
            textposition='auto'
        ))

    fig.update_layout(
        showlegend=False,
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#FAFAFA'),
        yaxis_title="Número de reseñas"
    )
    st.plotly_chart(fig, width="stretch")

    # Sample reviews
    st.markdown("---")
    st.markdown("#### Reseñas de muestra")

    cols = st.columns(3)

    for i, rest_id in enumerate(selected_restaurants[:3]):
        rest_name = restaurants[restaurants["restaurant_id"] == rest_id]["restaurant_name"].values[0]
        rest_reviews = compare_df[compare_df["restaurant_id"] == rest_id]["review_text"].dropna().head(2)

        with cols[i]:
            st.markdown(f"**{rest_name}**")
            for review in rest_reviews:
                with st.expander("Ver reseña"):
                    st.write(review[:200] + "..." if len(str(review)) > 200 else review)
