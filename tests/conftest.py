"""
Pytest configuration and shared fixtures for Restaurant Sentiment Analysis tests.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Sample test data for unit tests
@pytest.fixture
def sample_reviews_df():
    """Create a sample DataFrame with restaurant reviews for testing."""
    data = {
        "restaurant_id": ["rest_1", "rest_1", "rest_2", "rest_2", "rest_3"],
        "restaurant_name": ["Restaurante A", "Restaurante A", "Restaurante B", "Restaurante B", "Restaurante C"],
        "category": ["Italiana", "Italiana", "Mexicana", "Mexicana", "Panameña"],
        "price_range": ["$$ - $$$", "$$ - $$$", "$", "$", "$$$ - $$$$"],
        "overall_rating": [4.5, 4.2, 3.8, 4.0, 4.7],
        "review_text": [
            "La comida estaba deliciosa y el servicio excelente. Muy recomendado!",
            "Buen ambiente y comida sabrosa. El precio es un poco alto.",
            "Comida tradicional muy bien preparada. Lugar tranquilo.",
            "Me encantó el pozole, el servicio fue muy atento.",
            "Excelente cocina local. Los mejores mariscos de la ciudad."
        ],
        "review_date": ["2024-01-15", "2024-01-20", "2024-02-01", "2024-02-10", "2024-02-15"],
        "reviewer_name": ["Juan", "María", "Carlos", "Ana", "Pedro"],
        "source": ["degusta", "degusta", "tripadvisor", "tripadvisor", "degusta"],
        "sentiment_comida_score": [0.8, 0.5, 0.7, 0.9, 0.95],
        "sentiment_servicio_score": [0.9, 0.3, 0.6, 0.8, 0.85],
        "sentiment_precio_score": [0.0, -0.3, 0.5, 0.4, -0.2],
        "sentiment_ambiente_score": [0.7, 0.6, 0.8, 0.5, 0.9],
        "word_count": [12, 15, 10, 8, 14],
        "char_count": [78, 95, 62, 52, 88],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_clustered_df():
    """Create a sample DataFrame with clustered restaurants for testing."""
    data = {
        "restaurant_id": ["rest_1", "rest_1", "rest_2", "rest_2", "rest_3", "rest_3"],
        "restaurant_name": ["Restaurante A", "Restaurante A", "Restaurante B", "Restaurante B", "Restaurante C", "Restaurante C"],
        "category": ["Italiana", "Italiana", "Mexicana", "Mexicana", "Panameña", "Panameña"],
        "price_range": ["$$ - $$$", "$$ - $$$", "$", "$", "$$$ - $$$$", "$$$ - $$$$"],
        "overall_rating": [4.5, 4.2, 3.8, 4.0, 4.7, 4.8],
        "review_text": [
            "Excelente comida italiana!",
            "Muy buenos pastas y pizzas.",
            "Comida mexicana auténtica.",
            "Los tacos están increíbles.",
            "Mariscos frescos y bien preparados.",
            "El ceviche es espectacular."
        ],
        "location": ["Casco Viejo", "Casco Viejo", "Via Argentina", "Via Argentina", "Marbella", "Marbella"],
        "cluster": [0, 0, 1, 1, 2, 2],
        "sentiment_comida_score": [0.8, 0.7, 0.6, 0.85, 0.95, 0.9],
        "sentiment_servicio_score": [0.9, 0.8, 0.5, 0.6, 0.85, 0.8],
        "sentiment_precio_score": [0.0, -0.1, 0.5, 0.6, -0.2, -0.1],
        "sentiment_ambiente_score": [0.7, 0.6, 0.4, 0.5, 0.9, 0.85],
        "word_count": [5, 4, 4, 5, 6, 5],
        "char_count": [30, 28, 25, 32, 38, 35],
    }
    return pd.DataFrame(data)


@pytest.fixture
def raw_reviews_df():
    """Create raw reviews DataFrame similar to scraped data."""
    data = {
        "restaurant_id": ["rest_1", "rest_1", "rest_2"],
        "restaurant_name": ["Restaurante Test", "Restaurante Test", "Otro Restaurante"],
        "category": ["Italiana", "Italiana", "Mexicana"],
        "price_range": ["$$ - $$$", "$$ - $$$", "$"],
        "overall_rating": [4.5, 4.5, 3.5],
        "review_text": [
            "La comida estaba <b>excelente</b>! Visiten http://example.com",
            "Muy buen servicio y ambiente.",
            "Comida regular, precio algo alto."
        ],
        "review_date": ["2024-01-15", "2024-01-16", "2024-01-17"],
        "reviewer_name": ["Usuario1", "Usuario2", "Usuario3"],
        "source": ["degusta", "degusta", "tripadvisor"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def processed_data_path():
    """Return path to processed data file if it exists."""
    path = Path("data/processed/restaurants_clustered.csv")
    if path.exists():
        return str(path)
    return None


@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory structure for testing."""
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"

    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)

    return data_dir
