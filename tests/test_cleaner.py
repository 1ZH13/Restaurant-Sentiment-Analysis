"""
Unit tests for src/preprocessing/cleaner.py module.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.preprocessing.cleaner import (
    remove_duplicates,
    clean_text,
    clean_dataframe,
    validate_schema
)


class TestCleanText:
    """Tests for clean_text function."""

    def test_clean_text_removes_urls(self):
        """Test that URLs are removed from text."""
        text = "Visit us at http://example.com or www.test.com"
        result = clean_text(text)
        assert "http://" not in result
        assert "www." not in result

    def test_clean_text_removes_html_tags(self):
        """Test that HTML tags are removed."""
        text = "<b>Bold text</b> and <i>italic</i>"
        result = clean_text(text)
        assert "<" not in result
        assert ">" not in result
        assert "Bold text" in result

    def test_clean_text_handles_none(self):
        """Test that None input returns empty string."""
        result = clean_text(None)
        assert result == ""

    def test_clean_text_handles_nan(self):
        """Test that NaN input returns empty string."""
        import numpy as np
        result = clean_text(np.nan)
        assert result == ""

    def test_clean_text_preserves_accents(self):
        """Test that accented characters are preserved."""
        text = "café Niño Señor"
        result = clean_text(text)
        assert "café" in result
        assert "Niño" in result
        assert "Señor" in result

    def test_clean_text_removes_extra_whitespace(self):
        """Test that extra whitespace is normalized."""
        text = "Multiple    spaces   here"
        result = clean_text(text)
        assert "  " not in result

    def test_clean_text_preserves_basic_punctuation(self):
        """Test that basic punctuation is preserved."""
        text = "Hello! How are you? I'm fine."
        result = clean_text(text)
        assert "!" in result
        assert "?" in result
        assert "." in result


class TestRemoveDuplicates:
    """Tests for remove_duplicates function."""

    def test_remove_duplicates_basic(self, raw_reviews_df):
        """Test basic duplicate removal."""
        # Add a duplicate row
        df = pd.concat([raw_reviews_df, raw_reviews_df.iloc[[0]]], ignore_index=True)
        assert len(df) == 4

        result = remove_duplicates(df)
        assert len(result) == 3

    def test_remove_duplicates_no_changes(self, sample_reviews_df):
        """Test that no duplicates returns same length."""
        result = remove_duplicates(sample_reviews_df)
        assert len(result) == len(sample_reviews_df)

    def test_remove_duplicates_custom_subset(self, raw_reviews_df):
        """Test duplicate removal with custom subset."""
        df = pd.concat([raw_reviews_df, raw_reviews_df.iloc[[0]]], ignore_index=True)
        result = remove_duplicates(df, subset=["restaurant_id"])
        assert len(result) == 2  # Only 2 unique restaurant_ids


class TestCleanDataframe:
    """Tests for clean_dataframe function."""

    def test_clean_dataframe_removes_missing_essential(self, raw_reviews_df):
        """Test that rows with missing essential fields are removed."""
        # Add row with missing restaurant_id
        df = raw_reviews_df.copy()
        df.loc[len(df)] = {
            "restaurant_id": None,
            "restaurant_name": "Test",
            "category": "Test",
            "price_range": "$",
            "overall_rating": 4.0,
            "review_text": "Test review",
            "source": "test"
        }

        result = clean_dataframe(df)
        assert len(result) == len(raw_reviews_df)

    def test_clean_dataframe_cleans_text_fields(self, raw_reviews_df):
        """Test that text fields are cleaned."""
        result = clean_dataframe(raw_reviews_df)

        # Check that HTML is removed
        assert "<b>" not in result["review_text"].values[0]
        assert "http://" not in result["review_text"].values[0]

    def test_clean_dataframe_converts_ratings_to_numeric(self, raw_reviews_df):
        """Test that rating columns are converted to numeric."""
        result = clean_dataframe(raw_reviews_df)
        assert pd.api.types.is_numeric_dtype(result["overall_rating"])

    def test_clean_dataframe_converts_dates(self, raw_reviews_df):
        """Test that review_date is converted to datetime."""
        result = clean_dataframe(raw_reviews_df)
        assert pd.api.types.is_datetime64_any_dtype(result["review_date"])


class TestValidateSchema:
    """Tests for validate_schema function."""

    def test_validate_schema_valid(self, sample_reviews_df):
        """Test schema validation with valid data."""
        assert validate_schema(sample_reviews_df) is True

    def test_validate_schema_missing_columns(self, raw_reviews_df):
        """Test schema validation with missing columns."""
        # Drop a required column
        df = raw_reviews_df.drop(columns=["source"])
        assert validate_schema(df) is False

    def test_validate_schema_prints_missing(self, capsys, sample_reviews_df):
        """Test that missing columns are printed."""
        df = sample_reviews_df.drop(columns=["source"])
        validate_schema(df)
        captured = capsys.readouterr()
        assert "Missing required columns" in captured.out
