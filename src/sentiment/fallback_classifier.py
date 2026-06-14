"""
Fallback sentiment classifiers using VADER and TextBlob.
These are used when LLM is not available or as a comparison baseline.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


ASPECT_KEYWORDS = {
    "comida": ["comida", "food", "plato", "platillo", "dish", "sabor", "sabores", "menu", "cocina", "chef", "carnes", "pescado", "ensalada", "sopa", "postre"],
    "servicio": ["servicio", "service", "atencion", "mesero", "mesera", "camarero", "camarera", "mozo", "personal", "empleados", "staff"],
    "precio": ["precio", "price", "cost", "caro", "expensive", "barato", "cheap", "vale", "worth", "dinero", "bill", "cuenta", "pagar"],
    "ambiente": ["ambiente", "ambiance", "ambience", "ambiente", "ambiente", "decoracion", "decoration", "lugar", "place", "espacio", "vista", "music", "musica", "ruido", "noise"]
}


class VADERSentimentAnalyzer:
    """Fallback sentiment analyzer using VADER."""

    def __init__(self):
        if not VADER_AVAILABLE:
            raise ImportError("VADER not available. Run: pip install vaderSentiment")
        self.analyzer = SentimentIntensityAnalyzer()

    def get_compound_score(self, text: str) -> float:
        """Get compound sentiment score (-1 to 1)."""
        if not text:
            return 0.0
        scores = self.analyzer.polarity_scores(str(text))
        return scores["compound"]

    def classify(self, text: str, threshold: float = 0.05) -> str:
        """Classify sentiment as positive, negative, or neutral."""
        score = self.get_compound_score(text)
        if score >= threshold:
            return "positive"
        elif score <= -threshold:
            return "negative"
        else:
            return "neutral"

    def get_aspect_sentiment(self, text: str) -> Dict[str, str]:
        """Get sentiment for each aspect based on keyword extraction."""
        result = {
            "comida": "neutral",
            "servicio": "neutral",
            "precio": "neutral",
            "ambiente": "neutral"
        }

        if not text:
            return result

        text_lower = text.lower()

        for aspect, keywords in ASPECT_KEYWORDS.items():
            # Find sentences containing the aspect keywords
            sentences = text.split(".")
            aspect_sentences = []

            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(keyword.lower() in sentence_lower for keyword in keywords):
                    aspect_sentences.append(sentence)

            if aspect_sentences:
                # Analyze combined aspect-related sentences
                aspect_text = " ".join(aspect_sentences)
                result[aspect] = self.classify(aspect_text)

        return result

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, str]]:
        """Analyze multiple texts."""
        return [self.get_aspect_sentiment(text) for text in texts]


class TextBlobAnalyzer:
    """Fallback sentiment analyzer using TextBlob."""

    def __init__(self):
        if not TEXTBLOB_AVAILABLE:
            raise ImportError("TextBlob not available. Run: pip install textblob")

    def get_polarity(self, text: str) -> float:
        """Get polarity score (-1 to 1)."""
        if not text:
            return 0.0
        return TextBlob(str(text)).sentiment.polarity

    def classify(self, text: str, threshold: float = 0.1) -> str:
        """Classify sentiment as positive, negative, or neutral."""
        polarity = self.get_polarity(text)
        if polarity >= threshold:
            return "positive"
        elif polarity <= -threshold:
            return "negative"
        else:
            return "neutral"

    def get_aspect_sentiment(self, text: str) -> Dict[str, str]:
        """Get sentiment for each aspect based on keyword extraction."""
        result = {
            "comida": "neutral",
            "servicio": "neutral",
            "precio": "neutral",
            "ambiente": "neutral"
        }

        if not text:
            return result

        for aspect, keywords in ASPECT_KEYWORDS.items():
            sentences = text.split(".")
            aspect_sentences = []

            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(keyword.lower() in sentence_lower for keyword in keywords):
                    aspect_sentences.append(sentence)

            if aspect_sentences:
                aspect_text = " ".join(aspect_sentences)
                result[aspect] = self.classify(aspect_text)

        return result

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, str]]:
        """Analyze multiple texts."""
        return [self.get_aspect_sentiment(text) for text in texts]


class HybridSentimentAnalyzer:
    """Hybrid analyzer combining VADER, TextBlob, and optionally LLM."""

    def __init__(self, use_llm: bool = True, llm_classifier=None):
        self.use_llm = use_llm
        self.llm_classifier = llm_classifier

        if VADER_AVAILABLE:
            self.vader = VADERSentimentAnalyzer()
        else:
            self.vader = None

        if TEXTBLOB_AVAILABLE:
            self.textblob = TextBlobAnalyzer()
        else:
            self.textblob = None

    def analyze_review(self, review_text: str) -> Dict[str, str]:
        """Analyze a single review."""
        if not review_text:
            return {
                "comida": "neutral",
                "servicio": "neutral",
                "precio": "neutral",
                "ambiente": "neutral"
            }

        # Try LLM first if available
        if self.use_llm and self.llm_classifier:
            try:
                result = self.llm_classifier.analyze_review(review_text)
                return result.to_dict()
            except Exception as e:
                print(f"LLM failed, falling back to VADER: {e}")

        # Fallback to VADER
        if self.vader:
            return self.vader.get_aspect_sentiment(review_text)

        # Fallback to TextBlob
        if self.textblob:
            return self.textblob.get_aspect_sentiment(review_text)

        # Ultimate fallback
        return {
            "comida": "neutral",
            "servicio": "neutral",
            "precio": "neutral",
            "ambiente": "neutral"
        }

    def analyze_batch(self, reviews: List[str]) -> List[Dict[str, str]]:
        """Analyze multiple reviews."""
        return [self.analyze_review(review) for review in reviews]


def sentiment_to_numeric(sentiment: str) -> float:
    """Convert sentiment string to numeric score."""
    mapping = {
        "positive": 1.0,
        "neutral": 0.0,
        "negative": -1.0
    }
    return mapping.get(sentiment.lower(), 0.0)


def add_sentiment_columns(df: pd.DataFrame, sentiment_column: str = "sentiment") -> pd.DataFrame:
    """Add numeric sentiment score columns based on sentiment strings."""
    df = df.copy()

    aspects = ["comida", "servicio", "precio", "ambiente"]

    for aspect in aspects:
        col_name = f"sentiment_{aspect}"
        sentiment_col = f"{sentiment_column}_{aspect}" if sentiment_column else col_name

        if sentiment_col in df.columns:
            df[f"{col_name}_score"] = df[sentiment_col].apply(sentiment_to_numeric)
        elif col_name in df.columns:
            df[f"{col_name}_score"] = df[col_name].apply(sentiment_to_numeric)

    # Overall sentiment score
    score_cols = [f"{aspect}_score" for aspect in aspects]
    existing_score_cols = [col for col in score_cols if col in df.columns]

    if existing_score_cols:
        df["overall_sentiment_score"] = df[existing_score_cols].mean(axis=1)

    return df


def main():
    """Example usage."""
    test_reviews = [
        "La comida estuvo excelente pero el servicio fue lento.",
        "Buen ambiente y comida deliciosa, muy recomendado!",
        "El precio es muy alto para la calidad que ofrecen.",
        "Excelente lugar para ir con amigos, la атмосфера es increíble."
    ]

    if VADER_AVAILABLE:
        print("Using VADER:")
        vader = VADERSentimentAnalyzer()
        for review in test_reviews:
            result = vader.get_aspect_sentiment(review)
            print(f"Review: {review[:40]}...")
            print(f"Sentiment: {result}")
            print()

    if TEXTBLOB_AVAILABLE:
        print("Using TextBlob:")
        tb = TextBlobAnalyzer()
        for review in test_reviews:
            result = tb.get_aspect_sentiment(review)
            print(f"Review: {review[:40]}...")
            print(f"Sentiment: {result}")
            print()


if __name__ == "__main__":
    main()
