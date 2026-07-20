"""
Detail Page - View detailed information about a single restaurant.

The sentiment filter here used to be a no-op: the reviews frame was built by
picking columns starting with "sentiment_", while the filter read a column named
"overall_sentiment_score", which therefore was never present. Selecting
"Negativo" silently returned every review, and the per-review sentiment badge
never rendered. Both now work off an explicitly computed column.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.aspects import ASPECT_LABELS, ASPECTS, all_aspect_summaries, coverage_note, mention_mask, overall_sentiment

TRANSPARENT = "rgba(0,0,0,0)"

SENTIMENT_STYLES = {
    "Positivo": ("#28a745", "rgba(40, 167, 69, 0.10)"),
    "Neutral": ("#ffc107", "rgba(255, 193, 7, 0.10)"),
    "Negativo": ("#dc3545", "rgba(220, 53, 69, 0.10)"),
}


def _clean_display(value):
    """Return a readable display value, skipping missing values."""
    if pd.isna(value) or str(value).strip().lower() in ("nan", ""):
        return None
    return str(value)


def _label_for(score) -> str:
    if pd.isna(score):
        return "Sin datos"
    if score > 0.1:
        return "Positivo"
    if score < -0.1:
        return "Negativo"
    return "Neutral"


def render(df: pd.DataFrame):
    """Render the Detail page."""

    st.markdown("### Selecciona un restaurante")

    restaurants = (
        df.groupby(["restaurant_id", "restaurant_name"], as_index=False)
          .agg(rating=("overall_rating", "mean"), resenas=("review_text", "size"))
          .sort_values("restaurant_name")
    )

    query = st.text_input("Buscar restaurante", key="detalle_search",
                          placeholder="Escribe parte del nombre...")
    if query.strip():
        mask = restaurants["restaurant_name"].str.lower().str.contains(query.strip().lower(), regex=False)
        restaurants = restaurants[mask]

    if restaurants.empty:
        st.warning("Ningun restaurante coincide con esa busqueda.")
        return

    lookup = restaurants.set_index("restaurant_id")

    def _format(rid):
        row = lookup.loc[rid]
        rating = f"{row['rating']:.1f}" if pd.notna(row["rating"]) else "s/c"
        return f"{rating} - {row['restaurant_name']} ({int(row['resenas'])} resenas)"

    selected_id = st.selectbox(
        "Elige un restaurante para explorar:",
        options=restaurants["restaurant_id"].tolist(),
        format_func=_format,
        key="detalle_select",
    )

    rest_df = df[df["restaurant_id"] == selected_id]
    if rest_df.empty:
        st.warning("No hay datos disponibles para este restaurante.")
        return

    _render_header(rest_df)
    st.markdown("---")
    _render_charts(rest_df)
    st.markdown("---")
    _render_reviews(rest_df)


def _render_header(rest_df: pd.DataFrame) -> None:
    info = rest_df.iloc[0]
    name = info.get("restaurant_name", "Restaurante desconocido")

    col1, col2 = st.columns([3, 1])

    with col1:
        avg_rating = rest_df["overall_rating"].mean()
        has_rating = pd.notna(avg_rating)
        color = ("#28a745" if has_rating and avg_rating >= 4.5
                 else "#ffc107" if has_rating and avg_rating >= 4
                 else "#A0AEC0" if not has_rating else "#dc3545")
        label = f"{avg_rating:.1f}" if has_rating else "s/c"

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 16px;">
            <h2 style="margin: 0; color: #FAFAFA;">{name}</h2>
            <div style="background-color: {color}33; padding: 8px 16px; border-radius: 20px;
                        border: 2px solid {color};">
                <span style="color: {color}; font-size: 20px; font-weight: bold;">{label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        badges = [_clean_display(info.get(c)) for c in
                  ("category", "price_band", "price_range", "location")]
        badges = [b for b in badges if b]
        # price_band supersedes price_range when both exist.
        if _clean_display(info.get("price_band")) and _clean_display(info.get("price_range")):
            badges = [b for b in badges if b != _clean_display(info.get("price_range"))]
        if badges:
            st.markdown(
                " ".join(
                    f"<span style='background:#1E2530;border:1px solid #2D3748;border-radius:16px;"
                    f"padding:4px 12px;margin-right:8px;color:#A0AEC0;'>{b}</span>"
                    for b in badges
                ),
                unsafe_allow_html=True,
            )

        address = _clean_display(info.get("address"))
        if address:
            st.caption(address)

    with col2:
        st.markdown(f"""
        <div style="background-color: #1E2530; padding: 16px; border-radius: 12px; text-align: center;">
            <h1 style="margin: 0; color: #4ECDC4; font-size: 48px;">{len(rest_df)}</h1>
            <p style="margin: 4px 0 0 0; color: #A0AEC0;">resenas</p>
        </div>
        """, unsafe_allow_html=True)


def _render_charts(rest_df: pd.DataFrame) -> None:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Calificaciones de las resenas")
        # review_rating is the score the reviewer gave; overall_rating is the
        # restaurant's headline score and is identical on every row.
        source_col = "review_rating" if "review_rating" in rest_df.columns else "overall_rating"
        ratings = rest_df[source_col].dropna()

        if ratings.empty:
            st.info("Este restaurante no tiene calificaciones por resena.")
        else:
            counts = ratings.value_counts().sort_index()
            fig = go.Figure(go.Bar(
                x=[f"{v:g}" for v in counts.index],
                y=counts.values,
                marker_color="#4ECDC4",
                text=counts.values,
                textposition="auto",
            ))
            fig.update_layout(
                plot_bgcolor=TRANSPARENT, paper_bgcolor=TRANSPARENT,
                font=dict(color="#FAFAFA"), showlegend=False, height=350,
                xaxis_title="Estrellas", yaxis_title="Resenas",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, width="stretch")
            if source_col == "review_rating":
                st.caption(f"{len(ratings)} de {len(rest_df)} resenas traen calificacion propia.")

    with col2:
        st.markdown("#### Sentimiento por aspecto")
        summaries = all_aspect_summaries(rest_df)

        if not summaries:
            st.info("No hay datos de sentimiento disponibles.")
        else:
            colors = ["#28a745" if s["mean"] > 0.1 else "#dc3545" if s["mean"] < -0.1 else "#ffc107"
                      for s in summaries]
            fig = go.Figure(go.Bar(
                x=[s["label"] for s in summaries],
                y=[s["mean"] for s in summaries],
                marker_color=colors,
                text=[f"{s['mean']:.2f}" for s in summaries],
                textposition="auto",
                customdata=[[s["mentions"]] for s in summaries],
                hovertemplate="%{x}<br>Promedio: %{y:.2f}"
                              "<br>%{customdata[0]} resenas lo mencionan<extra></extra>",
            ))
            fig.update_layout(
                plot_bgcolor=TRANSPARENT, paper_bgcolor=TRANSPARENT,
                font=dict(color="#FAFAFA"), showlegend=False, height=350,
                yaxis=dict(range=[-1, 1], title="Sentimiento"),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, width="stretch")
            st.caption(coverage_note(summaries))

    _render_site_ratings(rest_df)


def _render_site_ratings(rest_df: pd.DataFrame) -> None:
    """Compare the site's own aspect scores against the computed sentiment."""
    pairs = [
        ("food_rating", "comida"),
        ("service_rating", "servicio"),
        ("ambiance_rating", "ambiente"),
    ]
    available = [(col, aspect) for col, aspect in pairs
                 if col in rest_df.columns and rest_df[col].notna().any()]
    if not available:
        return

    st.markdown("#### Calificacion del sitio vs. sentimiento calculado")

    rows = []
    for col, aspect in available:
        site_score = rest_df[col].dropna().mean()
        score_col = f"sentiment_{aspect}_score"
        mask = mention_mask(rest_df, aspect)
        computed = rest_df.loc[mask, score_col].mean() if score_col in rest_df.columns else None
        rows.append({
            "Aspecto": ASPECT_LABELS.get(aspect, aspect),
            "Sitio (0-5)": round(float(site_score), 2),
            "Sentimiento (-1 a 1)": round(float(computed), 2) if pd.notna(computed) else None,
            "Resenas que lo mencionan": int(mask.sum()),
        })

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("La columna del sitio es la nota publicada por la fuente; la de sentimiento "
               "es la que calcula nuestro analizador a partir del texto de las resenas.")


def _render_reviews(rest_df: pd.DataFrame) -> None:
    st.markdown("### Resenas de clientes")

    reviews = rest_df.copy()
    reviews["_sentiment_score"] = overall_sentiment(reviews)
    reviews["_sentiment_label"] = reviews["_sentiment_score"].apply(_label_for)
    reviews = reviews.dropna(subset=["review_text"])

    col1, col2 = st.columns([2, 1])
    with col1:
        counts = reviews["_sentiment_label"].value_counts()
        options = ["Todos"] + [o for o in ("Positivo", "Neutral", "Negativo") if counts.get(o, 0) > 0]
        labels = {o: (o if o == "Todos" else f"{o} ({counts.get(o, 0)})") for o in options}
        selected = st.radio(
            "Filtrar por sentimiento:",
            options=options,
            format_func=lambda o: labels[o],
            horizontal=True,
            key="detalle_sentiment",
        )
    with col2:
        text_query = st.text_input("Buscar en el texto", key="detalle_review_search",
                                   placeholder="p. ej. servicio")

    if selected != "Todos":
        reviews = reviews[reviews["_sentiment_label"] == selected]
    if text_query.strip():
        needle = text_query.strip().lower()
        reviews = reviews[reviews["review_text"].astype(str).str.lower().str.contains(needle, regex=False)]

    if "review_date" in reviews.columns:
        reviews = reviews.sort_values("review_date", ascending=False, na_position="last")

    st.markdown(f"**Mostrando {len(reviews)} resena(s)**")
    if reviews.empty:
        st.info("Ninguna resena coincide con este filtro.")
        return

    for _, review in reviews.iterrows():
        label = review["_sentiment_label"]
        color, background = SENTIMENT_STYLES.get(label, ("#A0AEC0", "#1E2530"))

        reviewer = _clean_display(review.get("reviewer_name")) or "Anonimo"
        date = _clean_display(review.get("review_date"))
        date_html = (f"<span style='color:#A0AEC0;margin-left:12px;'>{str(date)[:10]}</span>"
                     if date else "")
        stars = review.get("review_rating")
        stars_html = (f"<span style='color:#FFD700;margin-left:12px;'>{stars:g}/5</span>"
                      if pd.notna(stars) else "")

        st.markdown(f"""
        <div style="background-color: {background}; padding: 16px; border-radius: 12px;
                    margin-bottom: 12px; border-left: 4px solid {color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #FAFAFA; font-weight: bold;">{reviewer}</span>
                    {date_html}{stars_html}
                </div>
                <span style="color: {color}; font-weight: bold;">{label}</span>
            </div>
            <p style="margin: 12px 0 0 0; color: #FAFAFA; line-height: 1.6;">{review["review_text"]}</p>
        </div>
        """, unsafe_allow_html=True)
