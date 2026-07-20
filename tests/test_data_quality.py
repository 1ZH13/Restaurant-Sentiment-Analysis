"""
Tests for the data-quality guarantees added to the ingestion and cleaning
stages: stable identifiers, cross-source deduplication, relative date parsing
and a single price vocabulary.

Each test here corresponds to a defect that shipped in the dataset at some
point, so they exist to keep those defects from coming back.
"""

import re

import pandas as pd
import pytest

from src.preprocessing.feature_engineering import encode_categorical_features
from src.ingestion.build_dataset import (
    canonical_id,
    deduplicate_reviews,
    merge_metadata,
    normalize_name,
    normalize_review_text,
    unify_restaurants,
)
from src.ingestion.restaurantguru_scraper import make_restaurant_id
from src.preprocessing.cleaner import (
    add_price_band,
    add_primary_category,
    clean_dataframe,
    encode_price,
    parse_relative_date,
    standardize_dates,
)


class TestStableIdentifiers:
    """Ids must not change between runs.

    RestaurantGuru ids were built from Python's ``hash()``, which is randomised
    per process, so every scrape produced a different id for the same
    restaurant and nothing could be joined or deduplicated across runs.
    """

    def test_restaurantguru_id_is_deterministic(self):
        assert make_restaurant_id("Popino-Panama-City") == make_restaurant_id("Popino-Panama-City")

    def test_different_slugs_give_different_ids(self):
        assert make_restaurant_id("Popino-Panama-City") != make_restaurant_id("Maito-Panama-City")

    def test_canonical_id_is_deterministic(self):
        assert canonical_id("sushi bar") == canonical_id("sushi bar")

    def test_canonical_id_has_expected_shape(self):
        value = canonical_id("sushi bar")
        assert value.startswith("r_") and len(value) == 12


class TestNameNormalization:
    def test_ignores_accents_and_case(self):
        assert normalize_name("Café Perú") == normalize_name("cafe peru")

    def test_ignores_generic_words(self):
        assert normalize_name("Salsipuedes Restaurant") == normalize_name("Salsipuedes Restaurante")

    def test_keeps_branches_distinct(self):
        """Two branches of a chain are different restaurants, not duplicates."""
        assert normalize_name("Sugoi Obarrio") != normalize_name("Sugoi Costa del Este")

    def test_blank_name_gives_empty_key(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""


class TestCrossSourceUnification:
    @pytest.fixture
    def two_sources(self):
        return pd.DataFrame({
            "restaurant_id": ["dg_1", "dg_1", "rg_abc", "dg_2"],
            "restaurant_name": ["Salsipuedes Restaurante", "Salsipuedes Restaurante",
                                "Salsipuedes Restaurant", "Maito"],
            "review_text": ["comida excelente aqui", "muy buen servicio siempre",
                            "el mejor ceviche de la ciudad", "sabores panamenos increibles"],
            "source": ["degusta", "degusta", "restaurantguru", "degusta"],
            "category": ["Panamena", "Panamena", None, "Panamena"],
            "price_range": [None, None, "$$", "$$$"],
        })

    def test_same_restaurant_gets_one_id(self, two_sources):
        result = unify_restaurants(two_sources)
        salsipuedes = result[result["restaurant_name"].str.startswith("Salsipuedes")]
        assert salsipuedes["restaurant_id"].nunique() == 1

    def test_distinct_restaurants_stay_separate(self, two_sources):
        result = unify_restaurants(two_sources)
        assert result["restaurant_id"].nunique() == 2

    def test_source_id_is_preserved(self, two_sources):
        result = unify_restaurants(two_sources)
        assert set(result["source_restaurant_id"]) == {"dg_1", "rg_abc", "dg_2"}

    def test_metadata_is_filled_across_sources(self, two_sources):
        """Degusta rows lack a price; the RestaurantGuru row supplies it."""
        result = merge_metadata(unify_restaurants(two_sources))
        salsipuedes = result[result["restaurant_name"].str.startswith("Salsipuedes")]
        assert salsipuedes["price_range"].notna().all()


class TestReviewDeduplication:
    def test_removes_identical_review_of_same_restaurant(self):
        df = pd.DataFrame({
            "restaurant_id": ["r1", "r1"],
            "review_text": ["La comida estuvo excelente", "la comida estuvo excelente!"],
        })
        assert len(deduplicate_reviews(df)) == 1

    def test_keeps_same_text_for_different_restaurants(self):
        df = pd.DataFrame({
            "restaurant_id": ["r1", "r2"],
            "review_text": ["Todo muy rico aqui", "Todo muy rico aqui"],
        })
        assert len(deduplicate_reviews(df)) == 2

    def test_drops_too_short_reviews(self):
        df = pd.DataFrame({"restaurant_id": ["r1", "r1"],
                           "review_text": ["Una resena larga y valida", "ok"]})
        assert len(deduplicate_reviews(df)) == 1

    def test_normalize_review_text_ignores_punctuation_and_accents(self):
        assert normalize_review_text("¡Comida excelente!") == normalize_review_text("comida excelente")


class TestRelativeDates:
    """RestaurantGuru publishes "hace 2 años" instead of a date."""

    @pytest.fixture
    def reference(self):
        return pd.Timestamp("2026-07-19")

    def test_parses_months(self, reference):
        assert parse_relative_date("hace 3 meses", reference) == pd.Timestamp("2026-04-19")

    def test_parses_singular_article(self, reference):
        assert parse_relative_date("hace un mes", reference) == pd.Timestamp("2026-06-19")

    def test_parses_years(self, reference):
        assert parse_relative_date("hace 2 años", reference) == pd.Timestamp("2024-07-19")

    def test_returns_none_for_absolute_dates(self, reference):
        assert parse_relative_date("2025-03-12", reference) is None

    def test_standardize_handles_mixed_formats(self, reference):
        series = pd.Series(["2025-03-12", "hace un mes", None])
        result = standardize_dates(series, reference)

        assert pd.api.types.is_datetime64_any_dtype(result)
        assert result.iloc[0] == pd.Timestamp("2025-03-12")
        assert result.iloc[1] == pd.Timestamp("2026-06-19")
        assert pd.isna(result.iloc[2])


class TestPriceVocabulary:
    """Both sources describe price differently; one scale must come out."""

    @pytest.mark.parametrize("label,expected", [
        ("Hasta $15", 1),
        ("Desde $15 hasta $25", 2),
        ("Desde $25 hasta $35", 3),
        ("Más de $35", 4),
        ("$", 1),
        ("$$", 2),
        ("$$$", 3),
        ("$$$$", 4),
    ])
    def test_encode_price(self, label, expected):
        assert encode_price(label) == expected

    def test_encode_price_handles_missing(self):
        assert encode_price(None) is None
        assert encode_price(float("nan")) is None

    def test_price_band_unifies_sources(self):
        df = pd.DataFrame({"price_range": ["Desde $15 hasta $25", "$$"]})
        result = add_price_band(df)
        assert result["price_band"].nunique() == 1

    def test_price_band_is_ordered_by_level(self):
        df = pd.DataFrame({"price_range": ["Hasta $15", "Más de $35"]})
        result = add_price_band(df)
        assert result["price_level"].tolist() == [1.0, 4.0]


class TestCategoricalEncoding:
    """One-hot column names must be clean, unique and regex-safe."""

    def test_column_names_have_no_punctuation(self):
        df = pd.DataFrame({"category_primary": ["Latinoamericana, Contemporanea", "Sushi"]})
        result = encode_categorical_features(df)

        cat_cols = [c for c in result.columns if c.startswith("cat_")]
        assert cat_cols
        for col in cat_cols:
            assert re.fullmatch(r"cat_[a-z0-9_]+", col), f"nombre invalido: {col}"

    def test_accents_are_stripped(self):
        df = pd.DataFrame({"category_primary": ["Panameña"]})
        result = encode_categorical_features(df)
        assert "cat_panamena" in result.columns

    def test_regex_characters_do_not_break_matching(self):
        """Labels like "Bar (Rooftop)" are matched literally, not as a pattern."""
        df = pd.DataFrame({"category_primary": ["Bar (Rooftop)", "Sushi"]})
        result = encode_categorical_features(df)

        col = next(c for c in result.columns if c.startswith("cat_bar"))
        assert result[col].tolist() == [1, 0]

    def test_price_uses_shared_vocabulary(self):
        """Degusta labels must encode properly instead of hitting the fallback."""
        df = pd.DataFrame({"price_range": ["Hasta $15", "Más de $35"]})
        result = encode_categorical_features(df)
        assert result["price_range_encoded"].tolist() == [1.0, 4.0]


class TestCategoryHandling:
    def test_primary_category_takes_first_cuisine(self):
        df = pd.DataFrame({"category": ["Italiana, Pizzeria", "Panamena"]})
        result = add_primary_category(df)
        assert result["category_primary"].tolist() == ["Italiana", "Panamena"]

    def test_separator_is_preserved_as_comma(self):
        """clean_text drops "·", which used to merge two cuisines into one word."""
        df = pd.DataFrame({
            "restaurant_id": ["r1"],
            "restaurant_name": ["Test"],
            "category": ["Española · Argentina"],
        })
        result = clean_dataframe(df)
        assert "," in result["category"].iloc[0]
        assert result["category_primary"].iloc[0] == "Española"
