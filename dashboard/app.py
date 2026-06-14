"""
Restaurant Sentiment Analysis Dashboard
Main entry point for Streamlit application - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.config import THEME, PAGES, CUSTOM_CSS

st.set_page_config(
    page_title="Restaurant Analyzer - Panama",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply dark theme CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load processed data with caching."""
    try:
        df = pd.read_csv("data/processed/restaurants_clustered.csv")
        return df
    except FileNotFoundError:
        return None


def main():
    """Main application entry point."""

    # Enhanced Sidebar
    with st.sidebar:
        st.markdown("## 🍽️ Restaurant Analyzer")
        st.markdown("---")

        # Navigation with icons
        st.markdown("### 📍 Navigation")
        selected_page = st.radio(
            "Go to",
            list(PAGES.keys()),
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Info card
        st.markdown("""
        <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; border: 1px solid #2D3748;">
            <h4 style="margin: 0; color: #FF6B6B;">🏆 Grupo 5</h4>
            <p style="margin: 8px 0 0 0; color: #A0AEC0; font-size: 14px;">
                Análisis de Reseñas de Restaurantes en Panamá
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Data info
        st.markdown("---")
        st.markdown("### 📊 Data Info")

        df = load_data()
        if df is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Restaurants", df["restaurant_id"].nunique())
            with col2:
                st.metric("Reviews", len(df))
        else:
            st.warning("No data loaded")

    # Load data
    df = load_data()

    if df is None:
        st.markdown("""
        <div style="background-color: #1E2530; padding: 40px; border-radius: 12px; text-align: center;">
            <h2 style="color: #FF6B6B;">⚠️ No Data Found</h2>
            <p style="color: #A0AEC0; margin-top: 16px;">
                Please run the pipeline first to generate data.
            </p>
            <code style="display: block; margin-top: 20px; padding: 16px; background-color: #0E1117; border-radius: 8px;">
                python -m src.ingestion.degusta_scraper<br>
                python -m src.preprocessing.main<br>
                python -m src.clustering.restaurant_clusterer
            </code>
        </div>
        """, unsafe_allow_html=True)
        return

    # Main content header
    st.markdown(f"""
    <div style="margin-bottom: 24px;">
        <h1 style="margin: 0;">🍽️ {selected_page}</h1>
        <p style="color: #A0AEC0; margin-top: 8px;">
            Análisis de sentimiento de restaurantes en Ciudad de Panamá
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Load and run the selected page
    page_file = PAGES[selected_page]
    try:
        page_module = __import__(f"dashboard.pages.{page_file.replace('.py', '')}",
                                fromlist=["render"])

        if hasattr(page_module, "render"):
            page_module.render(df)
        else:
            st.warning(f"Page {selected_page} not fully implemented yet.")
    except Exception as e:
        st.error(f"Error loading page: {str(e)}")


if __name__ == "__main__":
    main()
