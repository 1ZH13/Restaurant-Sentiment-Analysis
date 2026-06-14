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

    st.markdown("### Find Your Perfect Restaurant")

    if RestaurantRecommender is None:
        st.error("Recommender module not available. Please check your installation.")
        return

    # Introduction card
    st.markdown("""
    <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; margin-bottom: 24px;">
        <p style="margin: 0; color: #A0AEC0;">Tell us your preferences and we'll find the best restaurants for you based on sentiment analysis and cluster insights.</p>
    </div>
    """, unsafe_allow_html=True)

    # Preference inputs
    st.markdown("#### What are you looking for?")

    col1, col2 = st.columns(2)

    with col1:
        categories = ["Any"] + df["category"].dropna().unique().tolist()
        selected_category = st.selectbox("Cuisine Type", categories)

    with col2:
        price_ranges = ["Any", "$", "$$ - $$$", "$$$ - $$$$", "$$$$"]
        selected_price = st.selectbox("Price Range", price_ranges)

    # Priority aspects
    st.markdown("#### What matters most to you? (select up to 2)")

    col1, col2, col3, col4 = st.columns(4)

    priority_aspects = []
    with col1:
        if st.checkbox("Food Quality", value=True):
            priority_aspects.append("comida")
    with col2:
        if st.checkbox("Service", value=True):
            priority_aspects.append("servicio")
    with col3:
        if st.checkbox("Price", value=False):
            priority_aspects.append("precio")
    with col4:
        if st.checkbox("Atmosphere", value=False):
            priority_aspects.append("ambiente")

    # Location
    if "location" in df.columns:
        locations = ["Any"] + df["location"].dropna().unique().tolist()
        selected_location = st.selectbox("Neighborhood (optional)", locations)
    else:
        selected_location = "Any"

    st.markdown("---")

    # Generate recommendations
    if st.button("Get Personalized Recommendations", type="primary", use_container_width=True):

        preferences = {
            "category": None if selected_category == "Any" else selected_category,
            "max_price": None if selected_price == "Any" else selected_price,
            "priority_aspects": priority_aspects,
            "location": None if selected_location == "Any" else selected_location
        }

        with st.spinner("Analyzing restaurants..."):
            recommender = RestaurantRecommender(df)
            recommendations = recommender.recommend(preferences, top_n=5)

        if recommendations:
            st.markdown("### Your Top Recommendations")

            for i, rec in enumerate(recommendations, 1):
                match_color = "#28a745" if rec.match_score >= 80 else "#ffc107" if rec.match_score >= 60 else "#dc3545"

                st.markdown(f"""
                <div style="background-color: #1E2530; padding: 20px; border-radius: 12px; margin-bottom: 16px; border-left: 4px solid {match_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #FAFAFA;">#{i} {rec.restaurant_name}</h3>
                        <div style="background-color: {match_color}33; padding: 8px 16px; border-radius: 8px;">
                            <span style="color: {match_color}; font-weight: bold;">{rec.match_score:.0f}% Match</span>
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
            st.warning("No recommendations found. Try adjusting your preferences.")
    else:
        # Default recommendation display when no interaction
        st.markdown("""
        <div style="background-color: rgba(78, 205, 196, 0.1); padding: 24px; border-radius: 12px; text-align: center; border: 1px dashed #4ECDC4;">
            <h4 style="color: #4ECDC4; margin: 0;">Ready to Help!</h4>
            <p style="color: #A0AEC0; margin-top: 12px;">Select your preferences above and click the button to get personalized restaurant recommendations.</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    df = pd.read_csv("data/processed/restaurants_clustered.csv")
    render(df)
