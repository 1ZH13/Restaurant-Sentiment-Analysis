# PRD - Plataforma de Análisis de Reseñas de Restaurantes en Panamá

> **Documento historico.** Es la planificacion original del proyecto, anterior a
> la implementacion. Se conserva como registro de lo que se propuso, pero **no
> describe el estado actual**: partes de lo aqui planteado se resolvieron de otra
> forma. Para la documentacion vigente ver [README.md](README.md) y la carpeta
> [docs/](docs/).



**Grupo:** 5
**Proyecto:** Restaurant Sentiment Analysis Platform
**Fecha:** 14 de Junio de 2026
**Versión:** 1.0

---

## 1. Resumen Ejecutivo

Plataforma de análisis inteligente de reseñas de restaurantes en Panamá que recopila, procesa y analiza opiniones de clientes mediante técnicas de ciencia de datos, aprendizaje automático e inteligencia artificial. El sistema permite comparar restaurantes, identificar aspectos evaluados (comida, servicio, precio, ambiente), agruparlos por características similares y generar recomendaciones automatizadas.

**Alcance Académico (Segundo Parcial - Semanas 9-11):**
- Pipeline ETL funcional con 2+ fuentes de datos
- Análisis de sentimiento por aspecto utilizando LLM
- Clustering de restaurantes
- Dashboard interactivo con Streamlit
- Documentación técnica completa

---

## 2. Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|-------------|----------------|
| Lenguaje | Python 3.10+ | Requisito del curso |
| Manipulación de datos | Pandas, NumPy | Estándar en ciencia de datos |
| ML/Analytics | Scikit-Learn | Clustering, preprocesamiento |
| IA/LLM | OpenAI API / Ollama | Análisis de sentimiento por aspecto |
| Web Scraping | BeautifulSoup, Requests | Extracción de Degusta Panamá |
| Visualización | Plotly, Streamlit | Dashboard interactivo |
| Control de versiones | GitHub | Requisito del curso |

---

## 3. Fuentes de Datos

### 3.1 Fuente Primaria: Degusta Panamá

**URL:** https://www.degustapanama.com/

**Método de extracción:** Web Scraping con BeautifulSoup/Requests

**Datos disponibles por restaurante:**
- Nombre del restaurante
- Categoría/Tipo de cocina (ej. "Tailandesa", "Asiática")
- Precio promedio por persona
- Ubicación/Dirección
- Barrio (ej. "San Francisco", "Casco Antiguo")
- Servicios disponibles (estacionamiento, wifi, etc.)
- Rating general (escala 1-5)
- Total de reseñas
- Ratings por aspecto: Comida, Servicio, Ambiente
- Reseñas individuales con:
  - Nombre del usuario
  - Fecha de la reseña
  - Texto del comentario
  - Votos de "Me gusta"

**Estructura de URLs:**
- Lista: `https://www.degustapanama.com/panama/search`
- Restaurante: `https://www.degustapanama.com/panama/restaurante/{nombre}_{id}.html`
- Reseñas paginadas: `https://www.degustapanama.com/panama/restaurante/{nombre}_{id}_fecha_{pag}_todos.html`

**Volumen estimado:** 500+ restaurantes con reseñas

---

### 3.2 Fuente Secundaria: Tripadvisor Panama

**URL:** https://www.tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html

**Geo ID:** g294480 (Panama City, Panama Province)

**Método de extracción:** Web Scraping con BeautifulSoup/Requests

**Datos disponibles por restaurante:**
- Nombre del restaurante
- Rating general (escala 1-5 bubbles)
- Total de reseñas
- Categoría/Tipo de cocina (ej. "Steakhouse", "Italian", "Caribbean")
- Rango de precio ($, $$-$$$, $$$-$$$$)
- Fragmentos destacados de reseñas
- Badges (Travelers' Choice, Best of the Best)
- Estado (Open now, Closed now)
- Link a menú
- Fotos

**Estructura de URLs:**
- Lista principal: `https://www.tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html`
- Detalle restaurante: `https://www.tripadvisor.com/Restaurant_Review-g294480-d{restaurant_id}-Reviews-{name}-Panama_City_Panama_Province.html`
- Reseñas paginadas: Parámetros `oa` (offset) en la URL

**Filtros disponibles en la web:**
- Establishment type: Restaurants, Coffee & Tea, Dessert, Bars & Pubs
- Meal type: Breakfast, Brunch, Lunch, Dinner
- Cusines: International, South American, Bar, Italian, etc.
- Price: Cheap Eats, Mid-range, Fine Dining
- Traveler rating: 3+, 4+, 5 bubbles
- Online options & offers
- Dietary restrictions: Vegetarian, Vegan, Gluten free
- Great for: Families, Business, Romantic, Large groups
- Features: Table Service, Seating, Reservations, Serves Alcohol

**Volumen estimado:** 1,470+ restaurantes listados en Panama City

---

## 4. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FUENTES DE DATOS                            │
├─────────────────────────────────────────────────────────────────────┤
│  Degusta Panamá (Scraping)          │  Fuente Secundaria (Kaggle)   │
│  └── Reviews + Ratings              │  └── CSV Dataset            │
└─────────────────┬───────────────────┴─────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PIPELINE ETL                                 │
├─────────────────────────────────────────────────────────────────────┤
│  EXTRACT                  TRANSFORM                  LOAD           │
│  ├── Scraping             ├── Limpieza               ├── DataFrame │
│  ├── CSV Reading          ├── Normalización          ├── CSV       │
│  └── API Calls (futuro)   ├── Deduplicación          └── JSON      │
│                            ├── Detección idioma                     │
│                            └── Tokenización                         │
└─────────────────┬───────────────────┴─────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ANÁLISIS DE DATOS                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│  │ SENTIMENT ANALYSIS│    │ ASPECT EXTRACTION │    │  CLUSTERING   │ │
│  │                  │    │                  │    │               │ │
│  │ ├── VADER/TextBlob│    │ ├── LLM Prompting │    │ ├── K-Means   │ │
│  │ └── LLM Classification│  │ ├── Comida       │    │ ├── Features  │ │
│  │                     │    │ ├── Servicio      │    │ └── Silhouette│ │
│  │                     │    │ ├── Precio        │    │               │ │
│  │                     │    │ └── Ambiente      │    │               │ │
│  └──────────────────┘    └──────────────────┘    └───────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    RECOMMENDATION SYSTEM                      │  │
│  │  Input: User preferences → Output: Ranked restaurant list     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DASHBOARD STREAMLIT                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📊 Home/Overview        │  📍 Comparación        │  😀 Sentiment   │
│  ├── Total restaurantes │  ├── Seleccionar 2+    │  ├── Distribución│
│  ├── Total reseñas      │  ├── Bar charts        │  ├── Por aspecto │
│  └── Rating promedio    │  ├── Radar charts      │  └── Timeline   │
│                          │  └── heatmaps          │                  │
│                                                                     │
│  🎯 Clustering          │  ⭐ Recomendaciones     │  🔍 Detalle    │
│  ├── Scatter plots      │  ├── Filtros           │  ├── Por rest.  │
│  ├── Cluster profiles   │  ├── Top recommendations│  ├── Reviews    │
│  └── Cluster map        │  └── LLM reasoning     │  └── Análisis   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Pipeline ETL - Especificación Detallada

### 5.1 Extract (EXTRACT)

#### Módulo: `src/ingestion/`

**Archivo:** `degusta_scraper.py`
```python
def scrape_restaurant_list(page=1, filters=None) -> List[Dict]
    """Extrae lista de restaurantes con metadata básica"""

def scrape_restaurant_details(restaurant_id: str) -> Dict
    """Extrae detalles completos de un restaurante"""

def scrape_reviews(restaurant_id: str, max_pages=10) -> List[Dict]
    """Extrae reseñas con calificaciones por aspecto"""

def scrape_all_reviews() -> pd.DataFrame
    """Orquestador principal del scraping"""
```

**Archivo:** `tripadvisor_scraper.py`
```python
def scrape_restaurant_list_panama(offset=0) -> List[Dict]
    """Extrae lista de restaurantes de Panama City con metadata"""

def scrape_restaurant_reviews(restaurant_id: str, offset=0) -> List[Dict]
    """Extrae reseñas de un restaurante específico"""

def get_restaurant_details(restaurant_id: str) -> Dict
    """Obtiene detalles: rating, categoría, precio, etc."""

def scrape_all_tripadvisor(max_restaurants=500, max_reviews_per_restaurant=50) -> pd.DataFrame
    """Orquestador principal - scraping completo con rate limiting"""
```

**Archivo:** `kaggle_loader.py` (fallback si scraping falla)
```python
def load_kaggle_dataset(dataset_path: str) -> pd.DataFrame
    """Carga dataset desde Kaggle/externo"""

def validate_schema(df: pd.DataFrame) -> bool
    """Valida que el dataset tenga columnas requeridas"""
```

**Archivo:** `degusta_scraper.py`

**Funciones:**
```python
def scrape_restaurant_list(page=1, filters=None) -> List[Dict]
    """Extrae lista de restaurantes con metadata básica"""

def scrape_restaurant_details(restaurant_id: str) -> Dict
    """Extrae detalles completos de un restaurante"""

def scrape_reviews(restaurant_id: str, max_pages=10) -> List[Dict]
    """Extrae reseñas con calificaciones por aspecto"""

def scrape_all_reviews() -> pd.DataFrame
    """Orquestador principal del scraping"""
```

**Archivo:** `kaggle_loader.py`
```python
def load_kaggle_dataset(dataset_path: str) -> pd.DataFrame
    """Carga dataset desde Kaggle/externo"""

def validate_schema(df: pd.DataFrame) -> bool
    """Valida que el dataset tenga columnas requeridas"""
```

**Salida:** `data/raw/raw_reviews.csv`

**Schema esperado:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| restaurant_id | string | Identificador único |
| restaurant_name | string | Nombre del restaurante |
| category | string | Tipo de cocina |
| location | string | Dirección |
| neighborhood | string | Barrio |
| price_range | string | Nivel de precio ($, $$-$$$, etc.) |
| overall_rating | float | Rating general (1-5) |
| food_rating | float | Rating comida (1-5) [Degusta únicamente] |
| service_rating | float | Rating servicio (1-5) [Degusta únicamente] |
| ambiance_rating | float | Rating ambiente (1-5) [Degusta únicamente] |
| review_text | string | Texto de la reseña |
| review_date | date | Fecha de la reseña |
| reviewer_name | string | Nombre del usuario |
| source | string | "degusta" o "tripadvisor" |
| review_count | int | Total de reseñas del restaurante |

---

### 5.2 Transform (TRANSFORM)

#### Módulo: `src/preprocessing/`

**Archivo:** `cleaner.py`
```python
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame
    """Elimina reseñas duplicadas basado en restaurant_id + review_text"""

def clean_text(text: str) -> str
    """Limpia texto: elimina caracteres especiales, emojis, URLs"""

def standardize_formats(df: pd.DataFrame) -> pd.DataFrame
    """Estandariza formatos de fecha, precio, ratings"""
```

**Archivo:** `normalizer.py`
```python
def normalize_text(text: str) -> str
    """Normaliza: lowercase,去除 acentos"""

def remove_stopwords(text: str, lang='spanish') -> str
    """Elimina stopwords"""

def tokenize(text: str) -> List[str]
    """Tokeniza texto"""

def detect_language(text: str) -> str
    """Detecta idioma (es/EN)"""
```

**Archivo:** `feature_engineering.py`
```python
def add_text_features(df: pd.DataFrame) -> pd.DataFrame
    """Añade features: word_count, char_count, etc."""

def calculate_restaurant_stats(df: pd.DataFrame) -> pd.DataFrame
    """Calcula estadísticas agregadas por restaurante"""
```

**Salida:** `data/processed/processed_reviews.csv`

---

### 5.3 Load (LOAD)

#### Módulo: `src/load/`

**Archivo:** `data_loader.py`
```python
def save_to_csv(df: pd.DataFrame, path: str) -> None
def save_to_json(df: pd.DataFrame, path: str) -> None
def load_processed_data() -> pd.DataFrame
```

---

## 6. Análisis de Sentimiento por Aspecto

### 6.1 Enfoque Técnico

**Arquitectura:** Hybrid Approach

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTIMENT ANALYSIS PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RAW REVIEW                                                      │
│  "La comida estuvo excelente pero el servicio fue lento"        │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                           │
│  │  LLM Classifier │  (OpenAI GPT-3.5 / Ollama)               │
│  │                 │                                           │
│  │  Prompt:        │                                           │
│  │  "Analyze this review and extract sentiment for each aspect:│
│  │   - Comida      │                                           │
│  │   - Servicio    │                                           │
│  │   - Precio      │                                           │
│  │   - Ambiente    │                                           │
│  │                  │                                           │
│  │  Return JSON"    │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                           │
│  │   JSON OUTPUT   │                                           │
│  │   {             │                                           │
│  │     "comida":   │                                           │
│  │       "positive",│                                          │
│  │     "servicio": │                                           │
│  │       "negative",│                                          │
│  │     "precio":   │                                           │
│  │       "neutral", │                                          │
│  │     "ambiente": │                                           │
│  │       "positive" │                                          │
│  │   }             │                                           │
│  │   }             │                                           │
│  └─────────────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              SENTIMENT SCORES TABLE                     │    │
│  │  restaurant_id │ comida │ servicio │ precio │ ambiente │    │
│  │  ──────────────────────────────────────────────────────  │    │
│  │  rest_001      │  0.85  │  -0.32   │  0.00  │  0.78    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Módulo: `src/sentiment/`

**Archivo:** `llm_classifier.py`
```python
class AspectSentimentClassifier:
    def __init__(self, provider='openai', model='gpt-3.5-turbo'):
        self.provider = provider  # 'openai' o 'ollama'
        self.model = model

    def analyze_review(self, review_text: str) -> Dict[str, str]:
        """Clasifica sentimiento por aspecto usando LLM"""

    def analyze_batch(self, reviews: List[str]) -> List[Dict[str, str]]:
        """Procesa múltiples reseñas con batching"""

    def to_numeric_score(self, sentiment: str) -> float:
        """Convierte positive/negative/neutral a 1.0/-1.0/0.0"""
```

**Archivo:** `fallback_classifier.py`
```python
class VADERSentimentAnalyzer:
    """Fallback usando VADER para sentiment general"""

class TextBlobAnalyzer:
    """Fallback secundario usando TextBlob"""
```

### 6.3 Prompt de LLM

```python
ASPECT_SENTIMENT_PROMPT = """
You are a restaurant review analyzer. For the following review, extract and classify
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

If an aspect is not mentioned, use "neutral".
"""
```

### 6.4 Criterios de Aceptación

| Métrica | Target | Método de evaluación |
|---------|--------|---------------------|
| Precisión del modelo | >70% | Validación manual de muestra (50 reseñas) |
| Cobertura de aspectos | 100% | Todas las reseñas procesadas |
| Tiempo de procesamiento | <5s por reseña | Con caching |
| Costo API | <$10 USD | Rate limiting + Ollama fallback |

---

## 7. Clustering de Restaurantes

### 7.1 Enfoque Técnico

**Algoritmo:** K-Means Clustering

**Variables para clustering:**
- Rating promedio general
- Sentimiento promedio por aspecto (4 features)
- Frecuencia de menciones positivas/negativas
- Categoría del restaurante (encoding)
- Rango de precio (encoding)

### 7.2 Módulo: `src/clustering/`

**Archivo:** `restaurant_clusterer.py`
```python
class RestaurantClusterer:
    def __init__(self, n_clusters=5):
        self.n_clusters = n_clusters
        self.model = KMeans(n_clusters=n_clusters, random_state=42)
        self.scaler = StandardScaler()

    def engineer_features(self, df: pd.DataFrame) -> np.ndarray:
        """Genera feature matrix para clustering"""

    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        """Entrena modelo y predice clusters"""

    def get_cluster_profiles(self, df: pd.DataFrame) -> Dict:
        """Genera perfil descriptivo de cada cluster"""
```

**Archivo:** `cluster_analyzer.py`
```python
def calculate_silhouette_score(features: np.ndarray, labels: np.ndarray) -> float
def find_optimal_k(features: np.ndarray, k_range=range(2, 10)) -> int
def visualize_clusters(df: pd.DataFrame, clusters: np.ndarray) -> plotly.Figure
```

### 7.3 Perfiles de Cluster Esperados

| Cluster | Característica Principal | Descripción |
|---------|-------------------------|-------------|
| 0 | "Premium Fine Dining" | Alta calificación, precio alto, ambiente excellent |
| 1 | "Value for Money" | Buena comida, precios accesibles, servicioOK |
| 2 | "Quick Bites" | Calificación media, enfoque en comida rápida |
| 3 | "Family Friendly" | Ambiente bueno, servicio bueno, para grupos |
| 4 | "Hidden Gems" | Ratings altos pero menos conocidos |

### 7.4 Criterios de Aceptación

| Métrica | Target | Método |
|---------|--------|--------|
| Silhouette Score | >0.3 | Scikit-learn metrics |
| Clusters interpretables | 100% | Validación manual |
| Cobertura de restaurantes | >80% | Mínimo 80% en clusters válidos |

---

## 8. Sistema de Recomendación

### 8.1 Enfoque Técnico

**Tipo:** Content-Based Filtering con LLM Reasoning

**Entrada del usuario:**
- Preferencia de tipo de comida
- Rango de presupuesto
- Aspectos importantes (comida, servicio, precio, ambiente)
- Ubicación preferida (opcional)

**Salida:**
- Top 5-10 restaurantes recomendados
- Justificación textual generada por LLM

### 8.2 Módulo: `src/recommendation/`

**Archivo:** `recommender.py`
```python
class RestaurantRecommender:
    def __init__(self, df: pd.DataFrame, classifier):
        self.df = df
        self.classifier = classifier

    def recommend(self,
                  cuisine: str = None,
                  max_price: str = None,
                  priority_aspects: List[str] = None,
                  location: str = None,
                  top_n: int = 5) -> List[Dict]:
        """Genera recomendaciones basadas en preferencias del usuario"""

    def generate_explanation(self, restaurant: Dict, preferences: Dict) -> str:
        """Genera justificación usando LLM"""
```

### 8.3 Ejemplo de Uso

**Input:**
```
Usuario busca: "Comida italiana, presupuesto medio, aspecto más importante: comida"
```

**Output:**
```
1. Salotto Italiano Bistrot (4.7★)
   Justificación: "Restaurante italiano con calificación de comida de 4.8/5,
   ubicado en San Francisco. Las reseñas destacan la calidad de la pasta
   y el risotto. Precio promedio de $25-35 por persona..."

2. La Strega Ristorante (4.6★)
   ...
```

---

## 9. Dashboard Streamlit

### 9.1 Estructura de Páginas

```
Dashboard/
├── app.py                 # Main entry point
├── pages/
│   ├── 1_📊_Overview.py   # Homepage con KPIs
│   ├── 2_📍_Comparar.py  # Comparación de restaurantes
│   ├── 3_😀_Sentimiento.py # Análisis de sentimiento
│   ├── 4_🎯_Clustering.py # Visualización de clusters
│   ├── 5_⭐_Recomendaciones.py # Sistema de recomendación
│   └── 6_🔍_Detalle.py   # Vista individual de restaurante
├── components/
│   ├── kpi_cards.py
│   ├── charts.py
│   └── filters.py
└── utils/
    ├── data_loader.py
    └── cache_manager.py
```

### 9.2 Especificación de Páginas

#### Página 1: Overview (Home)
**Objetivo:** Dashboard ejecutivo con métricas generales

**Componentes:**
- KPIs en tarjetas:
  - Total de restaurantes cargados
  - Total de reseñas procesadas
  - Rating promedio general
  - Distribución de sentimiento (%)
- Gráfico de barras: Top 10 restaurantes por rating
- Gráfico de pastel: Distribución por categoría de comida
- Histograma: Distribución de ratings
- Filtros en sidebar: Barrio, Categoría, Rango de precio

#### Página 2: Comparar
**Objetivo:** Comparar 2+ restaurantes lado a lado

**Componentes:**
- Selector múltiple de restaurantes
- Gráfico de barras: Ratings por aspecto
- Gráfico radar: Perfil comparativo
- Tabla de reseñas destacadas
- Heatmap de sentimiento por aspecto

#### Página 3: Sentimiento
**Objetivo:** Visualizar resultados del análisis de sentimiento

**Componentes:**
- Distribución general de sentimiento (pie chart)
- Stacked bar: Sentimiento por aspecto
- Word cloud: Palabras más frecuentes en positivas/negativas
- Timeline: Evolución del sentimiento (si hay datos temporales)
- Selector de restaurante para ver detalle

#### Página 4: Clustering
**Objetivo:** Visualizar grupos de restaurantes

**Componentes:**
- Scatter plot 2D de clusters (PCA)
- Perfil de cada cluster (ratings promedio)
- Lista de restaurantes por cluster
- Selector de cluster para filtrar

#### Página 5: Recomendaciones
**Objetivo:** Sistema interactivo de recomendación

**Componentes:**
- Formulario de preferencias:
  - Tipo de comida (dropdown)
  - Presupuesto (slider/radio)
  - Aspectos prioritarios (multiselect)
  - Ubicación (dropdown)
- Botón "Recomendar"
- Lista de resultados con:
  - Nombre y rating
  - Justificación generada por LLM
  - Links a detalle

#### Página 6: Detalle
**Objetivo:** Vista profunda de un restaurante específico

**Componentes:**
- Información del restaurante (nombre, categoría, ubicación, precio)
- Ratings promedios por aspecto
- Lista de reseñas con sentiment marcado
- Distribución de sentimiento de sus reseñas
- Comparar con similar (botón)

### 9.3 Theme y Estilo

```python
# config.py
THEME = {
    "primaryColor": "#FF6B6B",      # Rojo coral
    "backgroundColor": "#FFFFFF",   # Fondo blanco
    "secondaryBackgroundColor": "#F8F9FA",  # Gris claro
    "textColor": "#212529",         # Texto oscuro
    "font": "sans-serif"
}
```

---

## 10. Estructura del Repositorio

```
restaurant-sentiment-analysis/
├── .gitignore
├── README.md
├── requirements.txt
├── PRD.md
│
├── data/
│   ├── raw/
│   │   ├── raw_reviews.csv
│   │   └── kaggle_dataset.csv
│   ├── processed/
│   │   ├── processed_reviews.csv
│   │   └── restaurant_stats.csv
│   └── cache/
│       └── sentiment_cache.json
│
├── src/
│   ├── __init__.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── degusta_scraper.py
│   │   ├── kaggle_loader.py
│   │   └── api_client.py (futuro)
│   │
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── cleaner.py
│   │   ├── normalizer.py
│   │   └── feature_engineering.py
│   │
│   ├── sentiment/
│   │   ├── __init__.py
│   │   ├── llm_classifier.py
│   │   ├── fallback_classifier.py
│   │   └── batch_processor.py
│   │
│   ├── clustering/
│   │   ├── __init__.py
│   │   ├── restaurant_clusterer.py
│   │   └── cluster_analyzer.py
│   │
│   ├── recommendation/
│   │   ├── __init__.py
│   │   ├── recommender.py
│   │   └── explanation_generator.py
│   │
│   └── load/
│       ├── __init__.py
│       └── data_loader.py
│
├── dashboard/
│   ├── app.py
│   ├── config.py
│   ├── pages/
│   │   ├── 1_📊_Overview.py
│   │   ├── 2_📍_Comparar.py
│   │   ├── 3_😀_Sentimiento.py
│   │   ├── 4_🎯_Clustering.py
│   │   ├── 5_⭐_Recomendaciones.py
│   │   └── 6_🔍_Detalle.py
│   ├── components/
│   │   ├── kpi_cards.py
│   │   ├── charts.py
│   │   └── filters.py
│   └── utils/
│       ├── data_loader.py
│       └── cache_manager.py
│
├── notebooks/
│   ├── EDA.ipynb
│   ├── Model_Development.ipynb
│   └── Dashboard_Preview.ipynb
│
├── docs/
│   ├── TECHNICAL_SPEC.md
│   ├── API_DOCUMENTATION.md
│   └── USER_GUIDE.md
│
└── tests/
    ├── __init__.py
    ├── test_scraper.py
    ├── test_preprocessing.py
    ├── test_sentiment.py
    ├── test_clustering.py
    └── test_recommender.py
```

---

## 11. Cronograma del Proyecto (Semanas 9-11)

### Semana 9: Pipeline y Datos
| Día | Tarea | Entregable |
|-----|-------|-------------|
| 1-2 | Setup proyecto, GitHub, estructura | Repositorio creado |
| 3-4 | Scraping Degusta Panamá | Scraper funcional |
| 5 | Carga dataset secundario | Segunda fuente integrada |
| 6-7 | Pipeline ETL completo | data/raw y data/processed |

**Entregable Semana 9:** Pipeline ETL funcional documentado

### Semana 10: ML y Análisis
| Día | Tarea | Entregable |
|-----|-------|-------------|
| 1-2 | Integración LLM para sentimiento | Clasificador por aspecto |
| 3-4 | Fallback VADER/TextBlob | Pipeline híbrido |
| 5-6 | Clustering K-Means | Modelo de clusters |
| 7 | Validación y ajustes | Métricas de calidad |

**Entregable Semana 10:** Modelos de ML entrenados y validados

### Semana 11: Dashboard y Cierre
| Día | Tarea | Entregable |
|-----|-------|-------------|
| 1-2 | Dashboard Streamlit (3 páginas) | Pages 1-3 |
| 3-4 | Dashboard (páginas restantes) | Pages 4-6 |
| 5 | Sistema de recomendación | Integración en dashboard |
| 6 | Documentación final | README, docs/ |
| 7 | Presentación y demo | Entrega final |

**Entregable Semana 11:** Dashboard completo + documentación

---

## 12. Distribución de Responsabilidades

*[Ajustar según miembros del grupo]*

| Componente | Responsable | Backup |
|------------|-------------|--------|
| Scraping + ETL | Persona A | Persona B |
| Sentiment Analysis | Persona B | Persona A |
| Clustering | Persona C | Persona A |
| Recommender | Persona A | Persona C |
| Dashboard | Persona D | Persona C |
| Documentación | Todos | - |

---

## 13. Criterios de Éxito y Evaluación

### 13.1 Criterios de Éxito del Proyecto

El proyecto se considera exitoso si:

1. **Pipeline de datos (30% de la evaluación)**
   - [ ] Integra al menos 2 fuentes de datos
   - [ ] Pipeline ETL funcional y reproducible
   - [ ] Manejo correcto de errores
   - [ ] Datos almacenados en formato unificado

2. **Análisis ML (25% de la evaluación)**
   - [ ] Análisis de sentimiento por aspecto implementado
   - [ ] Uso de LLM para clasificación
   - [ ] Fallback implementado (VADER/TextBlob)
   - [ ] Clustering de restaurantes funcional
   - [ ] Métricas de calidad reportadas

3. **Dashboard (25% de la evaluación)**
   - [ ] Mínimo 3 páginas interactivas
   - [ ] Gráficos actualizados dinámicamente
   - [ ] Filtros funcionales
   - [ ] Visualización de sentimiento
   - [ ] Comparación de restaurantes

4. **Documentación (20% de la evaluación)**
   - [ ] README completo
   - [ ] Código documentado (docstrings)
   - [ ] Estructura del repositorio clara
   - [ ] PRD actualizado

### 13.2 Métricas de Calidad

| Componente | Métrica | Target |
|------------|---------|--------|
| Datos | Registros válidos | >500 reseñas |
| Datos | Duplicados eliminados | 100% detección |
| Sentiment | Accuracy (validación manual) | >70% |
| Sentiment | Cobertura | 100% reseñas |
| Clustering | Silhouette Score | >0.3 |
| Dashboard | Pages implementadas | 6/6 |
| Dashboard | Tiempo de carga | <5s por página |

---

## 14. Consideraciones Técnicas para Scraping

### 14.1 Degusta Panamá

**Robots.txt:** Verificar `https://www.degustapanama.com/robots.txt`

**Rate Limiting:**
- Implementar delay de 2-3 segundos entre requests
- Usar sesiones con user-agent rotativo
- Limitar requests a 1000 por hora

**Notas técnicas:**
- El sitio usa CDN (Cloudflare) puede requerir headers específicos
- Las reseñas están paginadas en URLs tipo `_fecha_{pag}_todos.html`
- Algunos datos cargan via JavaScript (considerar Selenium si es necesario)

### 14.2 Tripadvisor

**Rate Limiting:**
- Tripadvisor es conocido por bloquear scrapers
- Implementar delay de 5-10 segundos entre requests
- Usar proxies si es necesario
- Posible necesidad de cookies/sesiones

**Alternativa recomendada:**
- Tripadvisor ofrece API oficial a través de Accenture
- Investigar "Tripadvisor Content API" para acceso legal
- URL: https://www.tripadvisor.com/DevelopersCorner

**Estrategia de emergencia:**
- Si el scraping falla, usar dataset de Kaggle como fallback
- Dataset候选: "Tripadvisor Restaurant Reviews" (si disponible para Panamá)
- O generic "Restaurant Reviews and Ratings" dataset

---

## 15. Anexos

### A. Glosario

| Término | Definición |
|---------|------------|
| ETL | Extract, Transform, Load - Pipeline de datos |
| Aspect-based Sentiment | Análisis de sentimiento por aspecto específico |
| LLM | Large Language Model - Modelo de lenguaje grande |
| K-Means | Algoritmo de clustering no supervisado |
| Silhouette Score | Métrica de calidad de clustering |
| PCA | Principal Component Analysis - Reducción de dimensionalidad |

### B. Referencias Técnicas

- **OpenAI API:** https://platform.openai.com/docs/
- **Streamlit Docs:** https://docs.streamlit.io/
- **Scikit-learn:** https://scikit-learn.org/stable/
- **VADER Sentiment:** https://github.com/cjhutto/vaderSentiment
- **BeautifulSoup:** https://www.crummy.com/software/BeautifulSoup/

### C. Limitaciones Conocidas

1. Rate limiting en scraping de Degusta Panamá
2. Costo de API de OpenAI (mitigado con Ollama local)
3. Calidad variable de reseñas en español
4. Posible sesgo en dataset de Kaggle

---

## 16. Historial de Versiones

| Versión | Fecha | Autor | Cambios |
|---------|-------|-------|---------|
| 1.0 | 14-Jun-2026 | Grupo 5 | Versión inicial |

---

*Documento preparado para el Proyecto Integrador - Segundo Parcial*
*Facultad/Universidad - Curso de Ciencia de Datos*
