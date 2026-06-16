"""
Recommendations Page - Restaurant recommendation system - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.recommendation.recommender import RestaurantRecommender, RecommendationResult
except ImportError:
    RestaurantRecommender = None


def render(df: pd.DataFrame):
    """Render the Recommendations page with enhanced UI."""

    st.markdown("### Encuentra tu restaurante ideal")

    if RestaurantRecommender is None:
        st.error("El módulo de recomendaciones no está disponible. Revisa la instalación.")
        return

    # Introduction card
    st.markdown("""
    <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; margin-bottom: 24px;">
        <p style="margin: 0; color: #A0AEC0;">Cuéntanos tus preferencias y encontraremos los mejores restaurantes para ti según el análisis de sentimiento y los patrones de agrupamiento.</p>
    </div>
    """, unsafe_allow_html=True)

    # Preference inputs
    st.markdown("#### ¿Qué estás buscando?")

    col1, col2 = st.columns(2)

    with col1:
        categories = ["Cualquiera"] + df["category"].dropna().unique().tolist()
        selected_category = st.selectbox("Tipo de cocina", categories)

    with col2:
        price_ranges = ["Cualquiera", "$", "$$ - $$$", "$$$ - $$$$", "$$$$"]
        selected_price = st.selectbox("Rango de precio", price_ranges)

    # Priority aspects
    st.markdown("#### ¿Qué es lo más importante para ti? (selecciona hasta 2)")

    col1, col2, col3, col4 = st.columns(4)

    priority_aspects = []
    with col1:
        if st.checkbox("Calidad de la comida", value=True):
            priority_aspects.append("comida")
    with col2:
        if st.checkbox("Servicio", value=True):
            priority_aspects.append("servicio")
    with col3:
        if st.checkbox("Precio", value=False):
            priority_aspects.append("precio")
    with col4:
        if st.checkbox("Ambiente", value=False):
            priority_aspects.append("ambiente")

    # Location
    if "location" in df.columns:
        locations = ["Cualquiera"] + df["location"].dropna().unique().tolist()
        selected_location = st.selectbox("Zona (opcional)", locations)
    else:
        selected_location = "Cualquiera"

    st.markdown("---")

    # Generate recommendations
    if st.button("Obtener recomendaciones personalizadas", type="primary", use_container_width=True):

        preferences = {
            "category": None if selected_category == "Cualquiera" else selected_category,
            "max_price": None if selected_price == "Cualquiera" else selected_price,
            "priority_aspects": priority_aspects,
            "location": None if selected_location == "Cualquiera" else selected_location
        }

        with st.spinner("Analizando restaurantes..."):
            recommender = RestaurantRecommender(df)
            recommendations = recommender.recommend(preferences, top_n=5)

        if recommendations:
            st.markdown("### Tus mejores recomendaciones")

            for i, rec in enumerate(recommendations, 1):
                match_color = "#28a745" if rec.match_score >= 80 else "#ffc107" if rec.match_score >= 60 else "#dc3545"

                st.markdown(f"""
                <div style="background-color: #1E2530; padding: 20px; border-radius: 12px; margin-bottom: 16px; border-left: 4px solid {match_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #FAFAFA;">#{i} {rec.restaurant_name}</h3>
                        <div style="background-color: {match_color}33; padding: 8px 16px; border-radius: 8px;">
                            <span style="color: {match_color}; font-weight: bold;">{rec.match_score:.0f}% coincidencia</span>
                        </div>
                    </div>
                    <div style="margin-top: 12px; color: #A0AEC0;">
                        <span style="margin-right: 16px;">{rec.category}</span>
                        <span style="margin-right: 16px;">{rec.price_range}</span>
                        <span>{rec.overall_rating:.1f}/5.0</span>
                    </div>
                    <div style="margin-top: 12px; padding: 12px; background-color: rgba(0,0,0,0.3); border-radius: 8px;">
                        <p style="margin: 0; color: #28a745; font-style: italic;">{rec.explanation}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No se encontraron recomendaciones. Prueba ajustando tus preferencias.")
    else:
        # Default recommendation display when no interaction
        st.markdown("""
        <div style="background-color: rgba(78, 205, 196, 0.1); padding: 24px; border-radius: 12px; text-align: center; border: 1px dashed #4ECDC4;">
            <h4 style="color: #4ECDC4; margin: 0;">Listo para ayudarte</h4>
            <p style="color: #A0AEC0; margin-top: 12px;">Selecciona tus preferencias y presiona el botón para obtener recomendaciones personalizadas.</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    df = pd.read_csv("data/processed/restaurants_clustered.csv")
    render(df)
