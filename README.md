# 🍽️ Plataforma de Análisis de Reseñas de Restaurantes — Panamá

Proyecto Integrador (Segundo Parcial) — **Grupo 5**

Sistema de gestión de información que recopila reseñas reales de restaurantes de
Ciudad de Panamá desde **dos fuentes distintas**, las procesa mediante un pipeline
ETL, aplica **análisis de sentimiento por aspecto** y **clustering (Machine
Learning)**, y las presenta en un **dashboard interactivo de Streamlit** con un
sistema de recomendación.

---

## 📑 Tabla de contenidos

1. [Problemática](#-problemática)
2. [Características principales](#-características-principales)
3. [Arquitectura y pipeline](#-arquitectura-y-pipeline)
4. [Stack tecnológico](#-stack-tecnológico)
5. [Fuentes de datos](#-fuentes-de-datos)
6. [Estructura del repositorio](#-estructura-del-repositorio)
7. [Instalación](#-instalación)
8. [Uso](#-uso)
9. [Componentes en detalle](#-componentes-en-detalle)
10. [Testing](#-testing)
11. [Cumplimiento de la rúbrica](#-cumplimiento-de-la-rúbrica)
12. [Limitaciones y notas](#-limitaciones-y-notas)
13. [Equipo y licencia](#-equipo-y-licencia)

---

## 🎯 Problemática

Elegir un restaurante en Ciudad de Panamá implica comparar opiniones dispersas en
múltiples plataformas, sin una vista unificada que separe **qué** se valora
(comida, servicio, precio, ambiente). Esta plataforma centraliza reseñas reales de
dos fuentes, las analiza por aspecto y permite **comparar restaurantes, descubrir
grupos similares (clusters) y recibir recomendaciones** según las preferencias del
usuario.

**Datos actuales:** 83 reseñas reales · 20 restaurantes · 9 categorías · 2 fuentes.

---

## ✨ Características principales

- 🔎 **Pipeline ETL** reproducible con **2 fuentes de datos reales**.
- 🧠 **Análisis de sentimiento por aspecto** (comida, servicio, precio, ambiente)
  con un clasificador léxico español/inglés (sin API key) y soporte opcional para
  LLM (Google Gemini).
- 🤖 **Clustering K-Means** de restaurantes con selección de *k* por *silhouette
  score*.
- ⭐ **Sistema de recomendación** basado en contenido (preferencias + sentimiento).
- 📊 **Dashboard interactivo** de 6 páginas con navegación nativa de Streamlit.
- ✅ **130 pruebas unitarias** (pytest).

---

## 🏗 Arquitectura y pipeline

```
┌──────────────────────────────┐
│        FUENTES DE DATOS       │
│  Degusta        RestaurantGuru│   (web scraping)
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│   INGESTA + UNIFICACIÓN       │   build_dataset.py
│   + sentimiento por aspecto   │   -> data/raw/raw_reviews.csv
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│            ETL                │   cleaner -> normalizer -> feature_engineering
│  limpieza · normalización ·   │   -> data/processed/*.csv
│  features                     │
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│        MACHINE LEARNING       │   K-Means clustering
│  clustering + perfiles        │   -> data/processed/restaurants_clustered.csv
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│      DASHBOARD (Streamlit)    │   6 páginas + recomendador
└──────────────────────────────┘
```

Todo el pipeline se ejecuta con un solo comando: `python run_pipeline.py`.

---

## 🧰 Stack tecnológico

| Componente            | Tecnología                          |
|-----------------------|-------------------------------------|
| Lenguaje              | Python 3.10+                        |
| Datos                 | pandas, numpy                       |
| Machine Learning      | scikit-learn (K-Means, silhouette)  |
| Scraping              | requests, BeautifulSoup, lxml       |
| Sentimiento           | Lexicón propio + vaderSentiment / TextBlob (LLM opcional: Google Gemini) |
| Visualización         | Streamlit, Plotly                   |
| Testing               | pytest, pytest-cov                  |

---

## 🌐 Fuentes de datos

Dos fuentes **reales e independientes** de reseñas de restaurantes en Ciudad de Panamá:

| Fuente | URL | Método | Reseñas |
|--------|-----|--------|---------|
| **Degusta Panamá** | https://www.degustapanama.com/ | Scraping de microdatos `schema.org` (`itemprop="reviewBody"`) con `requests` + `BeautifulSoup` | 59 |
| **RestaurantGuru** | https://restaurantguru.com/Panama-City | Scraping de reseñas agregadas (principalmente de Google) | 24 |

> **⚠️ Nota sobre Tripadvisor:** la segunda fuente planeada originalmente
> (`tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html`)
> responde **HTTP 403 + captcha** a los scrapers, por lo que se reemplazó por
> **RestaurantGuru**. El scraper de Tripadvisor se conserva en
> `src/ingestion/tripadvisor_scraper.py` como referencia del intento.

---

## 📁 Estructura del repositorio

```
restaurant-sentiment-analysis/
├── data/
│   ├── raw/                       # Fuentes y dataset unificado (versionados)
│   │   ├── degusta_reviews.csv
│   │   ├── restaurantguru_reviews.csv
│   │   └── raw_reviews.csv        # combinado + sentimiento
│   └── processed/                 # Salidas del pipeline (versionadas)
│       ├── cleaned_reviews.csv
│       ├── normalized_reviews.csv
│       ├── restaurant_features.csv
│       └── restaurants_clustered.csv   # archivo que carga el dashboard
├── src/
│   ├── ingestion/                 # Scrapers + construcción del dataset
│   │   ├── degusta_scraper.py
│   │   ├── restaurantguru_scraper.py
│   │   ├── tripadvisor_scraper.py # referencia (bloqueado por 403)
│   │   └── build_dataset.py
│   ├── preprocessing/             # cleaner, normalizer, feature_engineering
│   ├── sentiment/                 # clasificadores de sentimiento
│   │   ├── fallback_classifier.py # lexicón + VADER/TextBlob (por defecto)
│   │   ├── gemini_classifier.py   # LLM opcional (Google Gemini)
│   │   └── aspect_scores.py       # deriva sentiment_<aspecto>_score
│   ├── clustering/                # K-Means + perfiles de cluster
│   └── recommendation/            # recomendador basado en contenido
├── dashboard/
│   ├── app.py                     # entrypoint (st.navigation)
│   ├── config.py
│   └── views/                     # 6 páginas (render(df))
├── tests/                         # 130 pruebas unitarias + e2e
├── run_pipeline.py                # pipeline ETL+ML en un comando
├── requirements.txt
├── PRD.md                         # documento de requisitos del producto
└── README.md
```

---

## ⚙️ Instalación

Requiere **Python 3.10+**.

```bash
# 1. Clonar el repositorio
git clone https://github.com/1ZH13/Restaurant-Sentiment-Analysis.git
cd Restaurant-Sentiment-Analysis

# 2. Crear y activar un entorno virtual
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) variables de entorno — solo si vas a usar el LLM de Gemini
copy .env.example .env      # Windows  (cp en Linux/macOS)
```

> El análisis de sentimiento funciona **sin API key**. La clave de Gemini es
> opcional y solo se usa si querés sustituir el clasificador léxico por el LLM.

---

## 🚀 Uso

El dataset procesado **ya viene versionado** en `data/`, así que el dashboard
funciona de inmediato:

```bash
streamlit run dashboard/app.py
```

Luego abrí **http://localhost:8501** en el navegador.

> 💡 Si Streamlit dice que el puerto está ocupado y abre otro (8502, 8503…),
> cerrá las instancias previas o entrá al puerto que indique la consola.

### Regenerar los datos

**Opción A — un comando** (ETL + ML desde los archivos ya scrapeados):

```bash
python run_pipeline.py
```

**Opción B — paso a paso:**

```bash
# 1. Ingesta de las dos fuentes reales (scraping en vivo, con rate limiting)
python -m src.ingestion.degusta_scraper           # -> data/raw/degusta_reviews.csv
python -m src.ingestion.restaurantguru_scraper    # -> data/raw/restaurantguru_reviews.csv

# 2. Combinar fuentes + etiquetar sentimiento por aspecto
python -m src.ingestion.build_dataset             # -> data/raw/raw_reviews.csv

# 3. ETL: limpiar -> normalizar -> features
python -m src.preprocessing.cleaner
python -m src.preprocessing.normalizer
python -m src.preprocessing.feature_engineering

# 4. ML: clustering (genera el archivo que carga el dashboard)
python -m src.clustering.restaurant_clusterer     # -> data/processed/restaurants_clustered.csv

# 5. Dashboard
streamlit run dashboard/app.py
```

---

## 🔬 Componentes en detalle

### 1. Pipeline ETL (`src/ingestion`, `src/preprocessing`)
- **Extract:** scrapers de Degusta y RestaurantGuru → CSV por fuente.
- **Transform:** `cleaner` (deduplicación, limpieza de texto, estandarización de
  ratings/fechas) → `normalizer` (minúsculas, acentos, stopwords, tokenización,
  detección de idioma) → `feature_engineering` (word/char count, estadísticas por
  restaurante, encoding de precio).
- **Load:** CSVs en `data/processed/`.

### 2. Análisis de sentimiento por aspecto (`src/sentiment`)
Para cada reseña se clasifica el sentimiento de **comida, servicio, precio y
ambiente** como `positive` / `neutral` / `negative` y se convierte a un score
numérico (`+1 / 0 / -1`).

- **Clasificador por defecto:** `SpanishLexiconAnalyzer` — lexicón español/inglés
  con manejo de negación (p. ej. *"no recomiendo"* invierte la polaridad), sin API
  key. Combina el lexicón con VADER para texto en inglés.
- **LLM opcional:** `gemini_classifier.py` (Google Gemini) si se configura
  `GOOGLE_API_KEY`.

Sentimiento promedio actual por aspecto: **comida 0.73 · servicio 0.33 ·
ambiente 0.29 · precio 0.13** (escala −1 a +1).

### 3. Clustering (`src/clustering`)
- Algoritmo **K-Means** sobre features por restaurante (rating, sentimiento por
  aspecto, nº de reseñas, longitud media, precio).
- Selección de *k* evaluando el **silhouette score** (k = 2…9); se generan
  **5 clusters** con perfiles descriptivos y nombres automáticos
  (p. ej. *Premium Fine Dining*, *Foodie's Choice*).

### 4. Sistema de recomendación (`src/recommendation`)
Recomendador **basado en contenido**: el usuario indica tipo de cocina,
presupuesto y aspectos prioritarios; el sistema puntúa los restaurantes según
coincidencia + sentimiento y devuelve el top con una explicación.

### 5. Dashboard (`dashboard/`)
Seis páginas con navegación nativa (`st.navigation`):

| Página | Contenido |
|--------|-----------|
| 📊 **Overview** | KPIs, top 10 por rating, distribución de ratings/categorías/precios, sentimiento por aspecto |
| 📍 **Comparar** | Comparación lado a lado (2–5 restaurantes) con radar de aspectos |
| 😀 **Sentimiento** | Distribución de sentimiento, heatmap por categoría, mejores/peores reseñas |
| 🎯 **Clustering** | Tamaño de clusters, perfiles, top por cluster, mapa rating vs. sentimiento |
| ⭐ **Recomendaciones** | Formulario de preferencias + recomendaciones personalizadas |
| 🔍 **Detalle** | Vista individual de un restaurante con reseñas filtrables por sentimiento |

---

## 🧪 Testing

```bash
# Pruebas unitarias (rápidas)
pytest -m "not e2e" -q

# Incluir pruebas end-to-end del dashboard (requiere Playwright)
pytest -q
```

Suite actual: **130 pruebas unitarias** que cubren cleaner, normalizer, feature
engineering, sentimiento, clustering, recomendador y el pipeline.

---

## 📊 Cumplimiento de la rúbrica

| Componente | Peso | Cómo se cumple |
|------------|------|----------------|
| **Pipeline de datos** | 30% | ETL funcional y documentado con **2 fuentes reales** (Degusta + RestaurantGuru); reproducible con `run_pipeline.py` |
| **Análisis ML** | 25% | Clustering K-Means (silhouette) + análisis de sentimiento por aspecto |
| **Dashboard** | 25% | 6 páginas interactivas en Streamlit con filtros, comparativa y recomendaciones |
| **Documentación** | 20% | Este README + `PRD.md` + `docs/TECHNICAL_SPEC.md` + docstrings |

---

## ⚠️ Limitaciones y notas

- **RestaurantGuru aplica rate limiting** (HTTP 503 tras varias solicitudes
  seguidas). El scraper reintenta con *backoff*; para más datos, conviene correrlo
  por tandas.
- El análisis de sentimiento por defecto es **léxico** (no LLM), lo cual es rápido
  y reproducible pero menos matizado que un modelo de lenguaje.
- El dataset es **pequeño y centrado en Ciudad de Panamá** (alcance académico).

---

## 👥 Equipo y licencia

- **Grupo 5** — Plataforma de Análisis de Reseñas de Restaurantes
- Licencia: **MIT**
