"""
Overview Page - Dashboard homepage with KPIs and summary statistics - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render(df: pd.DataFrame):
    """Render the Overview page with enhanced UI."""

    # KPI Row
    st.markdown("### Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    total_restaurants = df["restaurant_id"].nunique()
    total_reviews = len(df)
    avg_rating = df["overall_rating"].mean()
    avg_sentiment = 0
    sentiment_cols = [col for col in df.columns if col.startswith("sentiment_") and col.endswith("_score")]
    if sentiment_cols:
        avg_sentiment = df[sentiment_cols].mean().mean()

    with col1:
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #2D3748;">
            <h1 style="margin: 0; color: #FF6B6B; font-size: 36px;">{total_restaurants}</h1>
            <p style="margin: 8px 0 0 0; color: #A0AEC0;">Total Restaurants</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #2D3748;">
            <h1 style="margin: 0; color: #4ECDC4; font-size: 36px;">{total_reviews}</h1>
            <p style="margin: 8px 0 0 0; color: #A0AEC0;">Total Reviews</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        rating_color = "#28a745" if avg_rating >= 4.5 else "#ffc107" if avg_rating >= 4 else "#dc3545"
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #2D3748;">
            <h1 style="margin: 0; color: {rating_color}; font-size: 36px;">{avg_rating:.2f}</h1>
            <p style="margin: 8px 0 0 0; color: #A0AEC0;">Average Rating</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        sentiment_label = "Positive " if avg_sentiment > 0.1 else "Neutral " if avg_sentiment > -0.1 else "Negative "
        sentiment_color = "#28a745" if avg_sentiment > 0.1 else "#ffc107" if avg_sentiment > -0.1 else "#dc3545"
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #2D3748;">
            <h1 style="margin: 0; color: {sentiment_color}; font-size: 36px;">{sentiment_label}</h1>
            <p style="margin: 8px 0 0 0; color: #A0AEC0;">Overall Sentiment</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts Row 1
    st.markdown("### Top Restaurants & Rating Distribution")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Top 10 by Rating")

        top_restaurants = df.groupby(["restaurant_id", "restaurant_name"])["overall_rating"].mean()\
            .reset_index()\
            .sort_values("overall_rating", ascending=False)\
            .head(10)

        fig = px.bar(
            top_restaurants,
            x="overall_rating",
            y="restaurant_name",
            orientation="h",
            color="overall_rating",
            color_continuous_scale=["#28a745", "#ffc107", "#dc3545"],
            range_color=[3.5, 5.0],
            text="overall_rating"
        )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            showlegend=False,
            height=450,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            yaxis_title="",
            xaxis_title="Rating"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Rating Distribution")

        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=df["overall_rating"].dropna(),
            nbinsx=20,
            marker_color='#FF6B6B',
            opacity=0.8,
            hovertemplate='Rating: %{x:.1f}<br>Count: %{y}<extra></extra>'
        ))

        fig.update_layout(
            showlegend=False,
            height=450,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            xaxis_title="Rating",
            yaxis_title="Count"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Charts Row 2
    st.markdown("### Category & Price Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Category Distribution")

        if "category" in df.columns:
            category_counts = df["category"].value_counts().head(8)

            fig = go.Figure(data=[go.Pie(
                labels=category_counts.index,
                values=category_counts.values,
                hole=0.5,
                marker=dict(colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'])
            )])

            fig.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FAFAFA'),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3)
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Price Range Distribution")

        if "price_range" in df.columns:
            price_counts = df["price_range"].value_counts()

            colors = {'$': '#28a745', '$$ - $$$': '#ffc107', '$$$ - $$$$': '#FF6B6B', '$$$$': '#dc3545'}

            fig = go.Figure(data=[go.Bar(
                x=price_counts.index,
                y=price_counts.values,
                marker_color=[colors.get(p, '#4ECDC4') for p in price_counts.index],
                text=price_counts.values,
                textposition='auto'
            )])

            fig.update_layout(
                showlegend=False,
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FAFAFA'),
                xaxis_title="Price Range",
                yaxis_title="Count"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Sentiment Analysis Section
    if sentiment_cols:
        st.markdown("### Sentiment Analysis by Aspect")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Sentiment Distribution")

            df["overall_sentiment"] = df[sentiment_cols].mean(axis=1)
            df["sentiment_category"] = df["overall_sentiment"].apply(
                lambda x: "Positive" if x > 0.1 else "Negative" if x < -0.1 else "Neutral"
            )

            sentiment_counts = df["sentiment_category"].value_counts()

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

        with col2:
            st.markdown("#### Average Sentiment by Aspect")

            aspect_scores = {}
            for aspect in ["comida", "servicio", "precio", "ambiente"]:
                col = f"sentiment_{aspect}_score"
                if col in df.columns:
                    aspect_scores[aspect.capitalize()] = df[col].mean()

            colors = ['#28a745' if v > 0.1 else '#ffc107' if v > -0.1 else '#dc3545' for v in aspect_scores.values()]

            fig = go.Figure(data=[go.Bar(
                x=list(aspect_scores.keys()),
                y=list(aspect_scores.values()),
                marker_color=colors,
                text=[f"{v:.2f}" for v in aspect_scores.values()],
                textposition='auto'
            )])

            fig.update_layout(
                showlegend=False,
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FAFAFA'),
                yaxis_title="Average Sentiment Score",
                xaxis_title="Aspect"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Filters section
    st.markdown("---")
    st.markdown("### Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        if "category" in df.columns:
            categories = ["All"] + df["category"].dropna().unique().tolist()
            selected_category = st.selectbox("Category", categories)

    with col2:
        if "price_range" in df.columns:
            price_ranges = ["All"] + df["price_range"].dropna().unique().tolist()
            selected_price = st.selectbox("Price Range", price_ranges)

    with col3:
        if "cluster" in df.columns:
            clusters = ["All"] + [f"Cluster {i}" for i in sorted(df["cluster"].unique())]
            selected_cluster = st.selectbox("Cluster", clusters)

    # Apply filters
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df["category"] == selected_category]
    if selected_price != "All":
        filtered_df = filtered_df[filtered_df["price_range"] == selected_price]
    if selected_cluster != "All":
        cluster_num = int(selected_cluster.split()[-1])
        filtered_df = filtered_df[filtered_df["cluster"] == cluster_num]

    st.markdown(f"**Showing {len(filtered_df)} reviews** ({filtered_df['restaurant_id'].nunique()} restaurants)")
