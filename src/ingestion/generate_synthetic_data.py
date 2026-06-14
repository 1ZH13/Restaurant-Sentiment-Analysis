"""
Generate synthetic review data for testing the pipeline.
This creates realistic reviews based on restaurant ratings.
"""

import pandas as pd
import random
from datetime import datetime, timedelta
import os

# Sample review templates for different sentiment combinations
POSITIVE_FOOD = [
    "La comida estaba deliciosa, especialmente el {}.",
    "Excelente calidad en los ingredientes, el {} estaba perfectamente preparado.",
    "El {} estaba increíble, los sabores eran únicos.",
    "Gran experiencia culinaria, el {} superó nuestras expectativas.",
    "Comida exquisita, el {} es simplemente perfecto."
]

NEGATIVE_FOOD = [
    "La comida no estuvo a la altura, el {} estaba demasiado cocido.",
    "失望 (Decepcionado) con el {}, no tenía sabor.",
    "El {} estaba frío cuando llegó a la mesa.",
    "No recomendaría el {}, la calidad no justifica el precio.",
    "El {} no estaba bueno, parece que usan ingredientes de baja calidad."
]

POSITIVE_SERVICE = [
    "El servicio fue excepcional, muy atentos y amables.",
    "Excelente atención del personal, nos trataron muy bien.",
    "Los meseros fueron muy profesionales ycordiales.",
    "Buen servicio, siempre estaban pendientes de nosotros.",
    "La atención fue rápida y muy amable."
]

NEGATIVE_SERVICE = [
    "El servicio fue muy lento, esperamos demasiado.",
    "La atención dejó mucho que desear, parecía que no les importaba.",
    "Tardaron mucho en traernos la cuenta.",
    "El personal no era muy amable.",
    "Servicio deficiente, no lo recomiendo."
]

POSITIVE_AMBIANCE = [
    "El ambiente es muy acogedor y bien decorado.",
    "Lugar perfecto para una cena romántica, el ambiente es increíble.",
    "Bonito local, la decoración es muy elegante.",
    "Me gustó mucho el ambiente, muy tranquilo y relajante.",
    "El lugar es muy bonito, ideal para especiales ocasiones."
]

NEGATIVE_AMBIANCE = [
    "El ambiente es muy ruidoso, difícil conversar.",
    "El local no tiene buena ventilación.",
    "La decoración podría mejorar, se ve algo anticuado.",
    "No me gustó el ambiente, demasiado oscuro.",
    "El lugar está bien pero el ruido molesta."
]

POSITIVE_PRICE = [
    "Buena relación calidad-precio.",
    "El precio es razonable para la calidad que ofrecen.",
    "Vale la pena el costo, excelente valor.",
    "Precios justos para lo que ofrecen.",
    "Buen precio por la experiencia."
]

NEGATIVE_PRICE = [
    "Muy caro para lo que ofrecen.",
    "Los precios son elevados, no corresponde a la calidad.",
    "No vale la pena el costo, demasiado caro.",
    "Precios excesivos para un restaurante normal.",
    "El precio está muy alto para esta zona."
]

DISHES = ["risotto", "pasta", "steak", "salmón", "pollo", "ensalada", "postre", "sopa", "mariscos", "arroz"]


def generate_review_text(rating: float, aspect_preferences: dict = None) -> tuple:
    """Generate a review text and return (text, comida, servicio, precio, ambiente) sentiment."""
    if aspect_preferences is None:
        aspect_preferences = {k: random.choice(['positive', 'positive', 'positive', 'neutral']) for k in ['comida', 'servicio', 'precio', 'ambiente']}

    dish = random.choice(DISHES)
    parts = []

    for aspect, sentiment in aspect_preferences.items():
        if sentiment == 'positive':
            if aspect == 'comida':
                parts.append(random.choice(POSITIVE_FOOD).format(dish))
            elif aspect == 'servicio':
                parts.append(random.choice(POSITIVE_SERVICE))
            elif aspect == 'ambiente':
                parts.append(random.choice(POSITIVE_AMBIANCE))
            elif aspect == 'precio':
                parts.append(random.choice(POSITIVE_PRICE))
        elif sentiment == 'negative':
            if aspect == 'comida':
                parts.append(random.choice(NEGATIVE_FOOD).format(dish))
            elif aspect == 'servicio':
                parts.append(random.choice(NEGATIVE_SERVICE))
            elif aspect == 'ambiente':
                parts.append(random.choice(NEGATIVE_AMBIANCE))
            elif aspect == 'precio':
                parts.append(random.choice(NEGATIVE_PRICE))

    # Add some variation based on overall rating
    if rating >= 4.5:
        parts.append("En general, muy recomendado.")
    elif rating >= 4.0:
        parts.append("Buen restaurante, lo visitaría de nuevo.")
    elif rating >= 3.5:
        parts.append("Restaurante aceptable.")
    else:
        parts.append("No lo recomiendo.")

    return " ".join(parts), aspect_preferences


def generate_reviews_for_restaurant(restaurant_row: pd.Series, n_reviews: int = 20) -> list:
    """Generate multiple reviews for a restaurant."""
    reviews = []
    rating = restaurant_row.get('overall_rating', 4.0)

    for i in range(n_reviews):
        # Vary the review rating around the restaurant's average
        review_rating = max(1.0, min(5.0, rating + random.uniform(-1.0, 1.0)))

        # Determine sentiment distribution based on rating
        if review_rating >= 4.5:
            sentiments = {k: 'positive' for k in ['comida', 'servicio', 'ambiente']}
            if random.random() > 0.3:
                sentiments['precio'] = 'positive'
        elif review_rating >= 4.0:
            sentiments = {k: random.choice(['positive', 'positive', 'neutral']) for k in ['comida', 'servicio', 'ambiente']}
        elif review_rating >= 3.0:
            sentiments = {k: random.choice(['positive', 'neutral', 'negative']) for k in ['comida', 'servicio', 'ambiente']}
        else:
            sentiments = {k: random.choice(['negative', 'negative', 'neutral']) for k in ['comida', 'servicio', 'ambiente']}

        text, _ = generate_review_text(review_rating, sentiments)

        # Generate random date in the last 6 months
        days_ago = random.randint(0, 180)
        review_date = datetime.now() - timedelta(days=days_ago)

        reviews.append({
            'restaurant_id': restaurant_row['restaurant_id'],
            'restaurant_name': restaurant_row['restaurant_name'],
            'category': restaurant_row.get('category', 'General'),
            'location': restaurant_row.get('location', 'Panama City'),
            'price_range': restaurant_row.get('price_range', '$$ - $$$'),
            'overall_rating': rating,
            'food_rating': rating + random.uniform(-0.3, 0.3),
            'service_rating': rating + random.uniform(-0.3, 0.3),
            'ambiance_rating': rating + random.uniform(-0.3, 0.3),
            'review_text': text,
            'review_date': review_date.strftime('%Y-%m-%d'),
            'reviewer_name': f"User{random.randint(1000, 9999)}",
            'source': 'degusta_synthetic',
            'aspect_sentiments': sentiments
        })

    return reviews


def main():
    """Generate synthetic dataset."""
    print("Loading restaurant data...")
    df_restaurants = pd.read_csv('data/raw/degusta_restaurants.csv')

    print(f"Found {len(df_restaurants)} restaurants")
    print(df_restaurants[['restaurant_id', 'restaurant_name', 'overall_rating']].head())

    all_reviews = []

    print("\nGenerating synthetic reviews...")
    for idx, row in df_restaurants.iterrows():
        n_reviews = random.randint(15, 30)
        reviews = generate_reviews_for_restaurant(row, n_reviews)
        all_reviews.extend(reviews)
        print(f"  {row['restaurant_name']}: {len(reviews)} reviews")

    df_reviews = pd.DataFrame(all_reviews)

    # Save
    output_path = 'data/raw/synthetic_reviews.csv'
    df_reviews.to_csv(output_path, index=False)
    print(f"\nSaved {len(df_reviews)} synthetic reviews to {output_path}")

    # Print summary
    print("\nDataset summary:")
    print(f"  Total reviews: {len(df_reviews)}")
    print(f"  Total restaurants: {df_reviews['restaurant_id'].nunique()}")
    print(f"  Average rating: {df_reviews['overall_rating'].mean():.2f}")

    return df_reviews


if __name__ == "__main__":
    main()
