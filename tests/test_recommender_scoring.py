"""
Tests for the recommender's match score.

The score is rendered in the dashboard as "N% coincidencia". It used to be a
raw average of unnormalised magnitudes, landing around 1-3, so every
recommendation displayed "1% coincidencia" and the colour thresholds (>=80
green, >=60 amber) could never trigger. It must be a real 0-100 percentage.
"""

import pandas as pd
import pytest

from src.recommendation.recommender import RestaurantRecommender


@pytest.fixture
def restaurants():
    return pd.DataFrame({
        "restaurant_id": ["r1", "r2", "r3"],
        "restaurant_name": ["Sushi Uno", "Pizza Nova", "Cafe Central"],
        "category": ["Japonesa", "Italiana", "Cafeteria"],
        "price_range": ["Más de $35", "Desde $15 hasta $25", "Hasta $15"],
        "location": ["Obarrio", "Marbella", "Obarrio"],
        "overall_rating": [4.9, 4.2, 3.8],
        "review_text": ["muy bueno", "rico", "aceptable"],
        "sentiment_comida_score": [1.0, 0.5, -0.5],
        "sentiment_servicio_score": [1.0, 0.0, 0.0],
        "sentiment_precio_score": [-1.0, 1.0, 1.0],
        "sentiment_ambiente_score": [1.0, 0.0, 0.0],
    })


@pytest.fixture
def recommender(restaurants):
    return RestaurantRecommender(restaurants)


class TestMatchScoreRange:
    def test_score_is_a_percentage(self, recommender):
        results = recommender.recommend({"priority_aspects": ["comida"]}, top_n=5)
        assert results
        for rec in results:
            assert 0.0 <= rec.match_score <= 100.0

    def test_good_match_scores_high(self, recommender):
        """A restaurant matching cuisine, budget, zone and aspects scores well."""
        results = recommender.recommend({
            "category": "Japonesa",
            "max_price": "Más de $35",
            "location": "Obarrio",
            "priority_aspects": ["comida", "servicio"],
        }, top_n=1)

        assert results[0].restaurant_name == "Sushi Uno"
        assert results[0].match_score >= 80

    def test_poor_match_scores_lower_than_good_match(self, recommender):
        preferences = {"category": "Japonesa", "priority_aspects": ["comida"]}
        results = recommender.recommend(preferences, top_n=3)
        by_name = {r.restaurant_name: r.match_score for r in results}
        assert by_name["Sushi Uno"] > by_name["Cafe Central"]


class TestPreferencesAreHonoured:
    def test_location_preference_changes_ranking(self, recommender):
        """Location was accepted by the API but never used in the score."""
        marbella = recommender.recommend({"location": "Marbella"}, top_n=3)
        obarrio = recommender.recommend({"location": "Obarrio"}, top_n=3)

        marbella_scores = {r.restaurant_name: r.match_score for r in marbella}
        obarrio_scores = {r.restaurant_name: r.match_score for r in obarrio}

        assert marbella_scores["Pizza Nova"] > obarrio_scores["Pizza Nova"]

    def test_budget_uses_real_price_vocabulary(self, recommender):
        """Degusta labels like "Hasta $15" must be understood, not defaulted."""
        cheap = recommender.recommend({"max_price": "Hasta $15"}, top_n=3)
        scores = {r.restaurant_name: r.match_score for r in cheap}
        assert scores["Cafe Central"] > scores["Sushi Uno"]

    def test_priority_aspect_changes_ranking(self, recommender):
        by_price = recommender.recommend({"priority_aspects": ["precio"]}, top_n=3)
        by_food = recommender.recommend({"priority_aspects": ["comida"]}, top_n=3)

        assert by_price[0].restaurant_name != "Sushi Uno"
        assert by_food[0].restaurant_name == "Sushi Uno"

    def test_results_are_sorted_descending(self, recommender):
        results = recommender.recommend({"priority_aspects": ["comida"]}, top_n=3)
        scores = [r.match_score for r in results]
        assert scores == sorted(scores, reverse=True)
