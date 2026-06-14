"""
Sentiment Analysis Page - Visualize sentiment analysis results - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dashboard.config import SENTIMENT_COLORS


def render(df: pd.DataFrame):
    """Render the Sentiment Analysis page with enhanced UI."""

    st.markdown("### 😊 Sentiment Distribution Overview")

    sentiment_cols = [col for col in df.columns if col.startswith("sentiment_") and col.endswith("_score")]

    if not sentiment_cols:
        st.warning("⚠️ Sentiment analysis not yet performed.")
        return

    # Calculate overall sentiment
    df["overall_sentiment"] = df[sentiment_cols].mean(axis=1)
    df["sentiment_category"] = df["overall_sentiment"].apply(
        lambda x: "Positive" if x > 0.1 else "Negative" if x < -0.1 else "Neutral"
    )

    # Overview cards
    col1, col2, col3, col4 = st.columns(4)

    sentiment_counts = df["sentiment_category"].value_counts()
    total = len(df)

    positive_pct = (sentiment_counts.get("Positive", 0) / total * 100) if total > 0 else 0
    negative_pct = (sentiment_counts.get("Negative", 0) / total * 100) if total > 0 else 0
    neutral_pct = (sentiment_counts.get("Neutral", 0) / total * 100) if total > 0 else 0

    with col1:
        st.markdown(f"""
        <div style="background-color: rgba(40, 167, 69, 0.15); padding: 16px; border-radius: 12px; border-left: 4px solid #28a745;">
            <h2 style="margin: 0; color: #28a745;">{positive_pct:.1f}%</h2>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">Positive 😊</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: rgba(255, 193, 7, 0.15); padding: 16px; border-radius: 12px; border-left: 4px solid #ffc107;">
            <h2 style="margin: 0; color: #ffc107;">{neutral_pct:.1f}%</h2>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">Neutral 😐</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background-color: rgba(220, 53, 69, 0.15); padding: 16px; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="margin: 0; color: #dc3545;">{negative_pct:.1f}%</h2>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">Negative 😞</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        avg_score = df["overall_sentiment"].mean()
        score_color = "#28a745" if avg_score > 0.1 else "#ffc107" if avg_score > -0.1 else "#dc3545"
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; border-left: 4px solid {score_color};">
            <h2 style="margin: 0; color: {score_color};">{avg_score:.3f}</h2>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">Avg Score</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Sentiment by Aspect")

        aspects = ["comida", "servicio", "precio", "ambiente"]
        aspect_means = {}

        for aspect in aspects:
            col = f"sentiment_{aspect}_score"
            if col in df.columns:
                aspect_means[aspect.capitalize()] = df[col].mean()

        colors = ['#28a745' if v > 0.1 else '#ffc107' if v > -0.1 else '#dc3545' for v in aspect_means.values()]

        fig = go.Figure(data=[go.Bar(
            x=list(aspect_means.keys()),
            y=list(aspect_means.values()),
            marker_color=colors,
            text=[f"{v:.2f}" for v in aspect_means.values()],
            textposition='auto'
        )])

        fig.update_layout(
            showlegend=False,
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            yaxis_title="Average Sentiment"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 🥧 Sentiment Distribution")

        fig = go.Figure(data=[go.Pie(
            labels=sentiment_counts.index,
            values=sentiment_counts.values,
            hole=0.5,
            marker=dict(colors=['#28a745', '#ffc107', '#dc3545'])
        )])

        fig.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA')
        )
        st.plotly_chart(fig, use_container_width=True)

    # Sentiment heatmap by category
    if "category" in df.columns:
        st.markdown("---")
        st.markdown("### 🔥 Sentiment Heatmap by Category")

        categories = df["category"].value_counts().head(8).index.tolist()

        heatmap_data = []
        for cat in categories:
            cat_df = df[df["category"] == cat]
            row = {"Category": cat}
            for aspect in aspects:
                col = f"sentiment_{aspect}_score"
                if col in cat_df.columns:
                    row[aspect.capitalize()] = cat_df[col].mean()
            heatmap_data.append(row)

        heatmap_df = pd.DataFrame(heatmap_data)

        fig = px.imshow(
            heatmap_df[aspects].values,
            x=[a.capitalize() for a in aspectos := aspects],
            y=heatmap_df["Category"].values,
            color_continuous_scale="RdYlGn",
            range_color=[-1, 1],
            labels=dict(x="Aspect", y="Category", color="Sentiment"),
            text=heatmap_df[aspects].values
        )

        fig.update_layout(
            height=500,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA')
        )
        st.plotly_chart(fig, use_container_width=True)

    # Top reviews
    st.markdown("---")
    st.markdown("### 💬 Top Reviews")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ Most Positive Reviews")

        positive_df = df[df["overall_sentiment"] > 0.3].nlargest(5, "overall_sentiment")

        for _, row in positive_df.iterrows():
            restaurant = row.get("restaurant_name", "Unknown")
            sentiment = row.get("overall_sentiment", 0)
            review = str(row.get("review_text", ""))[:150]

            st.markdown(f"""
            <div style="background-color: rgba(40, 167, 69, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #28a745;">
                <strong style="color: #28a745;">🏆 {restaurant}</strong>
                <span style="color: #A0AEC0; float: right;">Score: {sentiment:.2f}</span>
                <p style="margin: 8px 0 0 0; color: #FAFAFA;">"{review}..."</p>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### ⚠️ Most Negative Reviews")

        negative_df = df[df["overall_sentiment"] < -0.3].nsmallest(5, "overall_sentiment")

        for _, row in negative_df.iterrows():
            restaurant = row.get("restaurant_name", "Unknown")
            sentiment = row.get("overall_sentiment", 0)
            review = str(row.get("review_text", ""))[:150]

            st.markdown(f"""
            <div style="background-color: rgba(220, 53, 69, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #dc3545;">
                <strong style="color: #dc3545;">⚠️ {restaurant}</strong>
                <span style="color: #A0AEC0; float: right;">Score: {sentiment:.2f}</span>
                <p style="margin: 8px 0 0 0; color: #FAFAFA;">"{review}..."</p>
            </div>
            """, unsafe_allow_html=True)
