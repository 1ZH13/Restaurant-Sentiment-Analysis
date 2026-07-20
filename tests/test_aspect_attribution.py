"""
Tests for aspect-level sentiment attribution.

Two behaviours are pinned here:

1. Sentiment words are attributed to the aspect they are actually about. Scoring
   whole sentences meant "la comida estuvo excelente pero el servicio fue lento"
   gave both aspects the same blended score, marking the food negative.
2. An aspect the review never mentioned is reported as not mentioned, rather
   than as a neutral opinion. Treating silence as neutral left price neutral in
   ~87% of rows and flattened every chart.
"""

import pandas as pd
import pytest

from src.sentiment.aspect_scores import derive_aspect_sentiment_scores, parse_aspect_mentions
from src.sentiment.fallback_classifier import SpanishLexiconAnalyzer


@pytest.fixture(scope="module")
def analyzer():
    return SpanishLexiconAnalyzer()


class TestAspectAttribution:
    def test_mixed_sentence_splits_polarity(self, analyzer):
        result = analyzer.get_aspect_sentiment(
            "La comida estuvo excelente pero el servicio fue muy lento."
        )
        assert result["comida"] == "positive"
        assert result["servicio"] == "negative"

    def test_reverse_order_still_attributes_correctly(self, analyzer):
        result = analyzer.get_aspect_sentiment(
            "El servicio fue impecable aunque la comida estuvo insipida."
        )
        assert result["servicio"] == "positive"
        assert result["comida"] == "negative"

    @pytest.mark.parametrize("text,aspect,expected", [
        ("Los meseros fueron super atentos y amables.", "servicio", "positive"),
        ("Nos tardaron 40 minutos y olvidaron el pedido.", "servicio", "negative"),
        ("El ambiente es acogedor y la musica agradable.", "ambiente", "positive"),
        ("El local estaba sucio y muy ruidoso.", "ambiente", "negative"),
        ("Buena relacion calidad precio, muy accesible.", "precio", "positive"),
        ("Precios elevados para lo que ofrecen, carisimo.", "precio", "negative"),
    ])
    def test_single_aspect_sentences(self, analyzer, text, aspect, expected):
        assert analyzer.get_aspect_sentiment(text)[aspect] == expected

    def test_negation_flips_polarity(self, analyzer):
        assert analyzer.get_aspect_sentiment("La comida no estuvo buena.")["comida"] == "negative"


class TestMentionTracking:
    def test_unmentioned_aspect_is_flagged(self, analyzer):
        details = analyzer.get_aspect_details("Los meseros fueron muy amables.")
        assert details["servicio"]["mentioned"] is True
        assert details["precio"]["mentioned"] is False

    def test_mentioned_aspect_is_flagged(self, analyzer):
        details = analyzer.get_aspect_details("Los precios son muy accesibles.")
        assert details["precio"]["mentioned"] is True

    def test_food_fallback_is_not_reported_as_explicit(self, analyzer):
        """Food is inferred from the overall tone, which is not a real mention."""
        details = analyzer.get_aspect_details("Todo estuvo excelente, volveremos.")
        assert details["comida"]["mentioned"] is False

    def test_empty_text_mentions_nothing(self, analyzer):
        details = analyzer.get_aspect_details("")
        assert all(not d["mentioned"] for d in details.values())

    def test_empty_text_still_labels_neutral(self, analyzer):
        assert all(v == "neutral" for v in analyzer.get_aspect_sentiment("").values())


class TestDerivedColumns:
    def test_mention_columns_are_derived(self):
        df = pd.DataFrame({
            "aspect_sentiments": ["{'comida': 'positive', 'servicio': 'neutral', "
                                  "'precio': 'neutral', 'ambiente': 'neutral'}"],
            "aspect_mentions": ["{'comida': True, 'servicio': False, "
                                "'precio': False, 'ambiente': True}"],
        })
        result = derive_aspect_sentiment_scores(df)

        assert result["mentions_comida"].iloc[0] is True or result["mentions_comida"].iloc[0]
        assert not result["mentions_precio"].iloc[0]
        assert result["sentiment_comida_score"].iloc[0] == 1.0

    def test_missing_mentions_column_defaults_to_true(self):
        """Older datasets have no mention data and must keep working."""
        df = pd.DataFrame({
            "aspect_sentiments": ["{'comida': 'positive', 'servicio': 'neutral', "
                                  "'precio': 'neutral', 'ambiente': 'neutral'}"],
        })
        result = derive_aspect_sentiment_scores(df)
        assert result["mentions_precio"].all()

    def test_parse_aspect_mentions_handles_garbage(self):
        assert parse_aspect_mentions("no soy un dict") == {
            "comida": True, "servicio": True, "precio": True, "ambiente": True
        }
