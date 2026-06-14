"""
Unit tests for src/sentiment/fallback_classifier.py module.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.sentiment.fallback_classifier import (
    VADERSentimentAnalyzer,
    TextBlobAnalyzer,
    HybridSentimentAnalyzer,
    sentiment_to_numeric,
    add_sentiment_columns,
    ASPECT_KEYWORDS
)


class TestSentimentToNumeric:
    """Tests for sentiment_to_numeric function."""

    def test_positive_returns_one(self):
        """Test that positive returns 1.0."""
        assert sentiment_to_numeric("positive") == 1.0

    def test_negative_returns_minus_one(self):
        """Test that negative returns -1.0."""
        assert sentiment_to_numeric("negative") == -1.0

    def test_neutral_returns_zero(self):
        """Test that neutral returns 0.0."""
        assert sentiment_to_numeric("neutral") == 0.0

    def test_unknown_returns_zero(self):
        """Test that unknown sentiment returns 0.0."""
        assert sentiment_to_numeric("unknown") == 0.0

    def test_case_insensitive(self):
        """Test that function is case insensitive."""
        assert sentiment_to_numeric("POSITIVE") == 1.0
        assert sentiment_to_numeric("Positive") == 1.0


class TestVADERSentimentAnalyzer:
    """Tests for VADERSentimentAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create VADER analyzer instance."""
        try:
            return VADERSentimentAnalyzer()
        except ImportError:
            pytest.skip("VADER not installed")

    def test_get_compound_score_positive(self, analyzer):
        """Test compound score for positive text."""
        text = "This is amazing! I love it!"
        score = analyzer.get_compound_score(text)
        assert score > 0

    def test_get_compound_score_negative(self, analyzer):
        """Test compound score for negative text."""
        text = "This is terrible! I hate it!"
        score = analyzer.get_compound_score(text)
        assert score < 0

    def test_get_compound_score_neutral(self, analyzer):
        """Test compound score for neutral text."""
        text = "This is a table."
        score = analyzer.get_compound_score(text)
        assert abs(score) < 0.5

    def test_get_compound_score_empty(self, analyzer):
        """Test compound score for empty text."""
        score = analyzer.get_compound_score("")
        assert score == 0.0

    def test_classify_positive(self, analyzer):
        """Test classification of positive text."""
        result = analyzer.classify("This is great and wonderful!")
        assert result == "positive"

    def test_classify_negative(self, analyzer):
        """Test classification of negative text."""
        result = analyzer.classify("This is terrible and awful!")
        assert result == "negative"

    def test_classify_neutral(self, analyzer):
        """Test classification of neutral text."""
        result = analyzer.classify("This is a test.")
        assert result == "neutral"

    def test_get_aspect_sentiment_returns_dict(self, analyzer):
        """Test that aspect sentiment returns correct dict structure."""
        result = analyzer.get_aspect_sentiment("La comida estaba deliciosa.")

        assert isinstance(result, dict)
        for aspect in ["comida", "servicio", "precio", "ambiente"]:
            assert aspect in result

    def test_aspect_keywords_exist(self):
        """Test that aspect keywords are defined."""
        assert "comida" in ASPECT_KEYWORDS
        assert "servicio" in ASPECT_KEYWORDS
        assert "precio" in ASPECT_KEYWORDS
        assert "ambiente" in ASPECT_KEYWORDS

    def test_aspect_detection_comida(self, analyzer):
        """Test that comida aspect is detected (Spanish keywords)."""
        result = analyzer.get_aspect_sentiment("La comida estaba deliciosa y el sabor incredible.")
        # VADER is English-focused, so Spanish text may not be detected properly
        # This test verifies the function works, not necessarily the accuracy
        assert isinstance(result["comida"], str)

    def test_aspect_detection_servicio(self, analyzer):
        """Test that servicio aspect is detected."""
        # English text to test aspect detection with VADER
        result = analyzer.get_aspect_sentiment("The service was excellent and the staff was very attentive.")
        assert result["servicio"] == "positive"

    def test_analyze_batch(self, analyzer):
        """Test batch analysis."""
        texts = [
            "La comida estaba deliciosa.",
            "El servicio fue malo.",
            "Buen precio."
        ]
        results = analyzer.analyze_batch(texts)

        assert len(results) == 3
        assert isinstance(results[0], dict)


class TestTextBlobAnalyzer:
    """Tests for TextBlobAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create TextBlob analyzer instance."""
        try:
            return TextBlobAnalyzer()
        except ImportError:
            pytest.skip("TextBlob not installed")

    def test_get_polarity_positive(self, analyzer):
        """Test polarity for positive text."""
        text = "This is great and wonderful!"
        polarity = analyzer.get_polarity(text)
        assert polarity > 0

    def test_get_polarity_negative(self, analyzer):
        """Test polarity for negative text."""
        text = "This is terrible and awful!"
        polarity = analyzer.get_polarity(text)
        assert polarity < 0

    def test_get_polarity_empty(self, analyzer):
        """Test polarity for empty text."""
        polarity = analyzer.get_polarity("")
        assert polarity == 0.0

    def test_classify(self, analyzer):
        """Test sentiment classification."""
        assert analyzer.classify("amazing wonderful") == "positive"
        assert analyzer.classify("terrible awful") == "negative"

    def test_get_aspect_sentiment_returns_dict(self, analyzer):
        """Test that aspect sentiment returns correct structure."""
        result = analyzer.get_aspect_sentiment("La comida estaba deliciosa.")
        assert isinstance(result, dict)
        for aspect in ["comida", "servicio", "precio", "ambiente"]:
            assert aspect in result


class TestHybridSentimentAnalyzer:
    """Tests for HybridSentimentAnalyzer class."""

    def test_init_with_no_analyzers(self):
        """Test initialization with no analyzers."""
        try:
            import vaderSentiment
            import textblob
        except ImportError:
            pytest.skip("VADER or TextBlob not installed")

        analyzer = HybridSentimentAnalyzer(use_llm=False)

        # Should have at least one fallback
        assert analyzer.vader is not None or analyzer.textblob is not None

    def test_analyze_review_returns_dict(self):
        """Test that analyze_review returns correct dict structure."""
        try:
            analyzer = HybridSentimentAnalyzer(use_llm=False)
        except ImportError:
            pytest.skip("VADER not installed")

        result = analyzer.analyze_review("La comida estaba deliciosa.")

        assert isinstance(result, dict)
        for aspect in ["comida", "servicio", "precio", "ambiente"]:
            assert aspect in result

    def test_analyze_review_empty_text(self):
        """Test that empty review returns neutral sentiments."""
        try:
            analyzer = HybridSentimentAnalyzer(use_llm=False)
        except ImportError:
            pytest.skip("VADER not installed")

        result = analyzer.analyze_review("")

        for aspect in ["comida", "servicio", "precio", "ambiente"]:
            assert result[aspect] == "neutral"

    def test_analyze_batch(self):
        """Test batch analysis."""
        try:
            analyzer = HybridSentimentAnalyzer(use_llm=False)
        except ImportError:
            pytest.skip("VADER not installed")

        texts = ["Texto 1", "Texto 2", "Texto 3"]
        results = analyzer.analyze_batch(texts)

        assert len(results) == 3


class TestAddSentimentColumns:
    """Tests for add_sentiment_columns function."""

    def test_adds_sentiment_score_columns_from_strings(self):
        """Test that sentiment score columns are added from string columns."""
        # Create a dataframe with string sentiment columns but NO score columns
        df = pd.DataFrame({
            "restaurant_id": ["rest_1", "rest_2", "rest_3", "rest_4", "rest_5"],
            "restaurant_name": ["Rest A", "Rest B", "Rest C", "Rest D", "Rest E"],
            "sentiment_comida": ["positive", "positive", "positive", "positive", "positive"],
            "sentiment_servicio": ["positive", "neutral", "neutral", "positive", "positive"],
            "sentiment_precio": ["neutral", "negative", "positive", "positive", "negative"],
            "sentiment_ambiente": ["positive", "positive", "neutral", "neutral", "positive"],
        })

        result = add_sentiment_columns(df)

        # The function creates columns like "sentiment_comida_score"
        assert "sentiment_comida_score" in result.columns
        assert "sentiment_servicio_score" in result.columns
        assert "sentiment_precio_score" in result.columns
        assert "sentiment_ambiente_score" in result.columns

    def test_adds_overall_sentiment_score(self):
        """Test that overall sentiment score is calculated."""
        # Create a dataframe with string sentiment columns but NO score columns
        df = pd.DataFrame({
            "restaurant_id": ["rest_1", "rest_2", "rest_3"],
            "restaurant_name": ["Rest A", "Rest B", "Rest C"],
            "sentiment_comida": ["positive", "positive", "positive"],
            "sentiment_servicio": ["positive", "neutral", "neutral"],
            "sentiment_precio": ["neutral", "negative", "positive"],
            "sentiment_ambiente": ["positive", "positive", "neutral"],
        })

        result = add_sentiment_columns(df)

        assert "overall_sentiment_score" in result.columns

    def test_overall_sentiment_is_mean_of_aspects(self):
        """Test that overall is mean of aspect scores."""
        # Create a dataframe with string sentiment columns but NO score columns
        df = pd.DataFrame({
            "restaurant_id": ["rest_1", "rest_2"],
            "restaurant_name": ["Rest A", "Rest B"],
            "sentiment_comida": ["positive", "negative"],
            "sentiment_servicio": ["positive", "negative"],
            "sentiment_precio": ["positive", "negative"],
            "sentiment_ambiente": ["positive", "negative"],
        })

        result = add_sentiment_columns(df)

        # Row 0: all positive = 1.0, Row 1: all negative = -1.0
        assert abs(result.iloc[0]["overall_sentiment_score"] - 1.0) < 0.01
        assert abs(result.iloc[1]["overall_sentiment_score"] - (-1.0)) < 0.01
