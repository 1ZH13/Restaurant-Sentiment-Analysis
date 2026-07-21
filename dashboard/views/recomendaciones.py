"""
Recommendations Page - Restaurant recommendation system.

The price selector used to offer labels ("$$ - $$$") that do not exist in the
data, so the budget preference never matched anything. Options are now built
from the dataset itself, which also means they stay correct if the sources
change their vocabulary.
"""

import pandas as pd
import streamlit as st

try:
    from src.recommendation.recommender import RestaurantRecommender
except ImportError:  # pragma: no cover - surfaced in the UI below
    RestaurantRecommender = None

ANY = "Cualquiera"

ASPECT_CHOICES = {
    "comida": "Calidad de la comida",
    "servicio": "Servicio",
    "precio": "Precio",
    "ambiente": "Ambiente",
}


def _options(df: pd.DataFrame, column: str) -> list:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str)
    values = values[values.str.lower() != "nan"]
    return sorted(values.unique().tolist())


def render(df: pd.DataFrame):
    """Render the Recommendations page."""

    st.markdown("### Encuentra tu restaurante ideal")

    if RestaurantRecommender is None:
        st.error("El modulo de recomendaciones no esta disponible. Revisa la instalacion.")
        return

    st.markdown("""
    <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; margin-bottom: 24px;">
        <p style="margin: 0; color: #A0AEC0;">Cuéntanos qué buscas y combinamos tus preferencias
        con el análisis de sentimiento de las reseñas para ordenar los restaurantes.</p>
    </div>
    """, unsafe_allow_html=True)

    category_col = "category_primary" if "category_primary" in df.columns else "category"
    price_col = "price_range"

    col1, col2 = st.columns(2)
    with col1:
        selected_category = st.selectbox("Tipo de cocina", [ANY] + _options(df, category_col),
                                         key="rec_category")
    with col2:
        # Sort price options by their real ordinal level, not alphabetically.
        price_options = _options(df, price_col)
        if "price_level" in df.columns:
            levels = (df.dropna(subset=[price_col])
                        .groupby(df[price_col].astype(str))["price_level"].min()
                        .sort_values())
            price_options = [p for p in levels.index if p in price_options]
        selected_price = st.selectbox("Presupuesto máximo", [ANY] + price_options,
                                      key="rec_price")

    col3, col4 = st.columns(2)
    with col3:
        selected_zone = st.selectbox("Zona", [ANY] + _options(df, "location"), key="rec_zone")
    with col4:
        min_rating = st.slider("Calificación minima", 0.0, 5.0, 4.0, 0.1, key="rec_rating")

    st.markdown("#### ¿Qué es lo más importante para ti?")
    aspect_cols = st.columns(len(ASPECT_CHOICES))
    priority_aspects = []
    defaults = {"comida": True, "servicio": True, "precio": False, "ambiente": False}
    for col, (aspect, label) in zip(aspect_cols, ASPECT_CHOICES.items()):
        with col:
            if st.checkbox(label, value=defaults[aspect], key=f"rec_aspect_{aspect}"):
                priority_aspects.append(aspect)

    st.markdown("---")

    preferences = {
        "category": None if selected_category == ANY else selected_category,
        "max_price": None if selected_price == ANY else selected_price,
        "priority_aspects": priority_aspects,
        "location": None if selected_zone == ANY else selected_zone,
    }

    pressed = st.button("Obtener recomendaciones", type="primary", width="stretch")

    if pressed:
        # Rating is a hard filter; the rest are scored preferences.
        candidates = df
        if min_rating > 0 and "overall_rating" in df.columns:
            candidates = candidates[candidates["overall_rating"] >= min_rating]

        if candidates.empty:
            st.session_state.pop("rec_results", None)
            st.warning(f"Ningún restaurante alcanza una calificación de {min_rating:.1f}. "
                       "Prueba bajando el mínimo.")
            return

        with st.spinner("Analizando restaurantes..."):
            recommender = RestaurantRecommender(candidates)
            recommendations = recommender.recommend(preferences, top_n=5)

        # Results are kept in session state on purpose. st.button is only True
        # on the run that handled the click, so without this the whole block
        # disappeared as soon as the user touched any other control - which
        # reads as if the page did nothing.
        st.session_state["rec_results"] = {
            "recommendations": recommendations,
            "preferences": preferences,
            "min_rating": min_rating,
            "evaluated": int(candidates["restaurant_id"].nunique()),
        }

    stored = st.session_state.get("rec_results")

    if not stored:
        st.markdown("""
        <div style="background-color: rgba(78, 205, 196, 0.1); padding: 24px; border-radius: 12px;
                    text-align: center; border: 1px dashed #4ECDC4;">
            <h4 style="color: #4ECDC4; margin: 0;">Listo para ayudarte</h4>
            <p style="color: #A0AEC0; margin-top: 12px;">Elige tus preferencias y presiona el botón.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    recommendations = stored["recommendations"]

    if not recommendations:
        st.warning("No se encontraron recomendaciones. Prueba ajustando tus preferencias.")
        return

    st.markdown("### Tus mejores recomendaciones")
    st.caption(f"Evaluamos {stored['evaluated']} restaurantes que cumplen "
               f"la calificación minima de {stored['min_rating']:.1f}.")

    # Tell the user when what they are looking at no longer matches the form.
    if stored["preferences"] != preferences or stored["min_rating"] != min_rating:
        st.info("Cambiaste tus preferencias. Presiona **Obtener recomendaciones** "
                "para actualizar la lista.")

    for i, rec in enumerate(recommendations, 1):
        color = "#28a745" if rec.match_score >= 80 else "#ffc107" if rec.match_score >= 60 else "#dc3545"
        rating = f"{rec.overall_rating:.1f}/5.0" if rec.overall_rating else "sin calificación"
        details = [d for d in (rec.category, rec.price_range) if d and d.lower() != "nan"]

        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 20px; border-radius: 12px;
                    margin-bottom: 16px; border-left: 4px solid {color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #FAFAFA;">#{i} {rec.restaurant_name}</h3>
                <div style="background-color: {color}33; padding: 8px 16px; border-radius: 8px;">
                    <span style="color: {color}; font-weight: bold;">
                        {rec.match_score:.0f}% coincidencia</span>
                </div>
            </div>
            <div style="margin-top: 12px; color: #A0AEC0;">
                {" · ".join(details + [rating])}
            </div>
            <div style="margin-top: 12px; padding: 12px; background-color: rgba(0,0,0,0.3);
                        border-radius: 8px;">
                <p style="margin: 0; color: #28a745; font-style: italic;">{rec.explanation}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
