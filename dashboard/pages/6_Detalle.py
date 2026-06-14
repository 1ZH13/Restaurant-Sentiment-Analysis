"""
Detail Page - View detailed information about a single restaurant - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render(df: pd.DataFrame):
    """Render the Detail page with enhanced UI."""

    st.markdown("### 🔍 Select a Restaurant")

    # Restaurant selector
    restaurants = df.groupby(["restaurant_id", "restaurant_name"]).agg({
        "overall_rating": "first",
        "category": "first",
        "price_range": "first"
    }).reset_index()

    selected_restaurant_id = st.selectbox(
        "Choose a restaurant to explore:",
        options=restaurants["restaurant_id"].unique(),
        format_func=lambda x: f"⭐ {restaurants[restaurants['restaurant_id'] == x]['overall_rating'].values[0]:.1f} - {restaurants[restaurants['restaurant_id'] == x]['restaurant_name'].values[0]}"
    )

    if not selected_restaurant_id:
        return

    # Filter data for selected restaurant
    rest_df = df[df["restaurant_id"] == selected_restaurant_id]

    if len(rest_df) == 0:
        st.warning("No data available for this restaurant.")
        return

    # Restaurant info header
    rest_info = rest_df.iloc[0]
    rest_name = rest_info.get("restaurant_name", "Unknown Restaurant")

    col1, col2 = st.columns([3, 1])

    with col1:
        # Rating badge
        avg_rating = rest_df["overall_rating"].mean()
        rating_color = "#28a745" if avg_rating >= 4.5 else "#ffc107" if avg_rating >= 4 else "#dc3545"

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 16px;">
            <h2 style="margin: 0; color: #FAFAFA;">📍 {rest_name}</h2>
            <div style="background-color: {rating_color}33; padding: 8px 16px; border-radius: 20px; border: 2px solid {rating_color};">
                <span style="color: {rating_color}; font-size: 20px; font-weight: bold;">⭐ {avg_rating:.1f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Info badges
        info_items = []
        if "category" in rest_df.columns:
            info_items.append(f"🍽️ {rest_info['category']}")
        if "price_range" in rest_df.columns:
            info_items.append(f"💰 {rest_info['price_range']}")
        if "location" in rest_df.columns:
            info_items.append(f"📍 {rest_info['location']}")

        if info_items:
            st.markdown(" ".join(info_items), unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; text-align: center;">
            <h1 style="margin: 0; color: #4ECDC4; font-size: 48px;">{len(rest_df)}</h1>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">reviews</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Rating Distribution")

        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=rest_df["overall_rating"],
            nbinsx=10,
            marker_color='#4ECDC4',
            opacity=0.8
        ))

        fig.update_layout(
            showlegend=False,
            height=350,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            xaxis_title="Rating",
            yaxis_title="Count"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 😊 Aspect Sentiments")

        aspects = ["comida", "servicio", "precio", "ambiente"]
        aspect_scores = {}

        for aspect in aspects:
            col = f"sentiment_{aspect}_score"
            if col in rest_df.columns:
                score = rest_df[col].mean()
                aspect_scores[aspect.capitalize()] = score

        if aspect_scores:
            colors = ["#28a745" if v > 0.1 else "#dc3545" if v < -0.1 else "#ffc107"
                     for v in aspect_scores.values()]

            fig = go.Figure(data=[go.Bar(
                x=list(aspect_scores.keys()),
                y=list(aspect_scores.values()),
                marker_color=colors,
                text=[f"{v:.2f}" for v in aspect_scores.values()],
                textposition='auto'
            )])

            fig.update_layout(
                showlegend=False,
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FAFAFA'),
                yaxis=dict(range=[-1, 1]),
                yaxis_title="Sentiment Score"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sentiment data not available.")

    # Reviews section
    st.markdown("---")
    st.markdown("### 💬 Customer Reviews")

    # Sentiment filter
    sentiment_filter = st.radio(
        "Filter by sentiment:",
        options=["All", "Positive", "Neutral", "Negative"],
        horizontal=True
    )

    # Calculate sentiment if not exists
    if "overall_sentiment_score" not in rest_df.columns:
        sentiment_cols = [col for col in rest_df.columns if col.startswith("sentiment_") and col.endswith("_score")]
        if sentiment_cols:
            rest_df = rest_df.copy()
            rest_df["overall_sentiment_score"] = rest_df[sentiment_cols].mean(axis=1)

    # Get reviews
    reviews_df = rest_df[["review_text", "review_date", "reviewer_name"] +
                        [col for col in rest_df.columns if col.startswith("sentiment_")]].dropna(subset=["review_text"])

    if sentiment_filter != "All":
        sentiment_col = "overall_sentiment_score"
        if sentiment_col in reviews_df.columns:
            if sentiment_filter == "Positive":
                reviews_df = reviews_df[reviews_df[sentiment_col] > 0.1]
            elif sentiment_filter == "Negative":
                reviews_df = reviews_df[reviews_df[sentiment_col] < -0.1]
            else:
                reviews_df = reviews_df[(reviews_df[sentiment_col] >= -0.1) & (reviews_df[sentiment_col] <= 0.1)]

    st.markdown(f"**Showing {len(reviews_df)} review(s)**")

    for _, review in reviews_df.iterrows():
        sentiment = ""
        sentiment_color = "#A0AEC0"
        sentiment_bg = "#1E2530"

        if "overall_sentiment_score" in review.index and pd.notna(review["overall_sentiment_score"]):
            score = review["overall_sentiment_score"]
            if score > 0.1:
                sentiment = "😊 Positive"
                sentiment_color = "#28a745"
                sentiment_bg = "rgba(40, 167, 69, 0.1)"
            elif score < -0.1:
                sentiment = "😞 Negative"
                sentiment_color = "#dc3545"
                sentiment_bg = "rgba(220, 53, 69, 0.1)"
            else:
                sentiment = "😐 Neutral"
                sentiment_color = "#ffc107"
                sentiment_bg = "rgba(255, 193, 7, 0.1)"

        reviewer = review.get('reviewer_name', 'Anonymous')
        review_date = review.get('review_date', '')

        st.markdown(f"""
        <div style="background-color: {sentiment_bg}; padding: 16px; border-radius: 12px; margin-bottom: 12px; border-left: 4px solid {sentiment_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #FAFAFA; font-weight: bold;">👤 {reviewer}</span>
                    {"<span style='color: #A0AEC0; margin-left: 12px;'>📅 " + str(review_date) + "</span>" if pd.notna(review_date) and review_date else ""}
                </div>
                <span style="color: {sentiment_color}; font-weight: bold;">{sentiment}</span>
            </div>
            <p style="margin: 12px 0 0 0; color: #FAFAFA; line-height: 1.6;">{review["review_text"]}</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    df = pd.read_csv("data/processed/restaurants_clustered.csv")
    render(df)
