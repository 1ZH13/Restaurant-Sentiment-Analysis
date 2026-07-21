# El dashboard de Streamlit, página por página

Documentación completa del dashboard interactivo: qué hay en cada una de las
siete páginas, cómo se construyó, qué decisiones se tomaron y por qué.

Es el equivalente, para el dashboard, de lo que
[`powerbi/CONSTRUCCION.md`](../powerbi/CONSTRUCCION.md) es para Power BI.

---

## Índice

1. [Cómo ejecutarlo](#1-cómo-ejecutarlo)
2. [Arquitectura del dashboard](#2-arquitectura-del-dashboard)
3. [Reglas transversales](#3-reglas-transversales)
4. [Página 1 — Resumen](#4-página-1--resumen)
5. [Página 2 — Comparar](#5-página-2--comparar)
6. [Página 3 — Sentimiento](#6-página-3--sentimiento)
7. [Página 4 — Agrupamiento](#7-página-4--agrupamiento)
8. [Página 5 — Recomendaciones](#8-página-5--recomendaciones)
9. [Página 6 — Detalle](#9-página-6--detalle)
10. [Página 7 — Asistente](#10-página-7--asistente)
11. [Errores reales corregidos](#11-errores-reales-corregidos)
12. [Reparto de trabajo con Power BI](#12-reparto-de-trabajo-con-power-bi)

---

## 1. Cómo ejecutarlo

```bash
python run_pipeline.py          # genera los datos (una vez)
streamlit run dashboard/app.py  # levanta el dashboard
```

Se abre en `http://localhost:8501`. Si no hay datos procesados, la aplicación no
se rompe: muestra una pantalla con las instrucciones para generar el conjunto de
datos.

---

## 2. Arquitectura del dashboard

```
dashboard/
├── app.py                  punto de entrada, navegación y carga de datos
├── config.py               tema oscuro (CSS)
├── views/                  una página por archivo
│   ├── overview.py         Resumen
│   ├── comparar.py         Comparar
│   ├── sentimiento.py      Sentimiento
│   ├── clustering.py       Agrupamiento
│   ├── recomendaciones.py  Recomendaciones
│   ├── detalle.py          Detalle
│   └── asistente.py        Asistente con LLM
└── utils/                  lógica compartida entre páginas
    ├── aspects.py          máscaras de mención y resúmenes por aspecto
    ├── data_loader.py      lectura de CSV
    ├── i18n.py             traducción de valores al español
    └── restaurants.py      directorio y etiquetas de restaurante
```

### La carga de datos

`app.py` centraliza la carga en una sola función, cacheada:

```python
@st.cache_data
def load_data():
    df = pd.read_csv("data/processed/restaurants_clustered.csv")
    df = translate_dashboard_dataframe(df)
    return derive_aspect_sentiment_scores(df)
```

Tres pasos y cada uno tiene motivo:

1. **Se lee `restaurants_clustered.csv`**, la salida final del pipeline. Es el
   único archivo que tiene todo junto: reseña, restaurante, sentimiento y grupo.
2. **`translate_dashboard_dataframe`** traduce los *valores* al español
   (`degusta` → `Degusta`, categorías de cocina, etc.). La traducción se hace en
   la carga y no en cada página, para que todas muestren lo mismo.
3. **`derive_aspect_sentiment_scores`** calcula las columnas
   `sentiment_<aspecto>_score` si el CSV es de una versión anterior del pipeline.
   Es una salvaguarda: sin ella, un CSV viejo haría que todas las páginas de
   sentimiento salieran vacías sin explicar por qué.

`@st.cache_data` evita releer el CSV en cada interacción. **Es también la razón
de una regla importante:** las páginas *no deben escribir* en el DataFrame que
reciben. Ese objeto viene de la caché y es compartido; escribir en él filtra
estado de una página a otra. Es un error que llegó a ocurrir (ver sección 11).

### La navegación

Se usa la navegación multipágina nativa de Streamlit (`st.navigation` /
`st.Page`), con las siete páginas declaradas en `app.py`. Cada página es una
función `render(df)` que recibe los datos ya cargados y filtrados.

---

## 3. Reglas transversales

Tres criterios se aplican en todo el dashboard y conviene poder defenderlos.

### 3.1 — Los promedios de sentimiento solo cuentan a quien opinó

Es la decisión más importante de todo el análisis. Si una reseña no habla del
precio, su puntaje de precio es 0. Promediar esos ceros arrastra todo hacia el
centro y produce una lectura falsa: parece que el precio genera indiferencia,
cuando en realidad **no se menciona**.

Por eso `dashboard/utils/aspects.py` define `mention_mask(df, aspecto)`, y todo
promedio se calcula solo sobre las reseñas que mencionan ese aspecto.

El efecto es grande: el precio se menciona en el **22%** de las reseñas. Contando
los silencios como neutros, su sentimiento se veía plano; contando solo a quien
opina, sale **+0.27**, claramente el aspecto peor valorado.

### 3.2 — Toda cifra declara su cobertura

Consecuencia directa de la regla anterior: si un promedio se calcula sobre una
parte de los datos, hay que decir sobre cuál. Cada barra de sentimiento indica
cuántas reseñas la respaldan, y `coverage_note()` genera esa nota.

| Aspecto | Sentimiento | Lo mencionan | Cobertura |
|---|---|---|---|
| Comida | +0.66 | 1014 reseñas | 92% |
| Servicio | +0.61 | 721 reseñas | 65% |
| Ambiente | +0.52 | 686 reseñas | 62% |
| Precio | +0.27 | 240 reseñas | 22% |

### 3.3 — Los grupos son propiedad del restaurante, no de la reseña

El clustering agrupa **restaurantes**. Como el CSV tiene una fila por reseña, un
restaurante con 5 reseñas aparece 5 veces. Cualquier conteo de "restaurantes por
grupo" tiene que deduplicar antes, o multiplica por el número de reseñas.

---

## 4. Página 1 — Resumen

**Archivo:** `dashboard/views/overview.py`
**Qué responde:** ¿qué hay en este conjunto de datos?

### Estructura

**Filtros (arriba del todo).** Cocina, zona y banda de precio. Todo lo que hay
debajo —KPIs, gráficas y tablas— se calcula sobre el DataFrame ya filtrado.

> **Detalle a defender.** Los filtros estaban al final de la página y solo
> imprimían un conteo de filas: seleccionar una categoría no cambiaba nada en
> pantalla. Se movieron arriba y ahora alimentan todo el contenido. Es la
> diferencia entre un filtro decorativo y uno real.

**Métricas clave.** Fila de KPIs: total de reseñas, total de restaurantes,
calificación promedio y cobertura.

**Mejores restaurantes y distribución de calificaciones.** Dos columnas:

- *10 mejores por calificación* — ranking con el número de reseñas al lado, para
  que se vea sobre qué base se apoya cada posición.
- *Distribución de calificaciones* — histograma que muestra el sesgo del
  conjunto: casi todo se concentra entre 4.3 y 4.9.

**Distribuciones.** Reseñas por cocina, por zona y por banda de precio.

---

## 5. Página 2 — Comparar

**Archivo:** `dashboard/views/comparar.py`
**Qué responde:** ¿cómo se comparan estos restaurantes concretos entre sí?

### Estructura

**Selector múltiple** de restaurantes. El resto de la página se dibuja sobre la
selección.

**Información de restaurantes.** Tabla con cocina, zona, banda de precio y
calificación de cada uno.

**Comparación de calificaciones.** Dos columnas:

- *Calificación general* — barras comparativas.
- *Calificación por aspecto (radar)* — gráfico de radar con los cuatro aspectos.
  El radar es la forma natural de comparar varias entidades sobre los mismos
  cuatro ejes: se ve de un vistazo la *forma* del perfil, no solo su tamaño. Un
  restaurante equilibrado dibuja un polígono regular; uno desparejo, uno picudo.

**Cantidad de reseñas.** Porque comparar un restaurante de 30 reseñas con uno de
2 no es comparar lo mismo.

**Reseñas de muestra.** Texto real de cada restaurante seleccionado, para poder
contrastar las cifras con lo que dice la gente.

---

## 6. Página 3 — Sentimiento

**Archivo:** `dashboard/views/sentimiento.py`
**Qué responde:** ¿qué opinan los clientes y de qué?

Es la página que muestra el resultado del análisis de texto, el núcleo del
proyecto.

### Estructura

**Resumen de sentimiento.** KPIs con el sentimiento global y por aspecto.

**Sentimiento promedio por aspecto** y **Desglose de opiniones por aspecto**, en
dos columnas. El primero da el promedio; el segundo, la composición
positivo / neutral / negativo. Los dos hacen falta: un promedio de 0 puede ser
"todo el mundo indiferente" o "mitad encantados, mitad furiosos", y solo el
desglose los distingue.

**Sentimiento por tipo de cocina.** Mapa de calor cocina × aspecto.

**Reseñas destacadas.** Las cinco más negativas (`nsmallest(5)` por sentimiento).
Nótese que rankea por **sentimiento**, no por calificación — por eso esta página
no se ve afectada por las tres calificaciones corruptas de RestaurantGuru
descritas en el README.

---

## 7. Página 4 — Agrupamiento

**Archivo:** `dashboard/views/clustering.py`
**Qué responde:** ¿hay perfiles de restaurante diferenciados?

Muestra el resultado del K-Means. La explicación completa del modelo está en
[MODELOS.md](MODELOS.md).

### Estructura

**Tarjetas por grupo**, con el nombre descriptivo generado por el pipeline
(*"Los más comentados"*, *"Buena relación precio"*…) en vez de "Grupo 3".

**Restaurantes por grupo** y **Calificación promedio por grupo**, en dos
columnas. El conteo es **por restaurante**, deduplicando, según la regla 3.3.

**Perfiles de grupo.** Qué caracteriza a cada uno.

> **Nota para la defensa.** El silhouette es 0.17: los grupos no están nítidamente
> separados, hay un continuo. Y el cluster 3 tiene solo 3 restaurantes: son
> exactamente los tres con calificación corrupta. Ambas cosas están explicadas en
> [MODELOS.md](MODELOS.md); conviene mencionarlas antes de que las pregunten.

---

## 8. Página 5 — Recomendaciones

**Archivo:** `dashboard/views/recomendaciones.py`
**Motor:** `src/recommendation/recommender.py`
**Qué responde:** dime qué buscas y te digo dónde ir.

### Cómo puntúa

El usuario indica qué le importa (cocina, presupuesto, prioridad entre comida /
servicio / precio / ambiente) y el motor puntúa cada restaurante.

**El cálculo es una media ponderada normalizada.** Cada criterio aporta una
fracción de 0 a 1 de su propio peso, y el total se divide entre los pesos
**realmente usados**. Esto importa: la versión anterior sumaba magnitudes brutas
y dividía entre el *número* de pesos, de modo que un usuario que rellenaba tres
preferencias obtenía puntuaciones sistemáticamente más bajas que uno que
rellenaba una sola. Normalizar por los pesos aplicados hace las puntuaciones
comparables.

El presupuesto no es un filtro duro: si un restaurante se pasa del presupuesto,
recibe una penalización proporcional (`1 - exceso/3`) en vez de quedar excluido.
Un sitio ligeramente más caro pero perfecto en todo lo demás sigue siendo una
recomendación razonable.

> **Detalle a defender.** El selector de precio ofrecía etiquetas (`"$$ - $$$"`)
> que no existían en los datos, así que la preferencia de presupuesto no
> coincidía nunca con nada. Ahora las opciones se construyen **a partir de los
> valores reales del conjunto**, de modo que no pueden desincronizarse si el
> vocabulario de las fuentes cambia.

---

## 9. Página 6 — Detalle

**Archivo:** `dashboard/views/detalle.py`
**Qué responde:** todo sobre un restaurante concreto.

### Estructura

**Cabecera** con el nombre, la calificación en una insignia de color (verde ≥4.5,
ámbar ≥4, rojo por debajo, gris si no hay nota) y etiquetas de cocina, precio y
zona.

**Aviso de calidad de datos.** Si el restaurante es uno de los tres con
calificación no fiable, se muestra una advertencia explicando que su calificación
contradice el texto de sus reseñas por una inconsistencia de la fuente. Sin esto,
la ficha de *Aji de Cali* mostraría un 1.1 a secas junto a reseñas elogiosas.

**Sentimiento por aspecto** del restaurante, con su cobertura.

**Lista de reseñas** con filtro por sentimiento y una insignia por reseña.

> **Detalle a defender.** El filtro de sentimiento no hacía nada: las reseñas se
> construían tomando columnas que empiezan por `sentiment_`, pero el filtro leía
> una columna llamada `overall_sentiment_score`, que nunca estaba presente.
> Seleccionar "Negativo" devolvía en silencio *todas* las reseñas, y la insignia
> por reseña no se dibujaba nunca. Ambos funcionan ahora sobre una columna
> calculada explícitamente.

---

## 10. Página 7 — Asistente

**Archivo:** `dashboard/views/asistente.py`
**Motor:** `src/llm/asistente.py`
**Qué responde:** pregunta lo que quieras, en lenguaje natural.

Cubre el requisito de incorporar un modelo de lenguaje para interactuar con los
datos. Tiene dos pestañas.

### Pestaña 1 — Preguntar en lenguaje natural

Un cuadro de texto (con preguntas de ejemplo) que envía la consulta al modelo
junto con un **contexto compacto** de los datos.

**El modelo no recibe las 1108 reseñas.** No cabrían y saldría caro. Recibe un
resumen de unos 1300 caracteres con los agregados que el proyecto ya calcula:

```
RESUMEN GENERAL
- Reseñas: 1108
- Restaurantes: 241
- Fuentes: Degusta, RestaurantGuru
- Calificación promedio: 4.49 de 5

SENTIMIENTO POR ASPECTO
  Comida: sentimiento +0.66, lo mencionan 1014 reseñas (92%)
  Servicio: sentimiento +0.61, lo mencionan 721 reseñas (65%)
  Precio: sentimiento +0.27, lo mencionan 240 reseñas (22%)
  Ambiente: sentimiento +0.52, lo mencionan 686 reseñas (62%)

MEJOR CALIFICADOS / PEOR CALIFICADOS / COCINAS / ZONAS / RANGOS DE PRECIO
GRUPOS DEL CLUSTERING / LIMITACIÓN CONOCIDA DE LOS DATOS
```

**Cómo se evita que invente cifras.** El *prompt* le indica que use únicamente
esos datos, que no recurra a conocimiento general sobre restaurantes, y que si la
respuesta no está en el contexto **diga qué dato faltaría** en lugar de
estimarla. Un asistente que alucina cifras en un trabajo de análisis de datos es
peor que no tener asistente.

Además, la página incluye un desplegable **"Ver exactamente qué datos recibió el
modelo"** que muestra el contexto íntegro. Cualquiera puede verificar de dónde
sale una respuesta.

**Comprobado en vivo.** A la pregunta *"¿Cuántos restaurantes veganos hay y cuál
es su facturación?"* el asistente respondió que no era posible con los datos
disponibles y enumeró los dos datos que faltarían, en vez de inventarlos.

El contexto incluye una sección de **limitación conocida**: los tres restaurantes
con calificación corrupta se excluyen del ranking de peores y se le indica al
modelo que mencione la limitación si le preguntan por el peor restaurante.

### Pestaña 2 — Resumir un restaurante

Busca un restaurante y resume lo que dicen sus reseñas en un párrafo: qué
destacan, qué critican y para quién lo recomendarían. Se le envían hasta 25
reseñas reales, y se le pide explícitamente que **no invente una crítica** si las
reseñas no critican nada.

### Cuando no hay clave de API

La página **no se rompe**: detecta que falta la clave y muestra cómo obtenerla,
aclarando que el resto del proyecto funciona sin ella —el sentimiento se calcula
con léxico propio y la clasificación con scikit-learn—. El asistente es una capa
adicional, no una dependencia.

### Configuración

Crear un archivo `.env` en la raíz del proyecto:

```
GOOGLE_API_KEY=tu_clave
GEMINI_MODEL=gemini-3.5-flash
```

La clave es gratuita y se obtiene en <https://aistudio.google.com/apikey>.
`.env` está en `.gitignore`, así que no se sube al repositorio.

> **Aviso importante.** Google retira modelos para las claves nuevas sin previo
> aviso. `gemini-2.0-flash` y `gemini-2.5-flash` ya devuelven 404 o 429 aunque
> sigan apareciendo en el listado de la API. Para comprobar cuáles siguen vivos:
>
> ```bash
> python -m src.llm.modelos_disponibles
> ```
>
> Conviene ejecutarlo antes de una demostración.

---

## 11. Errores reales corregidos

Esta sección es material de defensa: son defectos que el dashboard tuvo, cómo se
detectaron y qué los causaba. Cada uno tiene test que impide su regreso.

| Página | Síntoma | Causa |
|---|---|---|
| Resumen | Los filtros no cambiaban nada | Estaban al final y solo imprimían un conteo de filas |
| Sentimiento | Todos los aspectos parecían neutros | Se contaban como neutras las reseñas que no mencionaban el aspecto |
| Sentimiento | Estado que se filtraba entre páginas | La página escribía columnas en el DataFrame de `st.cache_data`, que es compartido |
| Agrupamiento | Conteos de restaurantes inflados | Se contaban filas de reseña en vez de restaurantes únicos |
| Recomendaciones | El presupuesto no filtraba nunca | El selector ofrecía etiquetas que no existían en los datos |
| Recomendaciones | Puntuaciones no comparables | Se dividía entre el número de pesos en vez de entre los pesos aplicados |
| Detalle | El filtro de sentimiento no hacía nada | Leía una columna que nunca existía |
| Asistente | Fallaba con clave válida | El modelo configurado fue retirado por Google |

---

## 12. Reparto de trabajo con Power BI

Streamlit y Power BI **no muestran lo mismo**, a propósito. Repetir las mismas
gráficas en dos herramientas no aporta y obliga a mantener dos veces lo mismo.

| | Streamlit | Power BI |
|---|---|---|
| Sentimiento por aspecto extraído del texto | **lo produce** | consume el resultado |
| Agrupamiento K-Means | **lo produce** | consume el resultado |
| Recomendador interactivo | sí | — |
| Lectura de reseñas individuales | sí | — |
| Asistente con LLM | sí | — |
| Evolución en el tiempo | — | **sí** |
| Comparación contra un referente | — | **sí** |
| Ranking dinámico según lo filtrado | — | **sí** |
| Árbol de descomposición | — | **sí** |

En una frase: **Streamlit hace el análisis (Python, NLP, ML), Power BI hace la
exploración** de ese resultado.

El argumento más fuerte: el dashboard **no tiene ningún análisis temporal**, y el
conjunto de datos tiene fechas de 2019 a 2026. Todo ese eje quedaba sin explotar
y es exactamente lo que Power BI hace mejor.
