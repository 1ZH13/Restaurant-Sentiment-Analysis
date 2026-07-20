# Plataforma de Análisis de Reseñas de Restaurantes — Panamá

Proyecto Integrador (Segundo Parcial) — **Grupo 5**

Sistema de gestión de información que recopila reseñas reales de restaurantes de
Ciudad de Panamá desde **dos fuentes distintas**, las procesa mediante un pipeline
ETL, aplica **análisis de sentimiento por aspecto** y **clustering (Machine
Learning)**, y las presenta en un **dashboard interactivo de Streamlit** con un
sistema de recomendación.

---

## Tabla de contenidos

1. [Problemática](#problemática)
2. [Características principales](#características-principales)
3. [Arquitectura y pipeline](#arquitectura-y-pipeline)
4. [Stack tecnológico](#stack-tecnológico)
5. [Fuentes de datos](#fuentes-de-datos)
6. [Estructura del repositorio](#estructura-del-repositorio)
7. [Instalación](#instalación)
8. [Uso](#uso)
9. [Componentes en detalle](#componentes-en-detalle)
10. [Testing](#testing)
11. [Cumplimiento de la rúbrica](#cumplimiento-de-la-rúbrica)
12. [Limitaciones y notas](#limitaciones-y-notas)
13. [Equipo y licencia](#equipo-y-licencia)

---

## Problemática

Elegir un restaurante en Ciudad de Panamá implica comparar opiniones dispersas en
múltiples plataformas, sin una vista unificada que separe **qué** se valora
(comida, servicio, precio, ambiente). Esta plataforma centraliza reseñas reales de
dos fuentes, las analiza por aspecto y permite **comparar restaurantes, descubrir
grupos similares (clusters) y recibir recomendaciones** según las preferencias del
usuario.

**Datos actuales:** 1108 reseñas reales · 241 restaurantes · 121 categorías de
cocina · 32 zonas de la ciudad · 2 fuentes.

| Campo | Cobertura |
|-------|-----------|
| Rango de precio | 100% |
| Zona | 100% |
| Calificación del restaurante | 100% |
| Categoría de cocina | 97% |
| Fecha de la reseña | 90% |
| Calificación propia de la reseña | 88% |

Las fechas van de 2019 a 2026. Para regenerar estas cifras: `python run_pipeline.py`.

---

## Características principales

- **Pipeline ETL** reproducible con **2 fuentes de datos reales**.
- **Unificación de identidad**: el mismo restaurante listado por ambas fuentes se
  reconcilia en un único `restaurant_id` canónico, y las reseñas repetidas se
  eliminan comparando el texto normalizado.
- **Análisis de sentimiento por aspecto** (comida, servicio, precio, ambiente)
  con un clasificador léxico español/inglés (sin API key), atribución por
  cercanía y registro de qué aspectos menciona cada reseña.
- **Clustering K-Means** de restaurantes con *k* elegido por *silhouette score* y
  nombres de cluster derivados de lo que distingue a cada grupo.
- **Sistema de recomendación** basado en contenido (cocina, presupuesto, zona y
  aspectos prioritarios) con puntaje de coincidencia 0–100.
- **Dashboard interactivo** de 6 páginas con filtros y búsqueda que afectan a
  todos los gráficos de la página.
- **Suite de pruebas** con pytest, incluyendo tests que manejan los widgets
  reales de Streamlit (`AppTest`).

---

## Arquitectura y pipeline

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

## Stack tecnológico

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

## Fuentes de datos

Dos fuentes **reales e independientes** de reseñas de restaurantes en Ciudad de Panamá:

| Fuente | URL | Método | Reseñas |
|--------|-----|--------|---------|
| **Degusta Panamá** | https://www.degustapanama.com/ | Microdatos `schema.org` (`itemprop`) con `requests` + `BeautifulSoup` | 973 |
| **RestaurantGuru** | https://restaurantguru.com/Panama-City | Reseñas agregadas (principalmente de Google), vía JSON-LD | 135 |

Tres restaurantes aparecían en ambas fuentes con nombres ligeramente distintos
(p. ej. *"El Trapiche (Bella Vista)"* y *"Restaurante El Trapiche Bella Vista"*)
y se unificaron en un solo registro.

### Cómo se consiguió el volumen

**Degusta no tiene paginación**: `/panama/search?page=2` devuelve exactamente la
misma página. Los restaurantes se descubren combinando varios puntos de entrada
—la portada de la ciudad más una búsqueda por cada tipo de cocina— lo que llega a
unos 220 restaurantes distintos. Cada ficha expone sus 5 reseñas más recientes.

**Los metadatos vienen de los microdatos, no de las clases CSS.** La ficha
publica `servesCuisine`, `priceRange`, `address` y, por cada reseña, su propio
`ratingValue` y `datePublished`. Leer esos atributos en vez de selectores como
`.price` o `[class*="category"]` es lo que llevó la cobertura de precio del 29%
al 100% y eliminó las categorías genéricas "General".

**RestaurantGuru limita agresivamente** (HTTP 503 tras unas pocas peticiones).
Su scraper usa backoff exponencial y guarda el CSV cada pocos restaurantes, para
que interrumpir una corrida no descarte lo ya recolectado. Una corrida completa
es lenta a propósito: es el costo de scrapear esta fuente de forma respetuosa.

> **Nota sobre Tripadvisor:** la segunda fuente planeada originalmente
> (`tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html`)
> responde **HTTP 403 + captcha** a los scrapers, por lo que se reemplazó por
> **RestaurantGuru**. El scraper de Tripadvisor se conserva en
> `src/ingestion/tripadvisor_scraper.py` como referencia del intento.

---

## Estructura del repositorio

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
│   │   └── aspect_scores.py       # deriva sentiment_<aspecto>_score y mentions_<aspecto>
│   ├── clustering/                # K-Means por restaurante + perfiles y nombres
│   └── recommendation/            # recomendador basado en contenido
├── dashboard/
│   ├── app.py                     # entrypoint (st.navigation)
│   ├── config.py
│   ├── utils/
│   │   ├── filters.py             # filtros y búsqueda compartidos por las páginas
│   │   ├── aspects.py             # promedios de sentimiento conscientes de cobertura
│   │   └── i18n.py
│   └── views/                     # 6 páginas (render(df))
├── tests/                         # pruebas unitarias + de dashboard + e2e
├── run_pipeline.py                # pipeline ETL+ML en un comando
├── requirements.txt
├── PRD.md                         # documento de requisitos del producto
└── README.md
```

---

## Instalación

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

## Uso

El dataset procesado **ya viene versionado** en `data/`, así que el dashboard
funciona de inmediato:

```bash
streamlit run dashboard/app.py
```

Luego abrí **http://localhost:8501** en el navegador.

> Si Streamlit dice que el puerto está ocupado y abre otro (8502, 8503…),
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

## Componentes en detalle

### 1. Pipeline ETL (`src/ingestion`, `src/preprocessing`)
- **Extract:** scrapers de Degusta y RestaurantGuru → CSV por fuente.
- **Transform:** `cleaner` (deduplicación, limpieza de texto, estandarización de
  ratings/fechas) → `normalizer` (minúsculas, acentos, stopwords, tokenización,
  detección de idioma) → `feature_engineering` (word/char count, estadísticas por
  restaurante, encoding de precio).
- **Load:** CSVs en `data/processed/`.

### 2. Análisis de sentimiento por aspecto (`src/sentiment`)
Para cada reseña se clasifica el sentimiento de **comida, servicio, precio y
ambiente** como `positive` / `neutral` / `negative`, con un score numérico
(`+1 / 0 / -1`), **y se registra si la reseña realmente habló de ese aspecto**.

- **Clasificador por defecto:** `SpanishLexiconAnalyzer` — lexicón español/inglés
  sin API key, con manejo de negación (*"no recomiendo"* invierte la polaridad) e
  intensificadores (*"muy bueno"* pesa más que *"bueno"*). Combina el lexicón con
  VADER para texto en inglés.
- **Atribución por cercanía:** cada palabra de sentimiento se asigna al aspecto
  mencionado **más cercano**. Por eso *"la comida estuvo excelente pero el
  servicio fue muy lento"* da comida positiva y servicio negativo, en vez del
  mismo puntaje mezclado a ambos.
- **"No mencionado" ≠ "neutral":** si una reseña nunca habla del precio, eso no
  es evidencia de que el precio sea promedio. Los promedios se calculan solo
  sobre las reseñas que sí mencionan cada aspecto, y el dashboard muestra
  siempre sobre cuántas reseñas se apoya cada barra.
- **LLM opcional:** `gemini_classifier.py` (Google Gemini) si se configura
  `GOOGLE_API_KEY`.

### 3. Clustering (`src/clustering`)
- Algoritmo **K-Means** aplicado **a nivel de restaurante**: la tabla de reseñas
  se agrega primero a una fila por restaurante (rating, sentimiento por aspecto,
  nº de reseñas, longitud media, nivel de precio). Las etiquetas se mapean de
  vuelta a las reseñas al final.
- El número de clusters **se elige con el silhouette score** (k = 2…9) y se
  entrena con ese valor, no con una constante.
- Cada cluster se nombra según **aquello en lo que se destaca frente a los
  demás** (métricas estandarizadas entre clusters), garantizando nombres únicos:
  p. ej. *Mejor calificados*, *Alta gama*, *Buena relación precio*. El nombre se
  guarda en la columna `cluster_name` y el dashboard lo usa.

> **Sobre el silhouette:** el valor real ronda **0.17**, que es bajo — los
> restaurantes no forman grupos nítidamente separados. Se reporta tal cual a
> propósito: el clustering describe tendencias, no fronteras duras.

### 4. Sistema de recomendación (`src/recommendation`)
Recomendador **basado en contenido**: el usuario indica tipo de cocina,
presupuesto, zona y aspectos prioritarios; el sistema puntúa los restaurantes y
devuelve el top con una explicación. El puntaje es un **porcentaje real (0–100)**:
cada criterio aporta una fracción de su propio peso y el total se normaliza por
los pesos efectivamente usados.

### 5. Dashboard (`dashboard/`)
Seis páginas con navegación nativa (`st.navigation`):

| Página | Contenido |
|--------|-----------|
| **Resumen** | Filtros + búsqueda, KPIs, top 10 por calificación, distribución por cocina/precio/zona, sentimiento por aspecto con su cobertura |
| **Comparar** | Comparación lado a lado (2–5 restaurantes) con radar de aspectos |
| **Sentimiento** | Distribución de sentimiento, desglose por aspecto, heatmap por cocina, reseñas destacadas |
| **Agrupamiento** | Grupos con nombre descriptivo, perfiles, miembros de cada grupo, mapa calificación vs. sentimiento |
| **Recomendaciones** | Formulario de preferencias (cocina, presupuesto, zona, aspectos) + recomendaciones con % de coincidencia |
| **Detalle** | Vista individual con reseñas filtrables por sentimiento y por texto, y contraste entre la nota del sitio y el sentimiento calculado |

**Filtros compartidos** (`dashboard/utils/filters.py`): búsqueda por nombre o
cocina, cocina, rango de precio, zona, grupo y calificación mínima. El
componente devuelve el DataFrame filtrado que **todos** los gráficos de la página
consumen, y muestra siempre cuántos restaurantes y reseñas quedaron.

**Honestidad de los gráficos** (`dashboard/utils/aspects.py`): los promedios de
sentimiento se calculan solo sobre las reseñas que mencionan cada aspecto, y cada
gráfico indica esa cobertura. El precio, por ejemplo, se comenta en una minoría
de las reseñas; el dashboard lo dice en vez de diluir el promedio con silencio.

---

## Testing

```bash
# Pruebas unitarias (rápidas)
pytest -m "not e2e" -q

# Incluir pruebas end-to-end del dashboard (requiere Playwright)
pytest -q
```

La suite cubre cleaner, normalizer, feature engineering, sentimiento, clustering,
recomendador y el pipeline completo. Además hay archivos dedicados a las
garantías que se rompieron alguna vez y no deben volver a romperse:

| Archivo | Qué protege |
|---------|-------------|
| `tests/test_data_quality.py` | IDs estables entre corridas, unificación de restaurantes entre fuentes, deduplicación, fechas relativas (*"hace un mes"*) y un único vocabulario de precio |
| `tests/test_aspect_attribution.py` | Que el sentimiento se atribuya al aspecto correcto y que "no mencionado" no se confunda con "neutral" |
| `tests/test_dashboard_filters.py` | Que los filtros y la búsqueda **realmente reduzcan** los datos de la página (se manejan los widgets reales vía `AppTest`) |
| `tests/test_recommender_scoring.py` | Que el puntaje de coincidencia sea un porcentaje 0–100 y que se usen todas las preferencias, incluida la zona |

---

## Cumplimiento de la rúbrica

| Componente | Peso | Cómo se cumple |
|------------|------|----------------|
| **Pipeline de datos** | 30% | ETL funcional y documentado con **2 fuentes reales** (Degusta + RestaurantGuru), 997 reseñas de 207 restaurantes; unificación de identidad entre fuentes y deduplicación; reproducible con `run_pipeline.py` |
| **Análisis ML** | 25% | Clustering K-Means por restaurante con *k* elegido por silhouette + análisis de sentimiento por aspecto con atribución por cercanía |
| **Dashboard** | 25% | 6 páginas interactivas en Streamlit; filtros y búsqueda que afectan a todos los gráficos; cada gráfico declara sobre cuántos datos se apoya |
| **Documentación** | 20% | Este README + `PRD.md` + `docs/TECHNICAL_SPEC.md` + `docs/EXPLICACION_PROYECTO.md` + docstrings |

---

## Limitaciones y notas

- **RestaurantGuru aplica rate limiting agresivo** (HTTP 503 tras pocas
  solicitudes). Su scraper usa backoff exponencial y guarda resultados
  parciales; conviene correrlo por tandas y con paciencia. Por eso aporta muchas
  menos reseñas que Degusta.
- **Degusta expone solo las 5 reseñas más recientes** de cada restaurante, así
  que el dataset favorece amplitud (muchos restaurantes) sobre profundidad
  (muchas reseñas por restaurante).
- El análisis de sentimiento por defecto es **léxico** (no LLM): rápido y
  reproducible, pero menos matizado que un modelo de lenguaje. No entiende
  sarcasmo ni contexto largo.
- **El sentimiento está sesgado a positivo** porque las reseñas publicadas en
  estas fuentes lo están: cerca del 87% de las reseñas resultan positivas. Las
  gráficas lo muestran tal cual en vez de forzar un balance artificial.
- **El precio se menciona en una minoría de las reseñas** (~19%). Su promedio se
  calcula solo sobre esas, y el dashboard indica la cobertura.
- El **silhouette del clustering es bajo (~0.17)**: los grupos describen
  tendencias, no fronteras nítidas.
- El dataset está **centrado en Ciudad de Panamá** (alcance académico).

---

## Equipo y licencia

- **Grupo 5** — Plataforma de Análisis de Reseñas de Restaurantes
- Licencia: **MIT**
