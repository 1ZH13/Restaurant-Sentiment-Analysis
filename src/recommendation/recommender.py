"""
Restaurant recommendation system using content-based filtering.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.preprocessing.cleaner import encode_price

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass
class RecommendationResult:
    """A restaurant recommendation with explanation."""
    restaurant_id: str
    restaurant_name: str
    category: str
    overall_rating: float
    price_range: str
    match_score: float
    explanation: str


class RestaurantRecommender:
    """Content-based restaurant recommender system."""

    def __init__(self, df: pd.DataFrame, llm_client=None):
        """
        Initialize recommender with restaurant data.

        Args:
            df: DataFrame with restaurant data
            llm_client: Optional OpenAI client for generating explanations
        """
        self.df = df
        self.llm_client = llm_client

        # Precompute restaurant-level aggregates
        self.restaurant_profiles = self._compute_restaurant_profiles()

    def _compute_restaurant_profiles(self) -> pd.DataFrame:
        """Compute aggregated profiles per restaurant."""
        if "restaurant_id" not in self.df.columns:
            return self.df

        # Build aggregation dict dynamically
        agg_dict = {
            "restaurant_name": "first",
            "category": "first",
            "overall_rating": "mean",
            "price_range": "first",
            "location": "first",
        }
        if "review_count" in self.df.columns:
            agg_dict["review_count"] = "first"
        else:
            agg_dict["review_text"] = "count"

        # Group by restaurant
        profiles = self.df.groupby("restaurant_id").agg(agg_dict).reset_index()

        if "review_text" in profiles.columns:
            profiles.rename(columns={"review_text": "review_count"}, inplace=True)

        # Sentiment averages
        sentiment_cols = [col for col in self.df.columns if col.startswith("sentiment_") and col.endswith("_score")]
        if sentiment_cols:
            sentiment_agg = self.df.groupby("restaurant_id")[sentiment_cols].mean().reset_index()
            profiles = profiles.merge(sentiment_agg, on="restaurant_id")

        return profiles

    def _calculate_match_score(self, restaurant: pd.Series, preferences: Dict) -> float:
        """Score how well a restaurant matches the preferences, from 0 to 100.

        Each criterion contributes a 0-1 fraction of its own weight, and the
        total is divided by the weights actually used. The previous version
        summed raw magnitudes and divided by the *count* of weights, producing
        values around 1-3 that the dashboard then rendered as "2% coincidencia".
        """
        earned = 0.0
        total_weight = 0.0

        # Category match
        if preferences.get("category"):
            weight = 3.0
            category = str(restaurant.get("category", "")).lower()
            if category and preferences["category"].lower() in category:
                earned += weight
            total_weight += weight

        # Price range: full credit at or below budget, tapering off above it.
        if preferences.get("max_price"):
            weight = 2.0
            restaurant_price = encode_price(restaurant.get("price_range"))
            max_price = encode_price(preferences["max_price"])
            if restaurant_price is not None and max_price is not None:
                if restaurant_price <= max_price:
                    earned += weight
                else:
                    over = restaurant_price - max_price
                    earned += weight * max(0.0, 1.0 - over / 3.0)
                total_weight += weight

        # Location match
        if preferences.get("location"):
            weight = 2.0
            location = str(restaurant.get("location", "")).lower()
            if location and preferences["location"].lower() in location:
                earned += weight
            total_weight += weight

        # Priority aspects: map sentiment from [-1, 1] onto [0, 1].
        for aspect in preferences.get("priority_aspects", []) or []:
            col = f"sentiment_{aspect}_score"
            if col in restaurant.index and pd.notna(restaurant.get(col)):
                weight = 3.0
                sentiment = float(restaurant.get(col))
                earned += weight * (sentiment + 1.0) / 2.0
                total_weight += weight

        # Rating always contributes so ties break towards better restaurants.
        if pd.notna(restaurant.get("overall_rating")):
            weight = 2.0
            earned += weight * float(restaurant.get("overall_rating")) / 5.0
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(earned / total_weight * 100.0, 1)

    def recommend(self, preferences: Dict, top_n: int = 5) -> List[RecommendationResult]:
        """
        Generate recommendations based on user preferences.

        Args:
            preferences: Dict with keys:
                - category: preferred cuisine type
                - max_price: maximum price range ($, $$ - $$$, etc.)
                - priority_aspects: list of aspects that matter most (comida, servicio, precio, ambiente)
                - location: preferred neighborhood (optional)
            top_n: number of recommendations to return

        Returns:
            List of RecommendationResult objects
        """
        recommendations = []

        for _, restaurant in self.restaurant_profiles.iterrows():
            match_score = self._calculate_match_score(restaurant, preferences)

            if match_score > 0:
                # Generate explanation
                explanation = self._generate_explanation(restaurant, preferences, match_score)

                recommendations.append(RecommendationResult(
                    restaurant_id=str(restaurant.get("restaurant_id", "")),
                    restaurant_name=str(restaurant.get("restaurant_name", "")),
                    category=str(restaurant.get("category", "")),
                    overall_rating=float(restaurant.get("overall_rating", 0)) if pd.notna(restaurant.get("overall_rating")) else 0.0,
                    price_range=str(restaurant.get("price_range", "")),
                    match_score=match_score,
                    explanation=explanation
                ))

        # Sort by match score and return top N
        recommendations.sort(key=lambda x: x.match_score, reverse=True)
        return recommendations[:top_n]

    def _generate_explanation(self, restaurant: pd.Series, preferences: Dict, score: float) -> str:
        """Generate human-readable explanation for recommendation."""
        parts = []

        # Rating
        if pd.notna(restaurant.get("overall_rating")):
            rating = float(restaurant.get("overall_rating"))
            if rating >= 4.5:
                parts.append(f"Excelente calificación de {rating:.1f}/5.0")
            elif rating >= 4.0:
                parts.append(f"Buena calificación de {rating:.1f}/5.0")

        # Category
        if preferences.get("category") and restaurant.get("category"):
            if preferences["category"].lower() in str(restaurant.get("category")).lower():
                parts.append(f"Categoría: {restaurant.get('category')}")

        # Sentiment highlights
        for aspect in ["comida", "servicio", "ambiente"]:
            col = f"sentiment_{aspect}_score"
            if col in restaurant.index and pd.notna(restaurant.get(col)):
                sentiment = float(restaurant.get(col))
                if sentiment > 0.5:
                    aspect_names = {"comida": "comida", "servicio": "servicio",
                                   "ambiente": "ambiente", "precio": "precio"}
                    parts.append(f"Muy buenas reseñas sobre {aspect_names.get(aspect, aspect)}")

        if not parts:
            parts.append("Combina bien con tus preferencias")

        return ". ".join(parts) + "."

    def generate_llm_explanation(self, restaurant: RecommendationResult,
                                 preferences: Dict) -> str:
        """Generate detailed explanation using LLM."""
        if not self.llm_client:
            return restaurant.explanation

        prompt = f"""Eres un asistente que recomienda restaurantes en Panamá.

El usuario busca: {preferences}

Recomendación:
- Restaurante: {restaurant.restaurant_name}
- Categoría: {restaurant.category}
- Calificación: {restaurant.overall_rating}/5.0
- Precio: {restaurant.price_range}
- Puntuación de coincidencia: {restaurant.match_score:.2f}

Escribe una explicación breve (2-3 oraciones) de por qué este restaurante es una buena opción para el usuario.
Usa español y sé conciso.
"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Falló la explicación con LLM: {e}")
            return restaurant.explanation


def main():
    """Example usage."""
    # Load data
    try:
        df = pd.read_csv("data/processed/restaurants_clustered.csv")
    except FileNotFoundError:
        print("Ejecuta primero el módulo de agrupamiento para generar los datos requeridos.")
        return

    # Initialize recommender
    recommender = RestaurantRecommender(df)

    # Example preferences
    preferences = {
        "category": "italiana",
        "max_price": "$$ - $$$",
        "priority_aspects": ["comida", "servicio"],
        "location": None
    }

    # Get recommendations
    recommendations = recommender.recommend(preferences, top_n=5)

    print("Recomendaciones para comida italiana, rango de precio medio, priorizando comida y servicio:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec.restaurant_name}")
        print(f"   Categoría: {rec.category}")
        print(f"   Calificación: {rec.overall_rating:.1f}/5.0")
        print(f"   Precio: {rec.price_range}")
        print(f"   Puntaje de coincidencia: {rec.match_score:.2f}")
        print(f"   Explicación: {rec.explanation}")


if __name__ == "__main__":
    main()
