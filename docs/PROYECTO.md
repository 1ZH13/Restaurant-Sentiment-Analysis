# Manual del proyecto

Documentación completa del Proyecto Integrador del Grupo 5: análisis de reseñas
de restaurantes de Ciudad de Panamá.

Este documento cubre el proyecto de punta a punta: de dónde salen los datos, qué
les hace el pipeline, cómo se analiza el texto y cómo se verifica todo. Los
componentes que tienen su propio manual se enlazan en su sitio.

| Documento | Qué cubre |
|---|---|
| **PROYECTO.md** (este) | Datos, pipeline, análisis de texto, pruebas, limitaciones |
| [MODELOS.md](MODELOS.md) | Los tres modelos de aprendizaje automático, en detalle |
| [DASHBOARD.md](DASHBOARD.md) | El dashboard de Streamlit, página por página |
| [PREGUNTAS.md](PREGUNTAS.md) | 87 preguntas y respuestas para la defensa |
| [../powerbi/POWERBI.md](../powerbi/POWERBI.md) | Referencia del modelo de Power BI |
| [../powerbi/CONSTRUCCION.md](../powerbi/CONSTRUCCION.md) | Cómo se construyó Power BI, paso a paso |

---

## Índice

1. [Qué hace el proyecto](#1-qué-hace-el-proyecto)
2. [Puesta en marcha](#2-puesta-en-marcha)
3. [Los datos](#3-los-datos)
4. [Obtención: los scrapers](#4-obtención-los-scrapers)
5. [El pipeline, etapa por etapa](#5-el-pipeline-etapa-por-etapa)
6. [El análisis de sentimiento](#6-el-análisis-de-sentimiento)
7. [Los modelos](#7-los-modelos)
8. [Las pruebas](#8-las-pruebas)
9. [Calidad de datos](#9-calidad-de-datos)
10. [Limitaciones conocidas](#10-limitaciones-conocidas)
11. [Preguntas frecuentes para la defensa](#11-preguntas-frecuentes-para-la-defensa)

---

## 1. Qué hace el proyecto

Recoge reseñas reales de restaurantes de Ciudad de Panamá de dos fuentes
públicas, extrae de cada texto qué opina el cliente sobre **cuatro aspectos**
—comida, servicio, precio y ambiente—, y presenta el resultado en dos
herramientas complementarias.

**El problema que resuelve.** Una calificación de 4.2 estrellas no dice *por qué*.
Un restaurante con la comida excelente y el servicio pésimo puede tener la misma
nota que uno mediocre en todo. El proyecto separa esos componentes.

**Las cifras.**

| | |
|---|---|
| Reseñas | 1108 |
| Restaurantes | 241 |
| Fuentes | Degusta (973) · RestaurantGuru (135) |
| Rango de fechas | 2019 – 2026 |
| Calificación promedio | 4.49 de 5 |
| Pruebas automatizadas | 263 |

**Los componentes.**

```
Fuentes web  →  scrapers  →  pipeline  →  datos procesados  →  dashboard Streamlit
                                                            →  informe Power BI
```

---

## 2. Puesta en marcha

### Requisitos

Python 3.11. El proyecto usa un entorno virtual en `.venv`.

```bash
pip install -r requirements.txt
```

### Generar los datos

```bash
python run_pipeline.py
```

Un solo comando ejecuta las cinco etapas. Tarda unos segundos: **no vuelve a
scrapear**, trabaja sobre los CSV crudos ya guardados en `data/raw/`.

### Levantar el dashboard

```bash
streamlit run dashboard/app.py
```

### Abrir Power BI

Abrir `powerbi/Restaurantes.pbip` con Power BI Desktop y ajustar el parámetro
`RutaDatos`. Ver [CONSTRUCCION.md](../powerbi/CONSTRUCCION.md#2-conexión-a-los-datos-y-parámetro-de-ruta).

### Ejecutar las pruebas

```bash
python -m pytest tests/ --ignore=tests/test_dashboard_e2e.py
```

Las pruebas de extremo a extremo requieren navegadores de Playwright
(`playwright install`); sin ellos dan error de configuración, no de lógica.

### Habilitar el asistente (opcional)

Crear `.env` en la raíz:

```
GOOGLE_API_KEY=tu_clave
GEMINI_MODEL=gemini-3.5-flash
```

Ver [DASHBOARD.md](DASHBOARD.md#10-página-7--asistente).

---

## 3. Los datos

### Por qué dos fuentes

El requisito era usar datos reales. Se eligieron dos fuentes independientes para
no depender de los sesgos de una sola plataforma, y porque unificar identidades
entre fuentes distintas es en sí mismo un problema de ingeniería de datos que el
proyecto tenía que resolver.

**Tripadvisor quedó descartada:** devuelve HTTP 403 a los scrapers. El intento
está en `src/ingestion/tripadvisor_scraper.py`, conservado como evidencia de que
se probó.

### Qué aporta cada una

| | Degusta | RestaurantGuru |
|---|---|---|
| Reseñas | 973 | 135 |
| Nota por reseña | sí | no |
| Nota del restaurante | sí | sí |
| Limitación | solo las 5 reseñas más recientes por restaurante | rate limiting agresivo (HTTP 503) |

La consecuencia de la limitación de Degusta es que el conjunto favorece
**amplitud** (muchos restaurantes) sobre **profundidad** (muchas reseñas por
restaurante), y que las fechas se concentran en meses recientes.

### Estructura de los datos

```
data/
├── raw/                          salida directa de los scrapers
│   ├── degusta_reviews.csv
│   └── restaurantguru_reviews.csv
└── processed/                    salida del pipeline
    ├── cleaned_reviews.csv
    ├── normalized_reviews.csv
    ├── restaurant_features.csv
    └── restaurants_clustered.csv   ← el que consumen dashboard y Power BI
```

---

## 4. Obtención: los scrapers

### Degusta

`src/ingestion/degusta_scraper.py`. Recorre el listado de restaurantes de Ciudad
de Panamá y, para cada ficha, extrae las reseñas renderizadas en el servidor.

### RestaurantGuru

`src/ingestion/restaurantguru_scraper.py`. Agrega reseñas (mayoritariamente de
Google) y las renderiza en el servidor, así que se pueden obtener con
`requests` + BeautifulSoup, sin JavaScript ni clave de API.

**El sitio limita agresivamente.** Devuelve HTTP 503 tras unas pocas solicitudes
rápidas, así que cada descarga pasa por un **backoff exponencial**: ante un 429 o
un 503, espera y reintenta con esperas crecientes. Una ejecución completa es
lenta por diseño; es el precio de scrapear esta fuente de forma educada.

Los metadatos del restaurante se extraen del bloque **JSON-LD** de schema.org que
la página incrusta (`aggregateRating`, `priceRange`, `servesCuisine`, `address`).
Es más estable que raspar el HTML visible, que cambia con cada rediseño — aunque
tiene un problema documentado en la [sección 9](#9-calidad-de-datos).

### Identificadores estables

`make_restaurant_id` genera el identificador a partir del *slug* de la URL
mediante un hash **determinista**.

> **Defecto real corregido.** Antes se usaba `hash()` de Python, que está
> aleatorizado por proceso. Cada ejecución producía identificadores distintos
> para el mismo restaurante, de modo que nada se podía unir ni deduplicar entre
> ejecuciones. Está fijado por `tests/test_data_quality.py`.

---

## 5. El pipeline, etapa por etapa

```bash
python run_pipeline.py
```

Ejecuta cinco etapas en orden:

### Etapa 1 — Unificar fuentes y calcular sentimiento

`src/ingestion/build_dataset.py`

Combina los CSV crudos, unifica la identidad de los restaurantes entre fuentes,
deduplica reseñas y calcula el sentimiento por aspecto con el léxico propio.

**Unificación de identidad.** El mismo restaurante puede llamarse *"Café Perú"* en
una fuente y *"cafe peru"* en otra. `normalize_name` ignora acentos, mayúsculas y
palabras genéricas (*restaurante*, *café*…) para generar una clave común, y
`canonical_id` produce un identificador estable a partir de ella. Las sucursales
se mantienen separadas a propósito: *"Sushi Express Punta Pacífica"* y *"Sushi
Express Costa del Este"* son locales distintos.

**Deduplicación.** Se eliminan reseñas con texto idéntico del mismo restaurante,
comparando tras normalizar puntuación y acentos. El mismo texto en restaurantes
distintos **sí** se conserva: son reseñas diferentes.

### Etapa 2 — Limpieza

`src/preprocessing/cleaner.py`

- **Fechas relativas.** Las fuentes escriben *"hace 3 meses"*. `parse_relative_date`
  las convierte a fecha absoluta.
- **Vocabulario de precios único.** Cada fuente usa su propia notación
  (`"Hasta $15"`, `"$"`, `"$$"`). `add_price_band` los unifica en cuatro bandas:
  `$ (hasta $15)`, `$$ ($15-$25)`, `$$$ ($25-$35)`, `$$$$ (mas de $35)`.
- **Categoría principal.** De `"Italiana, Pizzería"` se extrae `Italiana` como
  `category_primary`, para poder agrupar sin que cada combinación sea una
  categoría nueva.

> **Defecto real corregido.** `clean_text` eliminaba el carácter `·`, que las
> fuentes usan como separador de cocinas. `"Española · Argentina"` se convertía en
> una sola palabra. Ahora el separador se preserva como coma.

### Etapa 3 — Normalización

`src/preprocessing/normalizer.py`

Normaliza el texto para el análisis: minúsculas, espacios, caracteres de control.
Detecta el idioma de cada reseña (`review_language`) y calcula `word_count` y
`char_count`.

### Etapa 4 — Ingeniería de características

`src/preprocessing/feature_engineering.py`

Agrega las reseñas a nivel de **restaurante** y construye las ocho variables que
alimentan el clustering:

`avg_rating`, `sentiment_comida_avg`, `sentiment_servicio_avg`,
`sentiment_precio_avg`, `sentiment_ambiente_avg`, `review_count`,
`avg_word_count`, `price_level`.

También codifica las variables categóricas.

### Etapa 5 — Agrupamiento

`src/clustering/restaurant_clusterer.py`

K-Means sobre las ocho variables, con selección de *k* por silhouette. Genera
`cluster` y `cluster_name`. Detalle completo en [MODELOS.md](MODELOS.md).

**El resultado es determinista:** volver a ejecutar el pipeline produce un CSV
byte a byte idéntico.

---

## 6. El análisis de sentimiento

`src/sentiment/fallback_classifier.py` — clase `SpanishLexiconAnalyzer`.

Es el motor por defecto del proyecto, y es **propio**, no una librería genérica.

### Por qué un léxico propio

Las herramientas estándar de análisis de sentimiento en español no distinguen
*aspectos*: dicen si una reseña es positiva, no si lo positivo era la comida y lo
negativo el servicio. Y el requisito del proyecto era precisamente el desglose
por aspecto.

### Cómo funciona

**1. Detección de menciones.** Cada aspecto tiene un conjunto de términos
disparadores. Si la reseña no contiene ninguno, ese aspecto queda marcado como
**no mencionado** (`mentions_<aspecto> = False`) y su puntaje no se promedia en
ningún sitio. Es la base de la regla de cobertura que recorre todo el proyecto.

**2. Puntuación.** Sobre la ventana de texto alrededor de la mención, se buscan
términos del léxico:

| Componente | Tamaño |
|---|---|
| Léxico positivo | 171 términos |
| Léxico negativo | 152 términos |
| Intensificadores | 17 (*muy*, *súper*, *demasiado*…) |
| Negadores | 8 (*no*, *nada*, *nunca*…) |

**3. Negación e intensificación.** *"no es bueno"* no es positivo. Los negadores
invierten el signo del término al que afectan; los intensificadores amplifican su
magnitud.

**4. Resultado.** Por aspecto: una etiqueta (`positive` / `negative` / `neutral`)
y un puntaje continuo de −1 a 1.

### Atribución por aspecto

El caso difícil es una reseña que habla de varios aspectos con opiniones
distintas: *"la comida excelente pero el servicio lentísimo"*. La atribución
asocia cada término de sentimiento al aspecto más cercano en el texto, en lugar
de aplicar el sentimiento global a todos. Está cubierta por
`tests/test_aspect_attribution.py`.

### Alternativas incluidas

`fallback_classifier.py` también expone un analizador basado en **VADER**, usado
como contraste. Y el proyecto compara tres enfoques completos —léxico, supervisado
y LLM— en `src/classification/comparar_enfoques.py`. Ver [MODELOS.md](MODELOS.md).

---

## 7. Los modelos

El proyecto aplica **tres** enfoques de aprendizaje automático. Cada uno está
explicado en detalle en [MODELOS.md](MODELOS.md); aquí va el resumen.

| Modelo | Tipo | Resultado |
|---|---|---|
| K-Means | No supervisado | k=4, silhouette 0.17 |
| TF-IDF + regresión logística | Supervisado | F1 macro 0.713 ± 0.020 (validación cruzada), AUC 0.794 |
| Gemini | Modelo de lenguaje | Consultas en lenguaje natural, resúmenes y clasificación |

**Por qué tres y no uno.** Porque permite compararlos contra la misma verdad de
referencia —la calificación en estrellas que puso el propio reseñador, que
ninguno de los tres ve— y medirlos con la misma vara. La comparación se ejecuta
con:

```bash
python -m src.classification.comparar_enfoques --muestra 80
```

**El punto importante para la defensa:** sobre una partición de prueba única el
modelo supervisado parece no superar al léxico (F1 0.616 frente a 0.624), pero
esa partición tiene solo 32 casos de la clase minoritaria y mover tres aciertos
cambia el F1 varios puntos. La cifra a mirar es la validación cruzada de 5
particiones, donde el modelo gana con claridad: **0.713 frente a 0.618**.

---

## 8. Las pruebas

**263 pruebas.** No son decorativas: cada archivo corresponde a un aspecto real
del sistema y muchas fijan defectos que llegaron a producirse.

| Archivo | Qué cubre |
|---|---|
| `test_sentiment.py` | El léxico: negación, intensificadores, puntuación |
| `test_aspect_attribution.py` | Que cada opinión se asigne al aspecto correcto |
| `test_pipeline.py` | Las etapas del pipeline de extremo a extremo |
| `test_data_quality.py` | Identificadores estables, deduplicación, fechas, precios, calificaciones no fiables |
| `test_classification.py` | Modelo supervisado y asistente con LLM |
| `test_recommender.py`, `test_recommender_scoring.py` | Motor de recomendación y su puntuación |
| `test_restaurant_directory.py` | Directorio de restaurantes |
| `test_recommendations_page.py` | Página de recomendaciones |
| `test_documentacion.py` | **Que la documentación no se desincronice del código** |
| `test_dashboard_e2e.py` | Extremo a extremo con Playwright (requiere navegadores) |

### El caso de `test_documentacion.py`

Merece mención aparte porque nació de un defecto real: el README declaraba *"997
reseñas de 207 restaurantes"* cuando el conjunto ya tenía 1108 y 241. Nadie se dio
cuenta porque **ninguna prueba miraba la documentación**.

Ahora se verifica automáticamente que:

- Las cifras del README coinciden con los datos reales.
- Las 30 medidas DAX del modelo estén todas documentadas, y que no se documente
  ninguna que no exista.
- Los 22 visuales del informe estén documentados con su tamaño real.
- El código Power Query citado en la documentación exista literalmente en el modelo.
- Toda tabla del modelo esté registrada en `model.tmdl`.
- Los títulos de los visuales estén en `visualContainerObjects` y no en `objects`.
- Los archivos del informe sean UTF-8 sin BOM.

---

## 9. Calidad de datos

### Tres calificaciones no fiables

**El hallazgo.** *Aji de Cali* figuraba como el peor restaurante del conjunto
(1.1 de 5) pese a tener tres reseñas elogiosas: *"Mi lugar favorito de arepas
colombianas"*, *"Comida excelente"*.

**La verificación.** Se contrastó contra la fuente:

| | |
|---|---|
| Lo que muestra la web de RestaurantGuru | **4.6 / 5** |
| Lo que declara su JSON-LD | `ratingValue: 1.1` con `bestRating: 5` |

El scraper lee el JSON-LD, así que copió fielmente un dato que la propia fuente se
contradice.

**El síntoma en el conjunto.** Las calificaciones de RestaurantGuru son 1.1, 1.9,
2.4 y luego saltan a 4.8, 4.9, 5.0 — **nada entre 2.4 y 4.8**. No es una
distribución plausible. Y los tres restaurantes por debajo de 3 tienen sentimiento
léxico positivo.

**La respuesta.** No se corrigen: no hay forma de recuperar el valor bueno sin
volver a scrapear, y la fuente es lenta a propósito. En su lugar,
`src/preprocessing/calidad.py` los **detecta** comparando la calificación con el
sentimiento del texto, y:

- se excluyen de los rankings del asistente,
- la ficha del restaurante en el dashboard muestra un aviso,
- las pruebas **fijan el número en 3**, de modo que un nuevo scrape que introduzca
  más casos falla en vez de pasar desapercibido.

**Consecuencia en el clustering.** El cluster 3 son exactamente esos tres
restaurantes. Explicado en [MODELOS.md](MODELOS.md).

Es preferible declarar una limitación conocida que presentar un ranking que
sabemos que está mal.

---

## 10. Limitaciones conocidas

- **Tres calificaciones de RestaurantGuru no son fiables** (sección 9).
- **RestaurantGuru limita agresivamente**, por eso aporta muchas menos reseñas que
  Degusta.
- **Degusta expone solo las 5 reseñas más recientes** de cada restaurante: el
  conjunto favorece amplitud sobre profundidad y las fechas se concentran en meses
  recientes.
- **El análisis de sentimiento por defecto es léxico**, no un modelo de lenguaje:
  rápido y reproducible, pero no entiende sarcasmo ni contexto largo.
- **El sentimiento está sesgado a positivo** porque las reseñas publicadas lo
  están: cerca del 87% resultan positivas. Las gráficas lo muestran tal cual en
  vez de forzar un balance artificial.
- **El precio se menciona en el 22% de las reseñas.** Su promedio se calcula solo
  sobre esas, y tanto el dashboard como Power BI indican la cobertura.
- **El silhouette del clustering es bajo (0.17)**: los grupos describen un
  continuo, no fronteras nítidas.
- **`Calificación promedio` cubre el 88% de las reseñas**: solo Degusta publica la
  nota individual.
- **La ruta de datos de Power BI es absoluta.** Power BI no admite rutas
  relativas; por eso existe el parámetro `RutaDatos`.
- **Google retira modelos de Gemini sin aviso.** Comprobar con
  `python -m src.llm.modelos_disponibles`.

---

## 11. Preguntas frecuentes para la defensa

**¿Los datos son reales o inventados?**
Reales, scrapeados de dos fuentes públicas independientes. Los CSV crudos están
en `data/raw/` y los scrapers en `src/ingestion/`.

**¿Por qué no usaron Tripadvisor?**
Devuelve HTTP 403 a los scrapers. El intento está conservado en
`src/ingestion/tripadvisor_scraper.py`.

**¿Por qué un léxico propio y no una librería?**
Porque las librerías estándar dan un sentimiento global, y el proyecto necesitaba
el desglose por aspecto. Ver sección 6.

**¿Cómo saben que el análisis de sentimiento funciona?**
Se contrasta contra la calificación en estrellas que puso el propio reseñador,
que el modelo no ve. Y se compara con otros dos enfoques en
`comparar_enfoques.py`.

**¿Por qué el sentimiento es tan positivo?**
Porque las reseñas publicadas lo son: cerca del 87%. Es un sesgo de la fuente, y
se declara en vez de maquillarse.

**¿Por qué el silhouette es tan bajo?**
Porque casi todos los restaurantes tienen calificaciones entre 4.3 y 4.9: hay
poca variación de la que separar grupos. Una versión anterior mostraba 0.58, pero
era falso —se agrupaban reseñas en vez de restaurantes—. Ver [MODELOS.md](MODELOS.md).

**¿Qué es el cluster 3?**
No es un perfil de restaurante: es el residuo de las tres calificaciones
corruptas de RestaurantGuru. Ver sección 9.

**¿El LLM inventa datos?**
Se le pasa un contexto compacto con los agregados del proyecto y se le instruye
que diga qué dato faltaría en lugar de estimarlo. El dashboard muestra el
contexto exacto que recibió, para poder verificarlo. Comprobado en vivo.

**¿Por qué Power BI si ya hay un dashboard?**
Porque hacen cosas distintas: Streamlit produce el análisis (NLP, ML), Power BI
explora el resultado en ejes que el dashboard no cubre —sobre todo el temporal—.
Ver [DASHBOARD.md](DASHBOARD.md#12-reparto-de-trabajo-con-power-bi).

**¿Cómo se reproduce todo?**
`python run_pipeline.py`. Es determinista: produce un CSV idéntico cada vez.
