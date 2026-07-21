"""
Restaurant Sentiment Analysis Dashboard
Main entry point for Streamlit application - Enhanced UX/UI

Uses Streamlit's native multipage navigation (st.navigation / st.Page). Each
view lives in dashboard/views/ and exposes a ``render(df)`` function.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.config import CUSTOM_CSS
from dashboard.views import (
    overview,
    comparar,
    sentimiento,
    clustering,
    recomendaciones,
    detalle,
    asistente,
)
from dashboard.utils.i18n import translate_dashboard_dataframe
from src.sentiment.aspect_scores import derive_aspect_sentiment_scores

st.set_page_config(
    page_title="Analizador de Restaurantes - Panamá",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply dark theme CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

I18N_VERSION = "es-dashboard-content-v3"


@st.cache_data
def load_data():
    """Load processed data with caching."""
    _ = I18N_VERSION
    try:
        df = pd.read_csv("data/processed/restaurants_clustered.csv")
    except FileNotFoundError:
        return None
    df = translate_dashboard_dataframe(df)
    # Ensure sentiment score columns exist even if the CSV predates the
    # sentiment-aware pipeline, so all pages render sentiment correctly.
    return derive_aspect_sentiment_scores(df)


def _render_no_data():
    """Show the onboarding message when no processed data is available."""
    st.markdown("""
    <div style="background-color: #1E2530; padding: 40px; border-radius: 12px; text-align: center;">
        <h2 style="color: #FF6B6B;">No se encontraron datos</h2>
        <p style="color: #A0AEC0; margin-top: 16px;">
            Ejecuta primero el pipeline para generar los datos.
        </p>
        <code style="display: block; margin-top: 20px; padding: 16px; background-color: #0E1117; border-radius: 8px;">
            python -m src.preprocessing.cleaner<br>
            python -m src.preprocessing.normalizer<br>
            python -m src.clustering.restaurant_clusterer
        </code>
    </div>
    """, unsafe_allow_html=True)


def _page(render_fn, title, subtitle):
    """Build a no-arg page callable that loads data and renders a view."""
    def page():
        df = load_data()

        st.markdown(f"""
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0;">{title}</h1>
            <p style="color: #A0AEC0; margin-top: 8px;">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)

        if df is None:
            _render_no_data()
            return

        render_fn(df)

    return page


SUBTITLE = "Análisis de sentimiento de restaurantes en Ciudad de Panamá"

# Native multipage navigation. url_path values match tests/test_dashboard_e2e.py.
PAGES = [
    st.Page(_page(overview.render, "Resumen", SUBTITLE),
            title="Resumen", url_path="Overview", default=True),
    st.Page(_page(comparar.render, "Comparar", SUBTITLE),
            title="Comparar", url_path="Comparison"),
    st.Page(_page(sentimiento.render, "Sentimiento", SUBTITLE),
            title="Sentimiento", url_path="Sentiment"),
    st.Page(_page(clustering.render, "Agrupamiento", SUBTITLE),
            title="Agrupamiento", url_path="Clustering"),
    st.Page(_page(recomendaciones.render, "Recomendaciones", SUBTITLE),
            title="Recomendaciones", url_path="Recommendations"),
    st.Page(_page(detalle.render, "Detalle", SUBTITLE),
            title="Detalle", url_path="Detail"),
    st.Page(_page(asistente.render, "Asistente", SUBTITLE),
            title="Asistente", url_path="Assistant"),
]


def _render_sidebar():
    """Render the branded sidebar content shown under the page navigation."""
    with st.sidebar:
        st.markdown("## Analizador de Restaurantes")
        st.markdown("---")

        st.markdown("""
        <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; border: 1px solid #2D3748;">
            <h4 style="margin: 0; color: #FF6B6B;">Grupo 5</h4>
            <p style="margin: 8px 0 0 0; color: #A0AEC0; font-size: 14px;">
                Análisis de Reseñas de Restaurantes en Panamá
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Información de datos")

        df = load_data()
        if df is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Restaurantes", df["restaurant_id"].nunique())
            with col2:
                st.metric("Reseñas", len(df))
        else:
            st.warning("No hay datos cargados")


def main():
    """Main application entry point."""
    pg = st.navigation(PAGES, position="sidebar")
    _render_sidebar()
    pg.run()


if __name__ == "__main__":
    main()
