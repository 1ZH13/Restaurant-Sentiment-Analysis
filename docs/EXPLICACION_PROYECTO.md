# Plataforma de Analisis de Resenas de Restaurantes en Panama

## 1. Descripcion general

La Plataforma de Analisis de Resenas de Restaurantes es un sistema que recopila opiniones reales de restaurantes en Panama, procesa esos textos, identifica sentimientos por aspectos especificos y muestra los resultados en un dashboard interactivo.

El proyecto analiza principalmente cuatro aspectos:

- Comida
- Servicio
- Precio
- Ambiente

El objetivo es ayudar a comparar restaurantes con datos, no solamente con una calificacion general. Por ejemplo, dos restaurantes pueden tener una calificacion alta, pero uno puede destacar por comida y otro por servicio. El analisis por aspecto permite ver esas diferencias.

## 2. Problematica real

La problematica identificada es que las opiniones sobre restaurantes estan dispersas en varias plataformas. Un usuario debe revisar varios sitios para saber si un restaurante tiene buena comida, buen servicio, precios justos o buen ambiente.

Este proyecto resuelve esa situacion centralizando resenas reales, limpiandolas, analizandolas y transformandolas en indicadores comparables.

Ejemplo:

```text
Resena: "La comida estuvo excelente, pero el servicio fue lento."

Resultado:
comida: positivo
servicio: negativo
precio: neutral
ambiente: neutral
```

## 3. Criterios de uso

La plataforma se usa cuando se quiere:

- Comparar restaurantes de Panama usando resenas reales.
- Identificar que aspectos valoran o critican mas los usuarios.
- Ver patrones entre restaurantes similares.
- Recomendar restaurantes segun preferencias del usuario.
- Convertir texto no estructurado en datos analizables.

Entradas principales del sistema:

- Nombre del restaurante.
- Texto de la resena.
- Categoria o tipo de cocina.
- Ubicacion.
- Rango de precio.
- Calificacion general.
- Fuente de la resena.

Salidas principales:

- Dataset limpio y normalizado.
- Sentimiento por aspecto.
- Clusters de restaurantes.
- Dashboard comparativo.
- Recomendaciones personalizadas.

## 4. Dataset de resenas y web scraping

El proyecto utiliza datos reales obtenidos desde dos fuentes:

- Degusta Panama
- RestaurantGuru

La fuente Tripadvisor fue considerada inicialmente, pero no se uso como fuente principal porque bloquea el scraping mediante HTTP 403 y captcha. Por eso se reemplazo por RestaurantGuru.

Archivos de datos principales:

- `data/raw/degusta_reviews.csv`
- `data/raw/restaurantguru_reviews.csv`
- `data/raw/raw_reviews.csv`
- `data/processed/cleaned_reviews.csv`
- `data/processed/normalized_reviews.csv`
- `data/processed/restaurant_features.csv`
- `data/processed/restaurants_clustered.csv`

El proyecto documenta:

- 1108 resenas reales.
- 241 restaurantes.
- 2 fuentes de datos.
- 121 categorias de cocina.
- 32 zonas de Ciudad de Panama.

## 5. Que es web scraping

Web scraping es una tecnica para extraer informacion de paginas web de forma automatizada. En este proyecto se usa para obtener resenas, nombres de restaurantes, categorias, ratings y otros datos relacionados.

Librerias usadas:

- `requests`
- `BeautifulSoup`
- `lxml`

Los scrapers estan en:

- `src/ingestion/degusta_scraper.py`
- `src/ingestion/restaurantguru_scraper.py`
- `src/ingestion/tripadvisor_scraper.py`

El archivo que combina las fuentes es:

- `src/ingestion/build_dataset.py`

## 6. Pipeline de datos

El sistema sigue un flujo ETL mas Machine Learning y dashboard.

```text
Scraping de Degusta + RestaurantGuru
        ↓
Unificacion del dataset
        ↓
Limpieza de datos
        ↓
Normalizacion de texto
        ↓
Creacion de variables
        ↓
Analisis de sentimiento por aspecto
        ↓
Clustering K-Means
        ↓
Dashboard Streamlit
        ↓
Sistema de recomendacion
```

El pipeline principal esta en:

- `run_pipeline.py`

Se ejecuta con:

```bash
python run_pipeline.py
```

Este comando ejecuta:

1. Combinacion de fuentes y sentimiento por aspecto.
2. Limpieza.
3. Normalizacion.
4. Feature engineering.
5. Clustering.

## 7. Ingesta de las dos fuentes de datos

La ingesta consiste en obtener datos desde Degusta Panama y RestaurantGuru, guardarlos como archivos CSV y luego unirlos en un solo dataset.

Flujo:

```text
Degusta Panama -> degusta_reviews.csv
RestaurantGuru -> restaurantguru_reviews.csv
Ambos archivos -> raw_reviews.csv
```

El archivo `build_dataset.py` carga ambas fuentes, elimina registros sin texto util, elimina duplicados evidentes y agrega el analisis de sentimiento por aspecto.

## 8. Preprocesamiento y transformacion

El preprocesamiento prepara los datos antes de analizarlos.

Incluye:

- Eliminacion de duplicados.
- Eliminacion de registros sin campos esenciales.
- Limpieza de URLs, HTML y caracteres especiales.
- Conversion de ratings a valores numericos.
- Estandarizacion de fechas.
- Normalizacion de texto a minusculas.
- Eliminacion de acentos.
- Eliminacion de stopwords.
- Deteccion simple de idioma.
- Calculo de variables de texto.

Archivos principales:

- `src/preprocessing/cleaner.py`
- `src/preprocessing/normalizer.py`
- `src/preprocessing/feature_engineering.py`

Variables generadas:

- Cantidad de palabras.
- Cantidad de caracteres.
- Longitud promedio de palabras.
- Rating promedio.
- Rango de precio codificado.
- Cantidad de resenas.
- Sentimiento numerico por aspecto.

## 9. Analisis de sentimiento por aspecto

El analisis de sentimiento identifica si una opinion es positiva, neutral o negativa.

En este proyecto no se analiza solamente la resena completa. Se analiza por aspecto:

- Comida
- Servicio
- Precio
- Ambiente

Ejemplo:

```text
"La comida estuvo excelente, pero el servicio fue lento."

comida: positive
servicio: negative
precio: neutral
ambiente: neutral
```

El sistema convierte los sentimientos a valores numericos:

```text
positive = 1
neutral = 0
negative = -1
```

Archivo principal:

- `src/sentiment/fallback_classifier.py`

## 10. Uso de LLM

El proyecto tiene soporte opcional para LLM mediante Google Gemini:

- `src/sentiment/gemini_classifier.py`

Sin embargo, el proyecto funciona por defecto sin API key usando un clasificador lexico en espanol e ingles.

El clasificador lexico usa listas de palabras positivas y negativas, palabras clave por aspecto y manejo de negaciones.

Ejemplo:

```text
"No recomiendo el servicio"
```

La palabra "recomiendo" podria ser positiva, pero al estar precedida por "no", el sistema invierte la polaridad.

Ventajas del metodo lexico:

- No necesita API key.
- Es rapido.
- Es reproducible.
- Funciona localmente.

Ventajas de un LLM:

- Comprende mejor el contexto.
- Puede interpretar frases complejas.
- Puede manejar mejor ambiguedad y sarcasmo.

## 11. Machine Learning: clustering

La tecnica de Machine Learning aplicada es K-Means Clustering.

K-Means es un algoritmo no supervisado. Esto significa que no necesita etiquetas previas. El modelo agrupa restaurantes segun similitudes en sus caracteristicas.

Archivo principal:

- `src/clustering/restaurant_clusterer.py`

Variables usadas para clustering:

- Rating promedio.
- Sentimiento promedio de comida.
- Sentimiento promedio de servicio.
- Sentimiento promedio de precio.
- Sentimiento promedio de ambiente.
- Cantidad de resenas.
- Promedio de palabras por resena.
- Rango de precio codificado.

El sistema tambien evalua el numero de clusters usando silhouette score.

## 12. Que es silhouette score

Silhouette score es una metrica que mide que tan bien separados estan los clusters.

Sirve para evaluar si los grupos formados por K-Means tienen sentido:

- Un valor mas alto indica grupos mejor separados.
- Un valor bajo indica que los grupos se mezclan mucho.

En el proyecto se prueban valores de `k` de 2 a 9, se selecciona el mejor segun esta metrica **y el modelo se entrena con ese valor**. Antes el codigo calculaba el mejor `k` y luego lo ignoraba, entrenando siempre con 5 clusters fijos.

El silhouette real del dataset ronda 0.17, que es un valor bajo: significa que los restaurantes no forman grupos nitidamente separados. Se reporta asi a proposito. Un valor mucho mas alto que aparecia antes (~0.58) era artificial, porque el clustering se hacia sobre filas de resenas repetidas: varias filas identicas del mismo restaurante estan a distancia cero entre si e inflan la metrica.

## 13. Clustering de restaurantes

El clustering permite descubrir perfiles de restaurantes, por ejemplo:

- Restaurantes premium.
- Restaurantes economicos.
- Restaurantes con buena comida.
- Restaurantes con buen servicio.
- Restaurantes balanceados.

El resultado final se guarda en:

- `data/processed/restaurants_clustered.csv`

Este archivo es el que usa el dashboard.

## 14. Dashboard interactivo con Streamlit

Streamlit es una libreria de Python para crear aplicaciones web interactivas enfocadas en datos.

En este proyecto se usa para mostrar:

- Indicadores generales.
- Comparacion entre restaurantes.
- Graficas de sentimiento.
- Clusters.
- Recomendaciones.
- Detalle por restaurante.

Archivo principal:

- `dashboard/app.py`

Se ejecuta con:

```bash
streamlit run dashboard/app.py
```

El dashboard carga:

- `data/processed/restaurants_clustered.csv`

Paginas del dashboard:

- Resumen.
- Comparar.
- Sentimiento.
- Agrupamiento.
- Recomendaciones.
- Detalle.

## 15. Sistema de recomendacion

El sistema de recomendacion es basado en contenido.

Esto significa que recomienda restaurantes comparando las preferencias del usuario con las caracteristicas de cada restaurante.

Archivo principal:

- `src/recommendation/recommender.py`

El usuario puede seleccionar:

- Tipo de cocina.
- Rango de precio.
- Aspectos prioritarios.
- Ubicacion, si esta disponible.

El sistema calcula un puntaje de coincidencia usando:

- Categoria.
- Precio.
- Rating general.
- Sentimiento por aspecto.

Luego devuelve los mejores restaurantes con una explicacion.

## 16. Requisitos tecnicos

El proyecto usa:

- Python 3.10+
- pandas
- numpy
- scikit-learn
- Streamlit
- Plotly
- BeautifulSoup
- requests
- lxml
- nltk
- TextBlob
- vaderSentiment
- google-generativeai
- openai
- pytest

Archivo de dependencias:

- `requirements.txt`

Instalacion:

```bash
pip install -r requirements.txt
```

Ejecucion del dashboard:

```bash
streamlit run dashboard/app.py
```

Ejecucion del pipeline:

```bash
python run_pipeline.py
```

## 17. Resumen de implementacion

El proyecto implementa una solucion completa de analisis de resenas:

1. Obtiene resenas reales mediante scraping.
2. Une dos fuentes de datos.
3. Limpia y normaliza los textos.
4. Extrae sentimiento por aspecto.
5. Genera variables para analisis.
6. Agrupa restaurantes mediante K-Means.
7. Muestra resultados en Streamlit.
8. Recomienda restaurantes segun preferencias.

## 18. Preguntas y respuestas para exposicion

### 1. Cual es el objetivo principal del proyecto?

El objetivo es recopilar resenas reales de restaurantes en Panama, analizarlas por sentimiento y aspectos especificos como comida, servicio, precio y ambiente, para luego mostrar resultados comparativos en un dashboard y generar recomendaciones.

### 2. Que problema real resuelve?

Resuelve la dificultad de comparar restaurantes cuando las opiniones estan dispersas en varias plataformas. El sistema centraliza resenas, las procesa y permite comparar restaurantes con datos mas estructurados.

### 3. Por que no basta con ver la calificacion general?

Porque una calificacion general no explica que fue bueno o malo. Un restaurante puede tener buena comida pero mal servicio. El analisis por aspecto da mas detalle.

### 4. Que fuentes de datos se usaron?

Se usaron Degusta Panama y RestaurantGuru.

### 5. Por que no se uso Tripadvisor como fuente principal?

Porque Tripadvisor bloqueo el scraping con error HTTP 403 y captcha. Por eso se dejo como referencia y se reemplazo por RestaurantGuru.

### 6. Que es web scraping?

Es una tecnica para extraer informacion de paginas web de forma automatizada. En este proyecto se usa para obtener resenas, nombres de restaurantes, categorias, ratings y otros datos.

### 7. Que librerias se usaron para scraping?

Se usaron `requests`, `BeautifulSoup` y `lxml`.

### 8. Que datos se obtienen con el scraping?

Nombre del restaurante, resena, calificacion, categoria, ubicacion, rango de precio, fuente y algunos ratings especificos cuando estan disponibles.

### 9. El scraping se ejecuta cada vez que se abre el dashboard?

No. El scraping es parte de la ingesta de datos. El dashboard usa archivos ya procesados para cargar mas rapido.

### 10. Cuantas resenas tiene el dataset?

1108 resenas reales: 973 de Degusta y 135 de RestaurantGuru.

### 11. Cuantos restaurantes analiza?

241 restaurantes de Ciudad de Panama.

### 12. Por que Degusta aporta muchas mas resenas que RestaurantGuru?

Por como responde cada sitio al scraping. Degusta entrega las 5 resenas mas
recientes de cada ficha sin restricciones fuertes, y se pueden descubrir unos 220
restaurantes combinando la portada con busquedas por tipo de cocina.
RestaurantGuru limita agresivamente (devuelve HTTP 503 tras pocas peticiones), asi
que su scraper avanza lento y con esperas crecientes. El alcance sigue siendo
academico y acotado a Ciudad de Panama.

### 13. Que limitacion tiene un dataset pequeno?

Puede limitar la precision de los modelos y la generalizacion de los resultados. Con mas resenas, los clusters y recomendaciones serian mas robustos.

### 14. Que se hizo con los datos despues de obtenerlos?

Se combinaron las fuentes, se eliminaron duplicados, se limpiaron textos, se normalizaron variables, se calculo sentimiento por aspecto y se generaron features para clustering y dashboard.

### 15. Que es preprocesamiento de datos?

Es preparar los datos antes de analizarlos. Incluye limpiar texto, eliminar duplicados, convertir ratings a numeros y crear nuevas variables utiles.

### 16. Por que se eliminan duplicados?

Para evitar que una misma resena influya dos veces en los resultados y distorsione los promedios.

### 17. Por que se normaliza el texto?

Para que el analisis sea mas consistente. Por ejemplo, convertir a minusculas y quitar acentos ayuda a comparar palabras similares.

### 18. Que son stopwords?

Son palabras muy comunes como "el", "la", "de" o "que", que normalmente no aportan mucho significado al analisis.

### 19. Que features se generan?

Cantidad de palabras, cantidad de caracteres, promedio de palabras por resena, rating promedio, rango de precio codificado y sentimientos por aspecto.

### 20. Que es analisis de sentimiento?

Es una tecnica que identifica si un texto expresa una opinion positiva, negativa o neutral.

### 21. Que significa analisis de sentimiento por aspecto?

Significa analizar la opinion sobre partes especificas del restaurante, no solo sobre la resena completa.

### 22. Que aspectos analiza el proyecto?

Comida, servicio, precio y ambiente.

### 23. El proyecto usa LLM obligatoriamente?

No. Funciona por defecto con un clasificador lexico en espanol e ingles. El LLM, como Gemini, es opcional.

### 24. Que ventaja tendria usar un LLM?

Un LLM puede entender mejor el contexto, sarcasmo o frases complejas.

### 25. Que ventaja tiene el metodo lexico usado por defecto?

No necesita API key, es rapido, reproducible y funciona localmente.

### 26. Como se representa el sentimiento numericamente?

Se representa asi: positivo = 1, neutral = 0 y negativo = -1.

### 27. Que tecnica de Machine Learning se aplico?

Se aplico clustering usando K-Means.

### 28. Que es clustering?

Es una tecnica no supervisada que agrupa elementos similares. En este caso, agrupa restaurantes con caracteristicas parecidas.

### 29. Por que se usa K-Means?

Porque es un algoritmo simple, eficiente y adecuado para agrupar restaurantes segun variables numericas como rating, precio y sentimiento.

### 30. Que significa aprendizaje no supervisado?

Significa que el modelo no necesita etiquetas previas. El algoritmo descubre grupos por similitud.

### 31. Que variables usa el clustering?

Rating promedio, sentimientos por aspecto, numero de resenas, longitud promedio del texto y rango de precio.

### 32. Que es silhouette score?

Es una metrica que evalua que tan bien separados estan los clusters.

### 33. Para que sirven los clusters?

Sirven para identificar perfiles de restaurantes, como restaurantes premium, economicos, con buena comida o con mejor servicio.

### 34. Que es Streamlit?

Streamlit es una herramienta de Python para crear aplicaciones web interactivas enfocadas en datos.

### 35. Por que se uso Streamlit?

Porque permite crear dashboards rapidamente, integrandose bien con pandas, Plotly y modelos de Machine Learning.

### 36. Que muestra el dashboard?

Muestra metricas generales, comparaciones entre restaurantes, analisis de sentimiento, clusters, recomendaciones y detalle individual.

### 37. El dashboard calcula todo desde cero?

No. Carga los datos procesados desde `data/processed/restaurants_clustered.csv`.

### 38. Que ventaja tiene separar pipeline y dashboard?

Hace que el dashboard sea mas rapido y estable, porque no depende de hacer scraping o procesamiento pesado cada vez que se abre.

### 39. Como funciona el sistema de recomendacion?

Compara las preferencias del usuario con las caracteristicas de cada restaurante y calcula un puntaje de coincidencia.

### 40. Que tipo de recomendador es?

Es un recomendador basado en contenido.

### 41. Que toma en cuenta para recomendar?

Tipo de cocina, rango de precio, rating general y sentimientos por aspectos prioritarios.

### 42. Usa historial de usuarios?

No. No es filtrado colaborativo. Recomienda segun caracteristicas del restaurante.

### 43. Que diferencia hay entre recomendacion basada en contenido y colaborativa?

La basada en contenido usa caracteristicas del item, como precio o categoria. La colaborativa usa comportamiento de otros usuarios.

### 44. Que lenguaje se uso?

Python.

### 45. Que librerias principales se usaron?

pandas, numpy, scikit-learn, Streamlit, Plotly, BeautifulSoup, requests, nltk, TextBlob y vaderSentiment.

### 46. Donde esta el pipeline principal?

En `run_pipeline.py`.

### 47. Donde esta el dashboard?

En `dashboard/app.py`.

### 48. Donde esta el clustering?

En `src/clustering/restaurant_clusterer.py`.

### 49. Donde esta el recomendador?

En `src/recommendation/recommender.py`.

### 50. Donde esta el analisis de sentimiento?

En `src/sentiment/fallback_classifier.py` y opcionalmente en `src/sentiment/gemini_classifier.py`.

### 51. Cual es la mayor limitacion del proyecto?

El tamano del dataset. Al tener pocas resenas, los resultados son utiles como demostracion, pero mejorarian con mas datos.

### 52. Que mejorarias en una siguiente version?

Aumentaria el dataset, integraria mas fuentes, usaria un LLM de forma mas robusta y agregaria geolocalizacion o mapas.

### 53. Que riesgo existe con el analisis lexico?

Puede fallar con sarcasmo, frases ambiguas o contextos complejos.

### 54. Como se podria mejorar el analisis de sentimiento?

Usando un modelo entrenado en espanol o un LLM configurado para analisis por aspecto.

### 55. Que pasa si una resena no menciona precio?

El sentimiento de precio queda neutral, porque no hay evidencia suficiente para clasificarlo como positivo o negativo.

### 56. Por que es importante analizar por aspecto?

Porque permite saber exactamente que esta funcionando bien o mal en cada restaurante.

### 57. El sistema reemplaza la opinion humana?

No. Sirve como apoyo para organizar y resumir grandes cantidades de opiniones.

### 58. El proyecto cumple con un flujo completo de ciencia de datos?

Si. Incluye ingesta, limpieza, transformacion, analisis, Machine Learning, visualizacion y recomendacion.

## 19. Conclusiones

Este proyecto demuestra como integrar varias areas de ciencia de datos y desarrollo de software en una solucion funcional:

- Recoleccion de datos reales.
- Procesamiento ETL.
- Analisis de texto.
- Sentimiento por aspecto.
- Machine Learning no supervisado.
- Visualizacion interactiva.
- Sistema de recomendacion.

La plataforma permite transformar resenas dispersas en informacion util para comparar restaurantes y tomar mejores decisiones.
