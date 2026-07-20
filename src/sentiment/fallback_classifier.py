"""
Fallback sentiment classifiers using VADER and TextBlob.
These are used when LLM is not available or as a comparison baseline.
"""

import re
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


# Aspect vocabularies. These were originally very small, which meant most
# reviews never triggered the precio/servicio/ambiente aspects at all and the
# dataset came out ~87% neutral for them. The lists below cover the words that
# actually show up in Panamanian restaurant reviews, in Spanish and English.
ASPECT_KEYWORDS = {
    "comida": [
        "comida", "comidas", "food", "plato", "platos", "platillo", "platillos",
        "dish", "dishes", "sabor", "sabores", "sabroso", "menu", "menú", "cocina",
        "chef", "carne", "carnes", "pescado", "mariscos", "camarones", "pollo",
        "ensalada", "sopa", "postre", "postres", "pasta", "pizza", "sushi",
        "hamburguesa", "arroz", "pan", "queso", "salsa", "entrada", "entradas",
        "porcion", "porción", "porciones", "ingredientes", "fresco", "frescos",
        "cocinado", "cocida", "punto", "sazon", "sazón", "desayuno", "almuerzo",
        "cena", "bebida", "bebidas", "cafe", "café", "coctel", "cóctel", "trago",
        "vino", "cerveza", "delicioso", "deliciosa", "rico", "rica",
        "taste", "flavor", "meal", "dessert", "starter", "portion", "cooked",
    ],
    "servicio": [
        "servicio", "service", "atencion", "atención", "atendieron", "atendio",
        "atendió", "atendida", "atendido", "mesero", "meseros", "mesera", "meseras",
        "camarero", "camarera", "mozo", "personal", "empleado", "empleados",
        "staff", "waiter", "waitress", "trato", "amabilidad", "amable", "amables",
        "espera", "esperamos", "esperar", "demora", "demoro", "demoró", "tardaron",
        "rapidez", "atento", "atenta", "atentos", "anfitrion", "anfitrión",
        "reserva", "reservacion", "reservación", "pedido", "orden", "cortesia",
        "cortesía", "profesional", "hostess", "bartender",
    ],
    "precio": [
        "precio", "precios", "price", "prices", "pricing", "cost", "costo",
        "caro", "cara", "caros", "caras", "expensive", "barato", "barata",
        "baratos", "cheap", "economico", "económico", "economica", "económica",
        "vale", "valen", "worth", "dinero", "money", "bill", "cuenta", "pagar",
        "pague", "pagamos", "cobran", "cobro", "cobraron", "tarifa", "factura",
        "relacion calidad", "relación calidad", "calidad precio", "value",
        "accesible", "asequible", "presupuesto", "afordable", "affordable",
        "promocion", "promoción", "descuento", "oferta", "costoso", "costosa",
        "dolares", "dólares", "balboas",
    ],
    "ambiente": [
        "ambiente", "ambiance", "ambience", "atmosfera", "atmósfera", "atmosphere",
        "decoracion", "decoración", "decoration", "decor", "lugar", "place",
        "espacio", "vista", "vistas", "view", "musica", "música", "music",
        "ruido", "ruidoso", "noise", "noisy", "acogedor", "acogedora", "cozy",
        "iluminacion", "iluminación", "luz", "terraza", "rooftop", "jardin",
        "jardín", "mesa", "mesas", "silla", "sillas", "local", "instalaciones",
        "bano", "baño", "banos", "baños", "limpieza", "limpio", "limpia",
        "sucio", "sucia", "aire acondicionado", "climatizado", "romantico",
        "romántico", "familiar", "tranquilo", "tranquila", "concurrido", "lleno",
        "decorado", "moderno", "moderna", "elegante", "rustico", "rústico",
    ],
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


POSITIVE_LEXICON = {
    # Spanish
    "excelente", "excelentes", "delicioso", "deliciosa", "deliciosos", "deliciosas",
    "rico", "rica", "ricos", "ricas", "riquisimo", "riquísimo", "buenisimo", "buenísimo",
    "bueno", "buena", "buenos", "buenas", "increible", "increíble", "espectacular",
    "espectaculares", "recomendado", "recomendada", "recomiendo", "recomendable",
    "amable", "amables", "atento", "atenta", "atentos", "atentas", "perfecto", "perfecta",
    "encanto", "encantó", "encanta", "maravilloso", "maravillosa", "fresco", "fresca",
    "sabroso", "sabrosa", "agradable", "rapido", "rápido", "rapida", "rápida", "generoso",
    "generosa", "bonito", "bonita", "lindo", "linda", "divino", "divina", "super", "súper",
    "genial", "fabuloso", "exquisito", "exquisita", "mejor", "mejores", "favorito",
    "favorita", "calidad", "gusto", "gusta", "gustó", "encantador", "encantadora",
    "wow", "top", "supero", "superó",
    # Spanish - service, atmosphere and value vocabulary
    "acogedor", "acogedora", "atenta", "cordial", "cordiales", "profesional",
    "eficiente", "eficientes", "puntual", "limpio", "limpia", "impecable",
    "tranquilo", "tranquila", "comodo", "cómodo", "comoda", "cómoda", "elegante",
    "moderno", "moderna", "romantico", "romántico", "espectacular", "hermoso",
    "hermosa", "abundante", "abundantes", "generosas", "jugoso", "jugosa",
    "crujiente", "tierno", "tierna", "autentico", "auténtico", "casero", "casera",
    "economico", "económico", "economica", "económica", "accesible", "asequible",
    "justo", "justa", "razonable", "razonables", "conveniente", "volveria",
    "volvería", "volveremos", "repetire", "repetiré", "vale", "valio", "valió",
    "buenisima", "buenísima", "sorprendio", "sorprendió", "sorprendente",
    # English
    "excellent", "delicious", "great", "amazing", "good", "best", "friendly", "wonderful",
    "perfect", "awesome", "tasty", "nice", "fantastic", "love", "loved", "recommend",
    "recommended", "fresh", "gorgeous", "polite", "balanced", "cozy", "attentive",
    "affordable", "reasonable", "clean", "beautiful", "outstanding", "superb",
    "flavorful", "generous", "welcoming", "charming", "solid", "worth",
}

NEGATIVE_LEXICON = {
    # Spanish
    "malo", "mala", "malos", "malas", "pesimo", "pésimo", "malisimo", "malísimo", "terrible",
    "feo", "fea", "lento", "lenta", "lentos", "frio", "frío", "fria", "fría", "caro", "cara",
    "caros", "caras", "demora", "demoro", "demoró", "tardo", "tardó", "sucio", "sucia",
    "grosero", "grosera", "descortes", "descortés", "decepcion", "decepción", "decepcionado",
    "decepcionada", "decepcionante", "horrible", "mediocre", "desabrido", "salado", "quemado",
    "incomodo", "incómodo", "incomoda", "incómoda", "ruidoso", "ruidosa",
    "falta", "faltan", "falto", "faltó", "peor", "peores",
    "regular", "asco", "defraudo", "defraudó", "defrauda", "fome",
    # Spanish - service, atmosphere and value complaints
    "elevado", "elevada", "elevados", "elevadas", "exagerado", "exagerada",
    "carisimo", "carísimo", "carisima", "carísima", "sobrevalorado", "sobrevalorada",
    "costoso", "costosa", "abusivo", "abusiva", "escaso", "escasa", "escasas",
    "pequena", "pequeña", "insuficiente", "tibio", "tibia", "seco", "seca",
    "duro", "dura", "insipido", "insípido", "insipida", "insípida", "aguado",
    "aguada", "grasoso", "grasosa", "quemada", "crudo", "cruda", "descuidado",
    "descuidada", "desatento", "desatenta", "antipatico", "antipático",
    "antipatica", "antipática", "tardaron", "olvidaron", "olvido",
    "olvidó", "error", "errores", "equivocaron", "reclamo", "queja",
    "evitar", "eviten", "lamentable", "penoso", "penosa", "desagradable",
    "estrecho", "estrecha", "apretado", "apretada", "desorganizado",
    # English
    "bad", "terrible", "awful", "slow", "cold", "expensive", "overpriced", "disappointing",
    "disappointed", "worst", "rude", "dirty", "bland", "horrible", "mediocre",
    "tasteless", "soggy", "burnt", "undercooked", "cramped", "noisy", "unfriendly",
    "pricey", "avoid", "waited", "forgot", "wrong",
}

# Words that amplify the polarity of a nearby sentiment word.
INTENSIFIERS = {"muy", "super", "súper", "bastante", "tan", "demasiado", "sumamente",
                "realmente", "totalmente", "completamente", "extremadamente",
                "very", "really", "extremely", "so", "absolutely", "incredibly"}

NEGATORS = {"no", "nunca", "sin", "tampoco", "ni", "jamas", "jamás", "nada"}

_TOKEN_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)

# How many tokens around an aspect mention are attributed to that aspect.
# Spanish puts the adjective after the noun ("comida deliciosa"), so the window
# reaches further forward than back.
WINDOW_BEFORE = 3
WINDOW_AFTER = 6


class SpanishLexiconAnalyzer:
    """Aspect sentiment via a Spanish/English lexicon with negation handling.

    Designed for Spanish reviews (where English-only tools like VADER score most
    text as neutral). For each aspect it scores the sentences mentioning that
    aspect; for ``comida`` it falls back to the whole review since food is the
    central topic of a restaurant review. VADER is mixed in for English text.
    """

    def __init__(self):
        self.vader = VADERSentimentAnalyzer() if VADER_AVAILABLE else None

    def _lexicon_score(self, text: str) -> float:
        """Score text by summing lexicon hits, honouring negation and intensity."""
        tokens = _TOKEN_RE.findall(text.lower())
        score = 0.0
        for i, tok in enumerate(tokens):
            polarity = 1.0 if tok in POSITIVE_LEXICON else (-1.0 if tok in NEGATIVE_LEXICON else 0.0)
            if polarity == 0.0:
                continue

            window = tokens[max(0, i - 3):i]
            if any(n in window for n in NEGATORS):
                polarity = -polarity
            # "muy bueno" counts for more than "bueno".
            if any(n in window[-2:] for n in INTENSIFIERS):
                polarity *= 1.5

            score += polarity
        return score

    def _classify_text(self, text: str) -> str:
        score = self._lexicon_score(text)
        if self.vader is not None:
            compound = self.vader.get_compound_score(text)
            if compound >= 0.4:
                score += 1
            elif compound <= -0.4:
                score -= 1
        if score > 0:
            return "positive"
        if score < 0:
            return "negative"
        return "neutral"

    def _token_polarity(self, tokens: List[str], index: int) -> float:
        """Polarity of one token, adjusted for negation and intensifiers."""
        token = tokens[index]
        polarity = 1.0 if token in POSITIVE_LEXICON else (-1.0 if token in NEGATIVE_LEXICON else 0.0)
        if polarity == 0.0:
            return 0.0

        window = tokens[max(0, index - 3):index]
        if any(n in window for n in NEGATORS):
            polarity = -polarity
        if any(n in window[-2:] for n in INTENSIFIERS):
            polarity *= 1.5
        return polarity

    def _nearest_aspect(self, index: int, aspect_positions: Dict[int, str]) -> Optional[str]:
        """Attribute a sentiment word to the closest aspect mention.

        Fixed windows around each aspect overlap: in "el servicio fue impecable
        aunque la comida estuvo insipida", "impecable" falls inside comida's
        window too and cancels its negative. Assigning each word to exactly one
        aspect - the nearest - keeps the two opinions apart.

        Spanish places the adjective after the noun ("comida deliciosa"), so a
        word that follows a mention is treated as slightly closer than one at
        the same distance before it.
        """
        best_aspect, best_distance = None, float("inf")

        for position, aspect in aspect_positions.items():
            if position == index:
                continue
            offset = index - position
            if 0 < offset <= WINDOW_AFTER:
                distance = float(offset)
            elif -WINDOW_BEFORE <= offset < 0:
                distance = -offset + 0.5
            else:
                continue

            if distance < best_distance:
                best_aspect, best_distance = aspect, distance

        return best_aspect

    def _label_from_score(self, score: float) -> str:
        if score > 0:
            return "positive"
        if score < 0:
            return "negative"
        return "neutral"

    def get_aspect_details(self, text: str) -> Dict[str, Dict]:
        """Classify each aspect and report whether the review actually discussed it.

        Distinguishing "not mentioned" from "mentioned but neutral" matters: a
        review that never talks about price is not evidence that the price is
        average. Callers that average these scores should use ``mentioned`` to
        avoid diluting the result with silence.
        """
        details = {
            aspect: {"label": "neutral", "mentioned": False}
            for aspect in ASPECT_KEYWORDS
        }
        if not text or pd.isna(text):
            return details

        text = str(text)
        lowered = text.lower()
        tokens = _TOKEN_RE.findall(lowered)

        # Map every aspect mention's token position to its aspect.
        aspect_positions: Dict[int, str] = {}
        mentioned_aspects = set()

        for aspect, keywords in ASPECT_KEYWORDS.items():
            single = {k for k in keywords if " " not in k}
            phrases = [k for k in keywords if " " in k]

            positions = [i for i, tok in enumerate(tokens) if tok in single]
            # Multi-word cues ("relacion calidad") are anchored on their first token.
            for phrase in phrases:
                if phrase in lowered:
                    head = phrase.split()[0]
                    positions.extend(i for i, tok in enumerate(tokens) if tok == head)

            if positions:
                mentioned_aspects.add(aspect)
                for position in positions:
                    aspect_positions.setdefault(position, aspect)

        # Each sentiment word contributes to exactly one aspect: the nearest.
        scores = {aspect: 0.0 for aspect in ASPECT_KEYWORDS}
        for index in range(len(tokens)):
            polarity = self._token_polarity(tokens, index)
            if polarity == 0.0:
                continue
            target = self._nearest_aspect(index, aspect_positions)
            if target is not None:
                scores[target] += polarity

        for aspect in ASPECT_KEYWORDS:
            if aspect in mentioned_aspects:
                details[aspect] = {
                    "label": self._label_from_score(scores[aspect]),
                    "mentioned": True,
                }
            elif aspect == "comida":
                # Food is the central topic of a restaurant review: when it is not
                # named explicitly, fall back to the overall tone. This is an
                # inference, so it is not reported as an explicit mention.
                details[aspect] = {
                    "label": self._classify_text(text),
                    "mentioned": False,
                }

        return details

    def get_aspect_sentiment(self, text: str) -> Dict[str, str]:
        """Classify each aspect as positive / neutral / negative."""
        return {aspect: d["label"] for aspect, d in self.get_aspect_details(text).items()}

    def analyze_review(self, text: str) -> Dict[str, str]:
        return self.get_aspect_sentiment(text)

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, str]]:
        return [self.get_aspect_sentiment(t) for t in texts]


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
    score_cols = [f"sentiment_{aspect}_score" for aspect in aspects]
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
