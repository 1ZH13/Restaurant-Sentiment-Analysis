"""
Clustering Page - Visualize restaurant clusters - Enhanced UX/UI
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dashboard.config import CLUSTER_COLORS


def render(df: pd.DataFrame):
    """Render the Clustering page with enhanced UI."""

    st.markdown("### Restaurant Clusters")

    if "cluster" not in df.columns:
        st.warning("Clustering not yet performed.")
        return

    # Cluster summary cards
    cluster_counts = df.groupby("cluster")["restaurant_id"].nunique().reset_index()
    cluster_counts.columns = ["Cluster", "Count"]

    st.markdown("#### Cluster Distribution")

    cols = st.columns(len(cluster_counts))

    for i, (_, row) in enumerate(cluster_counts.iterrows()):
        cluster_id = int(row["Cluster"])
        with cols[i]:
            st.markdown(f"""
            <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; border: 1px solid {CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]}; text-align: center;">
                <h2 style="margin: 0; color: {CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]};">Cluster {cluster_id}</h2>
                <p style="margin: 8px 0 0 0; font-size: 24px;">{row["Count"]} restaurants</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Cluster Size Distribution")

        fig = go.Figure(data=[go.Pie(
            labels=[f"Cluster {int(c)}" for c in cluster_counts["Cluster"]],
            values=cluster_counts["Count"],
            hole=0.5,
            marker=dict(colors=[CLUSTER_COLORS[int(c) % len(CLUSTER_COLORS)] for c in cluster_counts["Cluster"]])
        )])

        fig.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA')
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Average Rating by Cluster")

        # Calculate cluster statistics
        cluster_stats = df.groupby("cluster").agg({
            "overall_rating": "mean",
            "restaurant_id": "nunique"
        }).reset_index()
        cluster_stats.columns = ["Cluster", "Avg Rating", "Restaurant Count"]

        colors = [CLUSTER_COLORS[int(c) % len(CLUSTER_COLORS)] for c in cluster_stats["Cluster"]]

        fig = go.Figure(data=[go.Bar(
            x=[f"Cluster {int(c)}" for c in cluster_stats["Cluster"]],
            y=cluster_stats["Avg Rating"],
            marker_color=colors,
            text=[f"{r:.2f}" for r in cluster_stats["Avg Rating"]],
            textposition='auto'
        )])

        fig.update_layout(
            showlegend=False,
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            yaxis=dict(range=[0, 5.5]),
            yaxis_title="Average Rating"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Cluster profiles table
    st.markdown("---")
    st.markdown("#### Cluster Profiles")

    cluster_profiles = []

    for cluster_id in sorted(df["cluster"].unique()):
        cluster_df = df[df["cluster"] == cluster_id]

        profile = {
            "Cluster": f"Cluster {cluster_id}",
            "Restaurants": cluster_df["restaurant_id"].nunique(),
            "Avg Rating": f"{cluster_df['overall_rating'].mean():.2f}",
            "Reviews": len(cluster_df)
        }

        # Sentiment averages
        sentiment_cols = [col for col in df.columns if col.startswith("sentiment_") and col.endswith("_score")]
        for col in sentiment_cols:
            aspect = col.replace("sentiment_", "").replace("_score", "").capitalize()
            profile[f"Avg {aspect}"] = f"{cluster_df[col].mean():.2f}"

        cluster_profiles.append(profile)

    profiles_df = pd.DataFrame(cluster_profiles)

    st.dataframe(
        profiles_df,
        use_container_width=True,
        hide_index=True
    )

    # Top restaurants per cluster
    st.markdown("---")
    st.markdown("#### Top Restaurants per Cluster")

    selected_cluster = st.selectbox(
        "Select a cluster:",
        options=sorted(df["cluster"].unique()),
        format_func=lambda x: f"Cluster {x}"
    )

    if selected_cluster is not None:
        cluster_df = df[df["cluster"] == selected_cluster]

        top_restaurants = cluster_df.groupby(["restaurant_id", "restaurant_name"]).agg({
            "overall_rating": "mean"
        }).reset_index().sort_values("overall_rating", ascending=False).head(10)

        top_restaurants.columns = ["ID", "Restaurant", "Rating"]

        st.dataframe(
            top_restaurants,
            use_container_width=True,
            hide_index=True,
            column_config={"Rating": st.column_config.NumberColumn(format="%.2f ")}
        )

    # Scatter plot
    st.markdown("---")
    st.markdown("#### Restaurant Map (Rating vs Sentiment)")

    if "overall_sentiment_score" not in df.columns:
        sentiment_cols = [col for col in df.columns if col.startswith("sentiment_") and col.endswith("_score")]
        if sentiment_cols:
            df["overall_sentiment_score"] = df[sentiment_cols].mean(axis=1)

    if "overall_sentiment_score" in df.columns and "overall_rating" in df.columns:
        scatter_df = df.groupby(["restaurant_id", "restaurant_name", "cluster"]).agg({
            "overall_rating": "mean",
            "overall_sentiment_score": "mean"
        }).reset_index()

        fig = px.scatter(
            scatter_df,
            x="overall_rating",
            y="overall_sentiment_score",
            color="cluster",
            hover_data=["restaurant_name"],
            color_discrete_sequence=CLUSTER_COLORS[:len(scatter_df["cluster"].unique())],
            size=[20] * len(scatter_df)
        )

        fig.update_layout(
            height=500,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            xaxis_title="Average Rating",
            yaxis_title="Average Sentiment Score",
            legend_title="Cluster"
        )
        st.plotly_chart(fig, use_container_width=True)
