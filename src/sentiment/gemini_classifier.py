"""
LLM-based aspect sentiment classifier using Google Gemini.
"""

import os
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import google.generativeai as genai
except ImportError:
    genai = None


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    comida: str  # positive, negative, neutral
    servicio: str
    precio: str
    ambiente: str

    def to_dict(self) -> Dict:
        return {
            "comida": self.comida,
            "servicio": self.servicio,
            "precio": self.precio,
            "ambiente": self.ambiente
        }


ASPECT_SENTIMENT_PROMPT = """You are a restaurant review analyzer. For the following review, extract and classify
the sentiment for each of these aspects: Comida (Food), Servicio (Service), Precio (Price),
Ambiente (Ambiance/Atmosphere).

Review: "{review_text}"

Respond ONLY with a valid JSON object in this exact format:
{{
    "comida": "positive" | "negative" | "neutral",
    "servicio": "positive" | "negative" | "neutral",
    "precio": "positive" | "negative" | "neutral",
    "ambiente": "positive" | "negative" | "neutral"
}}

If an aspect is not mentioned, use "neutral". Only respond with the JSON, nothing else."""


class AspectSentimentClassifier:
    """Classifier using Google Gemini for aspect-based sentiment analysis."""

    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        """
        Initialize the classifier.

        Args:
            model_name: Gemini model to use (e.g., 'gemini-2.5-flash')
            api_key: Google API key
        """
        if genai is None:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

        self.model_name = model_name

        if api_key:
            genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(model_name)

    def analyze_review(self, review_text: str) -> SentimentResult:
        """Analyze a single review and return aspect sentiments."""
        if not review_text or len(review_text.strip()) < 5:
            return SentimentResult(
                comida="neutral",
                servicio="neutral",
                precio="neutral",
                ambiente="neutral"
            )

        try:
            prompt = ASPECT_SENTIMENT_PROMPT.format(review_text=review_text)
            response = self.model.generate_content(prompt)

            result_text = response.text.strip()

            # Parse JSON response
            # Clean up potential markdown code blocks
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "".join(lines[1:-1])

            result_dict = json.loads(result_text)

            return SentimentResult(
                comida=result_dict.get("comida", "neutral"),
                servicio=result_dict.get("servicio", "neutral"),
                precio=result_dict.get("precio", "neutral"),
                ambiente=result_dict.get("ambiente", "neutral")
            )

        except Exception as e:
            print(f"Error analyzing review: {e}")
            return SentimentResult(
                comida="neutral",
                servicio="neutral",
                precio="neutral",
                ambiente="neutral"
            )

    def analyze_batch(self, reviews: List[str], delay: float = 0.5) -> List[SentimentResult]:
        """Analyze multiple reviews with rate limiting."""
        results = []

        for i, review in enumerate(reviews):
            if i % 10 == 0 and i > 0:
                print(f"Processed {i}/{len(reviews)} reviews...")

            result = self.analyze_review(review)
            results.append(result)

            # Rate limiting - Gemini free tier has limits
            time.sleep(delay)

        return results

    def to_numeric_score(self, sentiment: str) -> float:
        """Convert sentiment string to numeric score."""
        mapping = {
            "positive": 1.0,
            "neutral": 0.0,
            "negative": -1.0
        }
        return mapping.get(sentiment.lower(), 0.0)


def load_cache(cache_path: str) -> Dict:
    """Load sentiment results from cache."""
    try:
        with open(cache_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache: Dict, cache_path: str):
    """Save sentiment results to cache."""
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def process_reviews_with_cache(reviews: List[str], classifier: AspectSentimentClassifier,
                               cache_path: str = "data/cache/sentiment_cache.json") -> List[SentimentResult]:
    """Process reviews with caching to avoid re-analyzing same text."""
    cache = load_cache(cache_path)
    results = []

    for i, review in enumerate(reviews):
        if i % 50 == 0:
            print(f"Processing review {i+1}/{len(reviews)}...")

        review_hash = str(hash(review))

        if review_hash in cache:
            cached = cache[review_hash]
            results.append(SentimentResult(
                comida=cached["comida"],
                servicio=cached["servicio"],
                precio=cached["precio"],
                ambiente=cached["ambiente"]
            ))
        else:
            result = classifier.analyze_review(review)
            results.append(result)
            cache[review_hash] = result.to_dict()

            # Save cache periodically
            if len(cache) % 100 == 0:
                save_cache(cache, cache_path)

    # Final save
    save_cache(cache, cache_path)

    return results


def main():
    """Example usage."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    classifier = AspectSentimentClassifier(
        model_name="gemini-2.5-flash",
        api_key=api_key
    )

    test_reviews = [
        "La comida estuvo excelente pero el servicio fue lento y el precio muy alto.",
        "Buen ambiente y comida deliciosa, pero el servicio dejó mucho que desear.",
        "El restaurante es hermoso, la comida espectacular, muy recomendado!"
    ]

    for review in test_reviews:
        result = classifier.analyze_review(review)
        print(f"Review: {review[:50]}...")
        print(f"Sentiment: {result.to_dict()}")
        print()


if __name__ == "__main__":
    main()
