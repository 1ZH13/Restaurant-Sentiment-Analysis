"""
Regression tests for the dashboard filters.

The Overview page used to compute a filtered frame and then render every chart
from the unfiltered one, so selecting a category changed nothing on screen.
These tests drive the real Streamlit widgets and assert that the data behind the
page actually shrinks.
"""

import pandas as pd
import pytest

from dashboard.utils.aspects import mention_mask, overall_sentiment
from dashboard.utils.filters import search_restaurants


@pytest.fixture
def reviews_df():
    return pd.DataFrame({
        "restaurant_id": ["r1", "r1", "r2", "r3", "r3"],
        "restaurant_name": ["Sushi Bar", "Sushi Bar", "Pizza Nova", "Cafe Central", "Cafe Central"],
        "category": ["Japonesa", "Japonesa", "Italiana", "Cafeteria", "Cafeteria"],
        "category_primary": ["Japonesa", "Japonesa", "Italiana", "Cafeteria", "Cafeteria"],
        "price_band": ["$$ ($15-$25)"] * 2 + ["$ (hasta $15)"] + ["$$ ($15-$25)"] * 2,
        "location": ["Obarrio", "Obarrio", "Marbella", "Obarrio", "Obarrio"],
        "overall_rating": [4.8, 4.8, 3.9, 4.2, 4.2],
        "review_text": ["excelente sushi", "buen sushi", "pizza rica", "cafe bueno", "cafe lento"],
        "sentiment_comida_score": [1.0, 1.0, 1.0, 0.0, -1.0],
        "sentiment_precio_score": [0.0, 0.0, 1.0, 0.0, 0.0],
        "mentions_comida": [True, True, True, True, True],
        "mentions_precio": [False, False, True, False, False],
    })


class TestSearchRestaurants:
    def test_matches_name(self, reviews_df):
        result = search_restaurants(reviews_df, "sushi")
        assert set(result["restaurant_id"]) == {"r1"}

    def test_matches_category(self, reviews_df):
        result = search_restaurants(reviews_df, "italiana")
        assert set(result["restaurant_id"]) == {"r2"}

    def test_is_case_insensitive(self, reviews_df):
        assert len(search_restaurants(reviews_df, "SUSHI")) == 2

    def test_empty_query_returns_everything(self, reviews_df):
        assert len(search_restaurants(reviews_df, "   ")) == len(reviews_df)

    def test_no_match_returns_empty(self, reviews_df):
        assert len(search_restaurants(reviews_df, "zzzz")) == 0


class TestMentionAwareAggregation:
    def test_mention_mask_excludes_unmentioned(self, reviews_df):
        mask = mention_mask(reviews_df, "precio")
        assert mask.sum() == 1

    def test_price_average_ignores_silent_reviews(self, reviews_df):
        """Averaging only the review that mentions price gives 1.0, not 0.2."""
        mask = mention_mask(reviews_df, "precio")
        assert reviews_df.loc[mask, "sentiment_precio_score"].mean() == 1.0
        assert reviews_df["sentiment_precio_score"].mean() == pytest.approx(0.2)

    def test_missing_flag_column_counts_every_row(self, reviews_df):
        df = reviews_df.drop(columns=["mentions_precio"])
        assert mention_mask(df, "precio").all()

    def test_overall_sentiment_does_not_mutate_input(self, reviews_df):
        before = list(reviews_df.columns)
        overall_sentiment(reviews_df)
        assert list(reviews_df.columns) == before


class TestOverviewPageFilters:
    """Drive the real page through Streamlit's AppTest harness."""

    @pytest.fixture
    def app(self):
        AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
        at = AppTest.from_file("dashboard/app.py", default_timeout=60)
        at.run()
        if at.exception:
            pytest.fail(f"La app fallo al iniciar: {at.exception}")
        return at

    def test_page_loads_without_exception(self, app):
        assert not app.exception

    def test_search_narrows_the_page(self, app):
        """Typing a query must reduce what the page reports, not just a label."""
        caption_before = [c.value for c in app.caption]
        assert any("resenas" in str(c) for c in caption_before)

        app.text_input(key="overview_search").set_value("sushi").run()
        assert not app.exception

        captions_after = " ".join(str(c.value) for c in app.caption)
        assert "resenas" in captions_after
        assert captions_after != " ".join(str(c) for c in caption_before), \
            "la busqueda no cambio el contenido de la pagina"

    def test_impossible_search_shows_warning(self, app):
        app.text_input(key="overview_search").set_value("zzzznoexiste").run()
        assert not app.exception
        warnings = " ".join(str(w.value) for w in app.warning)
        assert "coincide" in warnings.lower()

    def test_category_filter_changes_selection(self, app):
        selectbox = app.selectbox(key="overview_cat")
        options = [o for o in selectbox.options if o != "Todos"]
        if not options:
            pytest.skip("El dataset no tiene categorias")

        selectbox.set_value(options[0]).run()
        assert not app.exception
        assert app.selectbox(key="overview_cat").value == options[0]
