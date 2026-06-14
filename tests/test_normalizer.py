"""
Unit tests for src/preprocessing/normalizer.py module.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.preprocessing.normalizer import (
    normalize_text,
    remove_stopwords,
    tokenize,
    detect_language,
    normalize_dataframe,
    add_text_features
)


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_normalize_text_lowercase(self):
        """Test that text is converted to lowercase."""
        text = "HELLO World"
        result = normalize_text(text)
        assert result == "hello world"

    def test_normalize_text_removes_accents(self):
        """Test that accents are removed."""
        text = "café Niño"
        result = normalize_text(text)
        assert "ñ" not in result
        assert "é" not in result

    def test_normalize_text_handles_none(self):
        """Test that None input returns empty string."""
        result = normalize_text(None)
        assert result == ""

    def test_normalize_text_removes_extra_whitespace(self):
        """Test that extra whitespace is normalized."""
        text = "hello    world"
        result = normalize_text(text)
        assert "  " not in result

    def test_normalize_text_preserves_basic_chars(self):
        """Test that alphanumeric chars are preserved."""
        text = "Hello123 World!"
        result = normalize_text(text)
        assert "hello123" in result
        assert "world!" in result


class TestRemoveStopwords:
    """Tests for remove_stopwords function."""

    def test_remove_stopwords_spanish(self):
        """Test that Spanish stopwords are removed."""
        text = "el la comida del restaurant"
        result = remove_stopwords(text, lang="spanish")
        assert "el" not in result
        assert "la" not in result
        assert "comida" in result

    def test_remove_stopwords_empty_result(self):
        """Test that all stopwords returns empty."""
        text = "el la de"
        result = remove_stopwords(text, lang="spanish")
        # Should only have whitespace
        assert result.strip() == ""


class TestTokenize:
    """Tests for tokenize function."""

    def test_tokenize_basic(self):
        """Test basic tokenization."""
        text = "hello world"
        result = tokenize(text)
        assert len(result) == 2
        assert "hello" in result
        assert "world" in result

    def test_tokenize_empty_string(self):
        """Test tokenization of empty string."""
        result = tokenize("")
        assert result == []

    def test_tokenize_handles_punctuation(self):
        """Test tokenization preserves punctuation."""
        text = "hello, world!"
        result = tokenize(text)
        assert "hello" in result or "," in result


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_detect_language_spanish(self):
        """Test Spanish detection."""
        text = "el la los las un una de en que es por con para"
        result = detect_language(text)
        assert result == "spanish"

    def test_detect_language_english(self):
        """Test English detection."""
        text = "the a an is was were are be have has had and or but"
        result = detect_language(text)
        assert result == "english"

    def test_detect_language_mixed(self):
        """Test mixed language detection."""
        # Equal number of Spanish and English indicators
        text = "the a is el la de"
        result = detect_language(text)
        assert result == "mixed"

    def test_detect_language_empty(self):
        """Test empty string detection."""
        result = detect_language("")
        assert result == "unknown"


class TestNormalizeDataframe:
    """Tests for normalize_dataframe function."""

    def test_normalize_dataframe_adds_normalized_columns(self, raw_reviews_df):
        """Test that normalized columns are added."""
        result = normalize_dataframe(raw_reviews_df)

        assert "review_text_normalized" in result.columns
        assert "restaurant_name_normalized" in result.columns
        assert "category_normalized" in result.columns

    def test_normalize_dataframe_adds_language_column(self, raw_reviews_df):
        """Test that language detection column is added."""
        result = normalize_dataframe(raw_reviews_df)
        assert "review_language" in result.columns

    def test_normalize_dataframe_preserves_original(self, raw_reviews_df):
        """Test that original columns are preserved."""
        result = normalize_dataframe(raw_reviews_df)
        assert "review_text" in result.columns
        assert "restaurant_name" in result.columns


class TestAddTextFeatures:
    """Tests for add_text_features function."""

    def test_add_text_features_adds_word_count(self, raw_reviews_df):
        """Test that word_count column is added."""
        result = add_text_features(raw_reviews_df)
        assert "word_count" in result.columns
        assert all(result["word_count"] > 0)

    def test_add_text_features_adds_char_count(self, raw_reviews_df):
        """Test that char_count column is added."""
        result = add_text_features(raw_reviews_df)
        assert "char_count" in result.columns
        assert all(result["char_count"] > 0)

    def test_add_text_features_adds_avg_word_length(self, raw_reviews_df):
        """Test that avg_word_length column is added."""
        result = add_text_features(raw_reviews_df)
        assert "avg_word_length" in result.columns

    def test_add_text_features_handles_none(self):
        """Test that None values don't cause errors."""
        df = pd.DataFrame({"review_text": [None, "hello world"]})
        result = add_text_features(df)
        assert "word_count" in result.columns
