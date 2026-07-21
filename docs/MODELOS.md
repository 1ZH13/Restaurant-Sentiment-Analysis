# Modelos de Machine Learning

Este documento explica **qué modelos usa el proyecto, por qué se eligieron esos
y no otros, y qué resultados dan**.

El proyecto aplica tres enfoques distintos sobre el mismo problema —entender qué
opinan los clientes— y los compara entre sí:

| Enfoque | Tipo | Aprende de ejemplos |
|---|---|---|
| Léxico español | Reglas escritas a mano | No |
| K-Means | Aprendizaje **no supervisado** (clustering) | Sí, sin etiquetas |
| Regresión logística | Aprendizaje **supervisado** (clasificación) | Sí, con etiquetas |
| Gemini | Modelo de lenguaje de gran escala | Ya venía entrenado |

---

## 1. Clustering de restaurantes (K-Means)

### Qué hace

Agrupa los 241 restaurantes en perfiles similares a partir de su calificación,
su sentimiento por aspecto, su nivel de precio y su volumen de reseñas.

### Por qué K-Means y no otro algoritmo

**Por qué clustering y no clasificación:** no existe una etiqueta previa de "tipo
de restaurante". Nadie marcó cuáles son premium o cuáles destacan por servicio.
Cuando no hay etiquetas, el aprendizaje supervisado no es aplicable; el problema
es de descubrimiento de estructura, que es exactamente lo que resuelve el
clustering.

**Por qué K-Means y no jerárquico o DBSCAN:**

- **Frente al clustering jerárquico:** K-Means escala mejor y produce grupos
  planos, que es lo que necesita el dashboard. Un dendrograma sería más
  informativo pero mucho menos accionable para un usuario final.
- **Frente a DBSCAN:** DBSCAN identifica ruido y grupos de forma arbitraria,
  pero exige ajustar `eps` y `min_samples`, que son difíciles de justificar con
  241 puntos en 8 dimensiones. Además dejaría muchos restaurantes sin grupo, y
  aquí interesa que todos queden clasificados.
- **A favor de K-Means:** las variables son numéricas y continuas, los grupos
  esperados son aproximadamente esféricos en el espacio estandarizado, y el
  resultado se explica fácil: cada grupo es un centroide, es decir, un
  "restaurante promedio" de ese perfil.

### Cómo se elige el número de grupos

Se prueban valores de *k* de 2 a 9 y se escoge el de mejor **silhouette score**,
métrica que mide qué tan separados están los grupos entre sí frente a qué tan
compactos son por dentro. Va de −1 a 1.

El modelo se entrena con el *k* ganador. Esto puede sonar obvio pero no lo era:
el código original calculaba el mejor *k* y luego entrenaba con 5 fijo.

### Resultados

| | |
|---|---|
| *k* elegido | 4 |
| Silhouette | **0.17** |
| Grupos | Los más comentados · Buena relación precio · Destacan por la comida · Destacan por el ambiente |

**Sobre el silhouette de 0.17.** Es un valor bajo, y se reporta tal cual. Un
0.17 significa que los restaurantes **no forman grupos nítidamente separados**:
hay un continuo, no fronteras claras. Es un resultado honesto y bastante
esperable, porque casi todos los restaurantes del dataset tienen calificaciones
entre 4.3 y 4.9; hay poca variación de la que separar grupos.

Conviene saber que una versión anterior mostraba **0.58**, un valor mucho más
lucido pero **falso**: el clustering se hacía sobre filas de reseñas en lugar de
restaurantes, así que las 5 reseñas de un mismo restaurante eran 5 puntos
idénticos. Puntos a distancia cero inflan artificialmente la métrica. Corregirlo
bajó el número y lo volvió real.

### El cluster 3 es un artefacto de datos, no un hallazgo

Los cuatro grupos no tienen tamaños comparables:

| Grupo | Restaurantes | Reseñas | Calificación |
|---|---|---|---|
| 0 · Los más comentados | 117 | 591 | 4.38 |
| 2 · Destacan por la comida | 77 | 382 | 4.62 |
| 1 · Buena relación precio | 44 | 126 | 4.82 |
| **3 · Destacan por el ambiente** | **3** | **9** | **1.80** |

Ese grupo de 3 son **exactamente** los tres restaurantes cuya calificación de
RestaurantGuru no es fiable (ver `src/preprocessing/calidad.py` y la sección de
limitaciones del README): *Aji de Cali* (1.1), *Sushi Express Punta Pacífica*
(1.9) y *Donde Stan S.A.* (2.4). No comparten nada real entre ellos salvo el
defecto: sus reseñas son positivas y su calificación dice lo contrario.

Como la calificación es una de las ocho variables de entrada, K-Means los ve como
tres puntos aislados en un extremo del espacio y los aparta en su propio grupo. La
etiqueta *"Destacan por el ambiente"* se genera automáticamente a partir de la
variable más alta del centroide, así que **no describe nada**: es el nombre que le
tocó a un grupo que no debería existir.

**Esto también afecta a la elección de _k_.** El número de grupos se elige por
silhouette, y esos tres puntos aislados empujan la métrica hacia arriba en *k*=4
(0.1613, frente a 0.1485 en *k*=3). Es decir, el propio *k* está en parte
determinado por el defecto de datos. Con las calificaciones correctas, lo
esperable es que esos tres se fundieran en alguno de los otros grupos.

**Por qué no se corrige.** Excluirlos y volver a agrupar daría un modelo más
limpio, pero regeneraría `restaurants_clustered.csv`, que es la fuente del
dashboard de Streamlit y del modelo de Power BI. Se documenta en lugar de
maquillarse: un grupo de 3 elementos sobre 241 no cambia ninguna conclusión del
análisis, y detectar que existe por un defecto de la fuente es en sí mismo un
resultado del trabajo de calidad de datos.

**Si preguntan por el cluster 3**, la respuesta corta es: *no es un perfil de
restaurante, es el residuo de tres calificaciones corruptas de RestaurantGuru que
detectamos, documentamos y excluimos de los rankings.*

---

## 2. Clasificación supervisada de sentimiento

> Código: `src/classification/sentiment_classifier.py`
> Ejecutar: `python -m src.classification.sentiment_classifier`

### Qué hace

**Predice** si una reseña es positiva a partir de su texto. A diferencia del
clustering, que solo describe, este modelo generaliza a textos que nunca vio.

### De dónde sale la etiqueta

Este es el punto más importante del diseño. La etiqueta **no** se construye con
el analizador léxico del proyecto. Hacerlo sería circular: el modelo aprendería a
imitar al léxico, y las métricas dirían cuánto se parecen entre sí, no cuánto
aciertan.

La etiqueta sale de la **calificación en estrellas que puso el propio
reseñador**, que es un juicio humano independiente del texto:

```
positiva     = 4 o 5 estrellas
no positiva  = 1, 2 o 3 estrellas
```

Eso permite medir al léxico, al modelo y al LLM **contra la misma verdad**.

### Por qué TF-IDF + regresión logística

- **TF-IDF con bigramas** captura expresiones que invierten el sentido —"no
  recomiendo", "muy lento"— que una bolsa de palabras simple perdería.
- **Regresión logística** funciona bien con muchas características y pocos
  ejemplos, que es exactamente este caso: 973 reseñas y miles de términos. Un
  bosque aleatorio o una red neuronal se sobreajustarían con tan pocos datos.
- Además es **interpretable**: se puede leer qué palabras empujan hacia cada
  clase. Un modelo de caja negra no permitiría justificar el resultado.

### Por qué binario y no tres clases

La distribución real es:

| Estrellas | Reseñas |
|---|---|
| 5 | 618 |
| 4 | 228 |
| 3 | 108 |
| 2 | 13 |
| 1 | 6 |

Con solo **19 reseñas de 1-2 estrellas**, un modelo de tres clases nunca
aprendería a reconocer "negativa". El problema se plantea binario y se usa
`class_weight="balanced"` para penalizar más los errores en la clase rara.

### Por qué la exactitud no es la métrica principal

El 87% de las reseñas son positivas. Un modelo que **responda siempre "positiva"
acierta el 87%** y no sirve para nada. Por eso se reportan precisión,
exhaustividad y F1 de la clase minoritaria, que es la difícil y la útil.

### Resultados

Comparación justa sobre el conjunto completo (el léxico no entrena, así que no
necesita partición; el modelo se mide con validación cruzada de 5 particiones):

| Enfoque | F1 macro |
|---|---|
| Léxico | 0.618 |
| **Regresión logística** | **0.713 ± 0.020** |

Sobre una partición de prueba única (244 reseñas, 32 no positivas):

| Enfoque | Exactitud | F1 macro | F1 clase minoritaria |
|---|---|---|---|
| Léxico | 0.820 | 0.624 | 0.353 |
| Modelo | 0.832 | 0.616 | 0.328 |

**Los dos números no se contradicen: muestran varianza.** Con solo 32 casos
minoritarios en la partición de prueba, mover 3 aciertos cambia el F1 varios
puntos. Por eso la validación cruzada es la cifra a mirar, y ahí el modelo sí
supera claramente al léxico.

**AUC = 0.794.** El modelo *ordena* bien las reseñas por probabilidad de ser
negativas, aunque le cueste el corte binario. Se probó ajustar el umbral de
decisión (0.49 en vez de 0.50) con validación cruzada sobre el entrenamiento,
pero apenas cambió: `class_weight="balanced"` ya desplaza la frontera.

### Qué aprendió

| Empujan hacia positiva | Empujan hacia no positiva |
|---|---|
| excelente, deliciosa, recomendado, delicioso, recomiendo, súper | no, nada, mala, hora, embargo, pedir, estaban |

Tiene sentido: "no" y "nada" son marcadores de negación, y "hora" aparece en
quejas sobre tiempos de espera.

---

## 3. Modelo de lenguaje (Gemini)

> Código: `src/llm/asistente.py` · Página "Asistente" del dashboard

### Tres usos

1. **Consultas en lenguaje natural** sobre el conjunto de datos.
2. **Resúmenes** de lo que dicen las reseñas de un restaurante.
3. **Clasificación de sentimiento**, para compararlo con los otros dos enfoques.

### Cómo se evita que invente cifras

El modelo **no recibe las 1108 reseñas**: no cabrían y saldría caro. Se le arma un
contexto compacto (~1800 caracteres) con los agregados que ya calcula el
proyecto, y se le instruye que **diga qué dato faltaría** si la respuesta no está
en el contexto, en vez de estimarla.

La página muestra el contexto exacto que se envió, para que cualquiera pueda
verificar de dónde sale una respuesta. En un trabajo de análisis de datos, un
asistente que alucina cifras es peor que no tener asistente.

### Comparación de los tres enfoques

> Ejecutar: `python -m src.classification.comparar_enfoques --muestra 80`

Los tres se miden contra la misma verdad (las estrellas del reseñador) sobre una
muestra estratificada. El LLM se evalúa sobre una muestra y no sobre las 973
reseñas porque cada llamada consume cuota y tiempo.

Resultado sobre 60 reseñas (8 no positivas), sin clave de API configurada:

| Enfoque | Exactitud | F1 macro | F1 minoritaria |
|---|---|---|---|
| Léxico | 0.817 | 0.623 | 0.353 |
| Supervisado | 0.867 | 0.677 | 0.429 |
| LLM | *requiere clave* | | |

### Configuración

El asistente necesita una clave gratuita de Google AI Studio:

```bash
# Crear un archivo .env en la raíz del proyecto
GOOGLE_API_KEY=tu_clave_aqui
```

Se obtiene en https://aistudio.google.com/apikey

**El proyecto funciona sin la clave.** El análisis de sentimiento usa el léxico y
la clasificación usa scikit-learn; ambos corren sin conexión. El asistente es una
capa adicional y, si no hay clave, la página lo explica en lugar de fallar.

---

## 4. Por qué tres enfoques y no uno

Cada uno responde a una restricción distinta:

- El **léxico** no necesita datos etiquetados ni conexión. Es el que produce las
  columnas de sentimiento del pipeline, porque tiene que correr sobre las 1108
  reseñas de forma reproducible.
- El **modelo supervisado** aprovecha que 973 reseñas traen la calificación del
  autor, y demuestra que aprender de ejemplos supera a las reglas escritas a mano.
- El **LLM** entiende contexto y sarcasmo mucho mejor que los otros dos, pero
  depende de un servicio externo, cuesta por llamada y no es determinista. Por eso
  se usa para explorar y resumir, no para generar las columnas del pipeline.

Tenerlos los tres permite comparar y justificar la decisión, en vez de afirmar
sin evidencia que uno es mejor.
