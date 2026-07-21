"""
Tests for the restaurant-level directory used by the selectors.

Cross-source unification gives one canonical restaurant_id to a venue that both
sources list, but the two sources spell the name differently. Grouping by
["restaurant_id", "restaurant_name"] therefore produced two rows sharing an id;
indexing by that id returned a DataFrame instead of a row and the Comparar and
Detalle selectors crashed with "The truth value of a Series is ambiguous".
"""

import pandas as pd
import pytest

from dashboard.utils.restaurants import format_restaurant_label, restaurant_directory


@pytest.fixture
def unified_reviews():
    """A restaurant unified across sources, keeping two spellings."""
    return pd.DataFrame({
        "restaurant_id": ["r_trapiche", "r_trapiche", "r_trapiche", "r_sushi"],
        "restaurant_name": [
            "El Trapiche (Bella Vista)",
            "El Trapiche (Bella Vista)",
            "Restaurante El Trapiche Bella Vista",
            "Sushi Uno",
        ],
        "overall_rating": [4.4, 4.4, 4.4, 4.9],
        "review_text": ["a", "b", "c", "d"],
        "category": ["Panamena", "Panamena", "Panamena", "Japonesa"],
        "source": ["degusta", "degusta", "restaurantguru", "degusta"],
    })


class TestRestaurantDirectory:
    def test_one_row_per_restaurant(self, unified_reviews):
        directory = restaurant_directory(unified_reviews)
        assert len(directory) == 2
        assert directory["restaurant_id"].is_unique

    def test_index_lookup_returns_a_single_row(self, unified_reviews):
        """This is the exact operation that used to raise."""
        lookup = restaurant_directory(unified_reviews).set_index("restaurant_id")
        row = lookup.loc["r_trapiche"]

        assert isinstance(row, pd.Series)
        assert format_restaurant_label(row).startswith("4.4 - ")

    def test_uses_the_most_common_spelling(self, unified_reviews):
        directory = restaurant_directory(unified_reviews).set_index("restaurant_id")
        assert directory.loc["r_trapiche", "restaurant_name"] == "El Trapiche (Bella Vista)"

    def test_counts_all_reviews_of_the_restaurant(self, unified_reviews):
        directory = restaurant_directory(unified_reviews).set_index("restaurant_id")
        assert directory.loc["r_trapiche", "resenas"] == 3

    def test_empty_frame_returns_empty_directory(self):
        assert restaurant_directory(pd.DataFrame()).empty


class TestLabelFormatting:
    def test_missing_rating_does_not_render_nan(self):
        row = pd.Series({"restaurant_name": "Sin Nota", "rating": float("nan"), "resenas": 2})
        assert format_restaurant_label(row) == "s/c - Sin Nota"

    def test_review_count_is_optional(self):
        row = pd.Series({"restaurant_name": "Sushi Uno", "rating": 4.9, "resenas": 5})
        assert format_restaurant_label(row) == "4.9 - Sushi Uno"
        assert format_restaurant_label(row, show_reviews=True) == "4.9 - Sushi Uno (5 reseñas)"
