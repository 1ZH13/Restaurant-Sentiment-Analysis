# Cómo se construyó el informe de Power BI, paso a paso

Este documento reconstruye **todo** el trabajo hecho en Power BI, en el orden en
que se hizo y con las acciones concretas de la interfaz: qué botón se pulsa, qué
campo se arrastra a qué contenedor y por qué se tomó cada decisión.

Sirve para tres cosas:

1. **Reproducir el informe desde cero** si el archivo se corrompe o se pierde.
2. **Responder en la defensa** a cualquier pregunta del tipo *"¿cómo hiciste esta
   gráfica?"* o *"¿de dónde sale ese número?"*.
3. **Auditar** que lo documentado coincide con lo que hay en los archivos.

> **Sobre el formato del proyecto.** El entregable es `Restaurantes.pbip`, un
> *proyecto* de Power BI: guarda el modelo en TMDL y el informe en JSON, ambos
> texto plano y versionables en git. Los pasos de este documento son los de la
> interfaz de Power BI Desktop y producen exactamente esos archivos. Si prefieres
> revisar el resultado sin abrir Power BI, cada paso indica qué archivo genera.

Para la referencia del modelo ya terminado (tablas, medidas, relaciones), ver
[POWERBI.md](POWERBI.md). Este documento es el *proceso*; aquel es el *resultado*.

---

## Índice

1. [Preparación previa](#1-preparación-previa)
2. [Conexión a los datos y parámetro de ruta](#2-conexión-a-los-datos-y-parámetro-de-ruta)
3. [Construcción de las tablas](#3-construcción-de-las-tablas)
4. [La tabla de calendario](#4-la-tabla-de-calendario)
5. [Relaciones: armar la estrella](#5-relaciones-armar-la-estrella)
6. [Las 30 medidas DAX](#6-las-30-medidas-dax)
7. [Página 1 — Evolución en el tiempo](#7-página-1--evolución-en-el-tiempo)
8. [Página 2 — Comparación contra el mercado](#8-página-2--comparación-contra-el-mercado)
9. [Página 3 — Dónde está el problema](#9-página-3--dónde-está-el-problema)
10. [Convenciones de maquetación](#10-convenciones-de-maquetación)
11. [Problemas encontrados y cómo se resolvieron](#11-problemas-encontrados-y-cómo-se-resolvieron)
12. [Cómo verificar que todo sigue bien](#12-cómo-verificar-que-todo-sigue-bien)

---

## 1. Preparación previa

Antes de abrir Power BI hay que tener los datos generados por el pipeline de
Python. Power BI **no procesa texto ni calcula sentimiento**: consume el
resultado.

```bash
python run_pipeline.py
```

Esto deja en `data/processed/` el archivo que alimenta todo el modelo:

| Archivo | Filas | Qué contiene |
|---|---|---|
| `restaurants_clustered.csv` | 1108 | Una fila por reseña, con las columnas del restaurante, el sentimiento por aspecto y el grupo del clustering |

**Por qué un solo CSV y no varios.** El pipeline produce varios archivos
intermedios, pero el modelo lee solo este porque es el único que tiene *todo*
junto: datos de reseña, datos de restaurante, sentimiento y clustering. Las cinco
tablas del modelo se derivan de él en Power Query. Así se garantiza que todas
comparten los mismos identificadores y no puede haber desajustes entre tablas.

Columnas relevantes del CSV:

| Grupo | Columnas |
|---|---|
| Reseña | `review_text`, `review_date`, `review_rating`, `reviewer_name`, `source`, `review_language`, `word_count`, `char_count` |
| Restaurante | `restaurant_id`, `restaurant_name`, `category`, `category_primary`, `location`, `address`, `price_band`, `price_level`, `overall_rating` |
| Sentimiento | `sentiment_comida`, `sentiment_servicio`, `sentiment_precio`, `sentiment_ambiente` (etiqueta) |
| Puntaje | `sentiment_comida_score`, `sentiment_servicio_score`, `sentiment_precio_score`, `sentiment_ambiente_score` (−1 a 1) |
| Menciones | `mentions_comida`, `mentions_servicio`, `mentions_precio`, `mentions_ambiente` (booleano) |
| Clustering | `cluster`, `cluster_name` |

---

## 2. Conexión a los datos y parámetro de ruta

### Paso 2.1 — Crear el parámetro `RutaDatos`

Power BI **no admite rutas relativas**. Si se escribe la ruta del CSV a pelo, el
proyecto solo funciona en la máquina de quien lo creó. La solución es un
parámetro que cada integrante ajusta una vez.

> *Inicio → Transformar datos → Administrar parámetros → Nuevo parámetro*

| Campo | Valor |
|---|---|
| Nombre | `RutaDatos` |
| Descripción | Carpeta con los CSV procesados del pipeline |
| Tipo | Texto |
| Requerido | Sí |
| Valor actual | `C:\Users\ZH\Desktop\Restaurant-Sentiment-Analysis\data\processed` |

**Cada integrante debe cambiar ese valor** por la ruta de su propia copia del
repositorio, apuntando a la carpeta `data/processed`.

*Archivo generado:* `Restaurantes.SemanticModel/definition/expressions.tmdl`

### Paso 2.2 — Crear la consulta base `DatosProcesados`

En vez de conectar cada tabla al CSV por separado (lo que leería el archivo cinco
veces), se crea **una consulta base** de la que derivan todas.

> *Inicio → Transformar datos → Nueva consulta → Consulta en blanco → Editor avanzado*

```m
let
    Origen = Csv.Document(
        File.Contents(RutaDatos & "\restaurants_clustered.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),
    ConIndice = Table.AddIndexColumn(Encabezados, "ReseñaID", 1, 1, Int64.Type)
in
    ConIndice
```

Tres detalles que importan:

- **`Encoding=65001`** es UTF-8. Sin esto, la ñ y los acentos de los nombres de
  restaurantes y del texto de las reseñas llegan corruptos (`Panamá` → `PanamÃ¡`).
  El CSV lo escribe Python en UTF-8.
- **`QuoteStyle=QuoteStyle.Csv`** hace que respete las comillas. El texto de las
  reseñas contiene comas; sin esto, una reseña partiría la fila en varias columnas.
- **`Table.AddIndexColumn`** crea `ReseñaID`. El CSV no trae un identificador de
  reseña, y hace falta uno para relacionar la tabla de hechos `Aspectos` con
  `Reseñas`. Se genera aquí, en la consulta base, para que **todas** las tablas
  derivadas vean el mismo identificador para la misma fila.

Marcar esta consulta como **no cargable** (clic derecho → desmarcar *Habilitar
carga*): es un paso intermedio, no una tabla del modelo.

---

## 3. Construcción de las tablas

El modelo tiene cinco tablas. Tres salen de `DatosProcesados`, una se escribe a
mano y otra es calculada en DAX.

### Paso 3.1 — `Restaurantes` (dimensión, 241 filas)

> *Nueva consulta → Consulta en blanco → Editor avanzado*

```m
let
    Columnas = Table.SelectColumns(DatosProcesados, {"restaurant_id", "restaurant_name", "category", "category_primary", "location", "address", "price_band", "price_level", "overall_rating", "cluster", "cluster_name", "source"}),
    Unicos = Table.Distinct(Columnas, {"restaurant_id"}),
    Renombrado = Table.RenameColumns(Unicos, {{"restaurant_id", "RestauranteID"}, {"restaurant_name", "Restaurante"}, {"category", "Cocina"}, {"category_primary", "CocinaPrincipal"}, {"location", "Zona"}, {"address", "Dirección"}, {"price_band", "BandaPrecio"}, {"price_level", "NivelPrecio"}, {"overall_rating", "Calificación"}, {"cluster", "GrupoID"}, {"cluster_name", "Grupo"}, {"source", "Fuente"}}),
    Tipos = Table.TransformColumnTypes(Renombrado, {{"Calificación", type number}, {"NivelPrecio", type number}, {"GrupoID", Int64.Type}})
in
    Tipos
```

**El paso clave es `Table.Distinct`.** El CSV tiene una fila por *reseña*, así
que un restaurante con 5 reseñas aparece 5 veces. Sin deduplicar, la dimensión
tendría 1108 filas y los conteos de restaurantes saldrían inflados. Con
`Table.Distinct` sobre `restaurant_id` quedan las 241 reales.

**Por qué se renombra todo al español.** Los nombres de columna se ven en los
paneles de campos, en los tooltips y en los títulos automáticos de los visuales.
Dejarlos como `category_primary` obliga a renombrar cada visual a mano; hacerlo
una vez en Power Query lo arregla en todo el informe.

### Paso 3.2 — `Reseñas` (hechos, 1108 filas)

```m
let
    Columnas = Table.SelectColumns(DatosProcesados, {"ReseñaID", "restaurant_id", "review_date", "review_rating", "review_text", "reviewer_name", "source", "review_language", "word_count", "char_count"}),
    Renombrado = Table.RenameColumns(Columnas, {{"restaurant_id", "RestauranteID"}, {"review_date", "Fecha"}, {"review_rating", "CalificaciónReseña"}, {"review_text", "Texto"}, {"reviewer_name", "Autor"}, {"source", "Fuente"}, {"review_language", "Idioma"}, {"word_count", "Palabras"}, {"char_count", "Caracteres"}}),
    Tipos = Table.TransformColumnTypes(Renombrado, {{"Fecha", type date}, {"CalificaciónReseña", type number}, {"Palabras", Int64.Type}, {"Caracteres", Int64.Type}})
in
    Tipos
```

Aquí **no** se deduplica: cada fila es una reseña y todas cuentan.

`Fecha` se convierte a tipo `date` (no `datetime`) porque la relación con
`Calendario` se hace por día. Si quedara como texto, la relación no se puede
crear y toda la inteligencia de tiempo deja de funcionar.

### Paso 3.3 — `Aspectos` (hechos despivotados, 4432 filas)

Esta es **la tabla más importante del modelo** y la que hace posible casi todo el
informe. Merece la explicación completa.

**El problema.** El CSV tiene el sentimiento en columnas separadas:
`sentiment_comida`, `sentiment_servicio`, `sentiment_precio`,
`sentiment_ambiente`. Con esa forma, para hacer una gráfica de "sentimiento por
aspecto" habría que crear cuatro medidas distintas y ponerlas una al lado de otra
— y no se podría segmentar por aspecto, ni usar el aspecto como eje, ni como
serie de una línea.

**La solución: despivotar.** Convertir esas cuatro columnas en filas, de modo que
cada reseña genere **cuatro filas**, una por aspecto. 1108 reseñas × 4 aspectos =
**4432 filas**.

| ReseñaID | Aspecto | Sentimiento | Puntaje | Mencionado |
|---|---|---|---|---|
| 1 | Comida | Positivo | 0.8 | TRUE |
| 1 | Servicio | Negativo | −0.6 | TRUE |
| 1 | Precio | Neutral | 0.0 | FALSE |
| 1 | Ambiente | Positivo | 0.4 | TRUE |

Con esta forma, `Aspecto` pasa a ser **un campo más**: se puede poner en un eje,
en una leyenda, en un segmentador o en un árbol de descomposición. Una sola
medida (`Sentimiento promedio`) sirve para los cuatro aspectos.

```m
let
    PorAspecto = (nombre as text, colEtiqueta as text, colPuntaje as text, colMencion as text) as table =>
        let
            Sel = Table.SelectColumns(DatosProcesados, {"ReseñaID", "restaurant_id", "review_date", colEtiqueta, colPuntaje, colMencion}),
            Ren = Table.RenameColumns(Sel, {{"restaurant_id", "RestauranteID"}, {"review_date", "Fecha"}, {colEtiqueta, "Sentimiento"}, {colPuntaje, "Puntaje"}, {colMencion, "Mencionado"}}),
            Con = Table.AddColumn(Ren, "Aspecto", each nombre, type text)
        in
            Con,
    Todos = Table.Combine({
        PorAspecto("Comida", "sentiment_comida", "sentiment_comida_score", "mentions_comida"),
        PorAspecto("Servicio", "sentiment_servicio", "sentiment_servicio_score", "mentions_servicio"),
        PorAspecto("Precio", "sentiment_precio", "sentiment_precio_score", "mentions_precio"),
        PorAspecto("Ambiente", "sentiment_ambiente", "sentiment_ambiente_score", "mentions_ambiente")
    }),
    Etiquetas = Table.TransformColumns(Todos, {{"Sentimiento", each if _ = "positive" then "Positivo" else if _ = "negative" then "Negativo" else "Neutral", type text}}),
    Logico = Table.TransformColumns(Etiquetas, {{"Mencionado", each _ = "True", type logical}}),
    Tipos = Table.TransformColumnTypes(Logico, {{"Puntaje", type number}, {"Fecha", type date}}),
    Orden = Table.SelectColumns(Tipos, {"ReseñaID", "RestauranteID", "Fecha", "Aspecto", "Sentimiento", "Puntaje", "Mencionado"})
in
    Orden
```

Detalles a defender:

- **`PorAspecto` es una función.** En lugar de escribir cuatro bloques casi
  idénticos, se define una función que recibe el nombre del aspecto y sus tres
  columnas, y se la llama cuatro veces. Si mañana se añade un quinto aspecto, es
  una línea más.
- **`Table.Combine`** apila los cuatro resultados. Es el equivalente a un
  `UNION ALL` en SQL.
- **Traducción de etiquetas.** El pipeline de Python escribe `positive` /
  `negative` / `neutral`. Se traducen a `Positivo` / `Negativo` / `Neutral`
  porque se muestran directamente en los visuales y el informe está en español.
- **`Mencionado` a booleano.** El CSV trae el texto `"True"` / `"False"`. Se
  convierte a lógico real para poder filtrar con `= TRUE()` en DAX.
- **`RestauranteID` y `Fecha` se arrastran hasta aquí** a propósito. Podrían
  obtenerse navegando `Aspectos → Reseñas → Restaurantes`, pero eso sería un
  **copo de nieve**, no una estrella. Trayendo las claves a la tabla de hechos,
  `Aspectos` apunta *directamente* a sus tres dimensiones.

### Paso 3.4 — `Aspecto` (dimensión, 4 filas)

Una tabla escrita a mano, sin origen externo:

```m
let
    Origen = #table(
        type table [Aspecto = text, Orden = Int64.Type, Descripcion = text],
        {
            {"Comida", 1, "Calidad, sabor y presentacion de los platos"},
            {"Servicio", 2, "Atencion del personal, rapidez y trato"},
            {"Precio", 3, "Relacion entre lo que se paga y lo que se recibe"},
            {"Ambiente", 4, "Local, decoracion, ruido y comodidad"}
        })
in
    Origen
```

**¿Por qué una dimensión de 4 filas si `Aspectos` ya tiene la columna `Aspecto`?**

Por tres razones concretas:

1. **Orden.** Sin esta tabla, los visuales listan los aspectos alfabéticamente:
   Ambiente, Comida, Precio, Servicio. Con la columna `Orden` (y configurando
   *Ordenar por columna*), salen en el orden lógico del análisis: Comida,
   Servicio, Precio, Ambiente.
2. **Segmentador limpio.** Un segmentador sobre la columna de la tabla de hechos
   funciona, pero recorre 4432 filas para obtener 4 valores distintos. Sobre la
   dimensión lee 4 filas.
3. **Descripción.** Da un sitio donde documentar qué significa cada aspecto, y se
   puede mostrar en un tooltip.

Es el mismo motivo por el que existe `Calendario` en vez de usar la fecha de la
tabla de hechos: **las dimensiones se separan aunque parezcan redundantes.**

*Después de crear las tablas:* **Cerrar y aplicar**.

---

## 4. La tabla de calendario

`Calendario` no es una consulta de Power Query: es una **tabla calculada en DAX**.

> *Modelado → Nueva tabla*

```dax
Calendario =
VAR FechaMinima = MIN('Reseñas'[Fecha])
VAR FechaMaxima = MAX('Reseñas'[Fecha])
VAR AnioInicio = IF(ISBLANK(FechaMinima), 2019, YEAR(FechaMinima))
VAR AnioFin = IF(ISBLANK(FechaMaxima), YEAR(TODAY()), YEAR(FechaMaxima))
RETURN
ADDCOLUMNS(
    CALENDAR(DATE(AnioInicio, 1, 1), DATE(AnioFin, 12, 31)),
    "Año", YEAR([Date]),
    "NúmeroMes", MONTH([Date]),
    "Mes", FORMAT([Date], "MMMM", "es-ES"),
    "AñoMes", FORMAT([Date], "yyyy-MM"),
    "Trimestre", "T" & FORMAT([Date], "Q"),
    "AñoTrimestre", FORMAT([Date], "yyyy") & "-T" & FORMAT([Date], "Q")
)
```

**Por qué hace falta una tabla de fechas.** Las funciones de inteligencia de
tiempo de DAX (`DATEADD`, `SAMEPERIODLASTYEAR`, `DATESINPERIOD`) exigen una tabla
de fechas **continua**: un día por fila, sin huecos. La columna `Fecha` de
`Reseñas` tiene huecos —hay días sin ninguna reseña— así que no sirve. Sin esta
tabla, la mitad de las medidas de la Página 1 no se podrían escribir.

**El bloque de `IF(ISBLANK(...))` no es decorativo.** Al abrir el proyecto por
primera vez, o tras limpiar la caché, `Reseñas` todavía no tiene datos cargados
cuando se evalúa la tabla calculada. En ese momento `MIN` y `MAX` devuelven vacío,
y `DATE(YEAR(BLANK()), 1, 1)` produce una fecha inválida que hace fallar la tabla
entera —y con ella, todas las relaciones y medidas que dependen de ella. Los
valores de reserva (2019 y el año actual) cubren el rango real del dataset y
quedan sustituidos en cuanto se actualiza. **Este fue un error real que rompía el
proyecto al abrirlo en otra máquina.**

Después de crearla:

> *Seleccionar la tabla → Herramientas de tabla → Marcar como tabla de fechas → columna `Date`*

Esto le dice a Power BI que es la dimensión temporal oficial del modelo.

---

## 5. Relaciones: armar la estrella

> *Modelado → Administrar relaciones*, o arrastrando campos en la vista *Modelo*.

Se crean cinco relaciones, todas de **uno a varios** (la dimensión es el lado
*uno*, la tabla de hechos el lado *varios*) y con **dirección de filtro simple**
(de la dimensión hacia los hechos):

| # | Desde (varios) | Hacia (uno) |
|---|---|---|
| 1 | `Reseñas[RestauranteID]` | `Restaurantes[RestauranteID]` |
| 2 | `Reseñas[Fecha]` | `Calendario[Date]` |
| 3 | `Aspectos[RestauranteID]` | `Restaurantes[RestauranteID]` |
| 4 | `Aspectos[Fecha]` | `Calendario[Date]` |
| 5 | `Aspectos[Aspecto]` | `Aspecto[Aspecto]` |

El resultado es este esquema:

```
        Restaurantes            Calendario           Aspecto
         (241 filas)             (dimensión)        (4 filas)
              │                       │                  │
        ┌─────┴─────┐           ┌─────┴─────┐            │
        ▼           ▼           ▼           ▼            ▼
     Reseñas ────────────────────         Aspectos ───────
    (1108 filas)                        (4432 filas)
```

**Por qué esto es una estrella y no un copo de nieve.** Cada tabla de hechos
apunta *directamente* a sus dimensiones. Ninguna dimensión cuelga de otra
dimensión. `Restaurantes` y `Calendario` son **dimensiones conformadas**: las
comparten las dos tablas de hechos, de modo que un segmentador de `Zona` filtra a
la vez `Reseñas` y `Aspectos` sin necesidad de relaciones cruzadas.

**Por qué dirección simple y no bidireccional.** El filtro bidireccional parece
cómodo pero genera ambigüedad cuando hay dos caminos entre dos tablas —que es
justo el caso aquí: `Restaurantes` llega a `Aspectos` directamente y también
podría llegar vía `Reseñas`. Con dirección simple, el camino es único y
determinista.

*Archivo generado:* `Restaurantes.SemanticModel/definition/relationships.tmdl`

---

## 6. Las 30 medidas DAX

Se crean con *Herramientas de tabla → Nueva medida*. Están organizadas en
**carpetas de visualización** (propiedad *Carpeta de presentación* en el panel de
propiedades de cada medida) para que el panel de campos no sea una lista plana de
treinta elementos.

Las medidas se alojan en la tabla de hechos con la que se corresponden:
`Reseñas` para las de volumen y tiempo, `Aspectos` para las de sentimiento.

### Carpeta `1 Base` — en `Reseñas`

```dax
Total reseñas = COUNTROWS('Reseñas')

Total restaurantes = DISTINCTCOUNT('Reseñas'[RestauranteID])

Calificación promedio = AVERAGE('Reseñas'[CalificaciónReseña])

Reseñas con calificación =
COUNTROWS(FILTER('Reseñas', NOT ISBLANK('Reseñas'[CalificaciónReseña])))

Palabras por reseña = AVERAGE('Reseñas'[Palabras])
```

`Reseñas con calificación` existe para poder **declarar la cobertura**: solo
Degusta publica la nota individual de cada reseña, así que `Calificación
promedio` no se apoya en las 1108 filas sino en el 88% de ellas. Poner las dos
medidas juntas evita presentar un promedio sin decir sobre cuántos casos se
calcula.

### Carpeta `2 Sentimiento` — en `Aspectos`

```dax
Sentimiento promedio =
CALCULATE(AVERAGE(Aspectos[Puntaje]), Aspectos[Mencionado] = TRUE())

Menciones =
CALCULATE(COUNTROWS(Aspectos), Aspectos[Mencionado] = TRUE())

Cobertura de menciones = DIVIDE([Menciones], COUNTROWS(Aspectos))

Menciones positivas =
CALCULATE(COUNTROWS(Aspectos), Aspectos[Mencionado] = TRUE(), Aspectos[Sentimiento] = "Positivo")

Menciones negativas =
CALCULATE(COUNTROWS(Aspectos), Aspectos[Mencionado] = TRUE(), Aspectos[Sentimiento] = "Negativo")

% positivas = DIVIDE([Menciones positivas], [Menciones])

% negativas = DIVIDE([Menciones negativas], [Menciones])

Saldo de opinión = [% positivas] - [% negativas]

Restaurantes con quejas =
CALCULATE(DISTINCTCOUNT(Aspectos[RestauranteID]), Aspectos[Mencionado] = TRUE(), Aspectos[Sentimiento] = "Negativo")
```

**El filtro `Mencionado = TRUE()` es la decisión más importante de todo el
modelo.** Si una reseña no habla del precio, su puntaje de precio es 0. Promediar
esos ceros arrastraría todos los promedios hacia el centro y daría una lectura
falsa: parecería que el precio genera indiferencia, cuando en realidad *no se
menciona*. Con el filtro, `Sentimiento promedio` de Precio se calcula solo sobre
las 240 reseñas que efectivamente hablan de precio.

Ese es también el motivo de que exista `Cobertura de menciones`: al lado de
cualquier promedio hay que poder decir sobre qué proporción de reseñas se apoya.

**`DIVIDE` en lugar de `/`.** `DIVIDE` devuelve vacío al dividir por cero en
lugar de un error. Con segmentadores que pueden dejar una selección sin
menciones, la división directa rompería el visual.

### Carpeta `3 Tiempo` — en `Reseñas` y `Aspectos`

Estas son las medidas que **justifican la existencia del informe de Power BI**:
el dashboard de Streamlit no tiene ningún análisis temporal, y el dataset abarca
de 2019 a 2026.

```dax
Reseñas mes anterior =
CALCULATE([Total reseñas], DATEADD(Calendario[Date], -1, MONTH))

Variación mensual =
VAR Actual = [Total reseñas]
VAR Previo = [Reseñas mes anterior]
RETURN IF(NOT ISBLANK(Previo) && Previo <> 0, DIVIDE(Actual - Previo, Previo))

Reseñas año anterior =
CALCULATE([Total reseñas], SAMEPERIODLASTYEAR(Calendario[Date]))

Reseñas acumuladas =
CALCULATE([Total reseñas], FILTER(ALL(Calendario), Calendario[Date] <= MAX(Calendario[Date])))

Media móvil 3 meses =
AVERAGEX(DATESINPERIOD(Calendario[Date], MAX(Calendario[Date]), -3, MONTH), [Total reseñas])

% del total de reseñas =
DIVIDE([Total reseñas], CALCULATE([Total reseñas], ALLSELECTED()))

Sentimiento mes anterior =
CALCULATE([Sentimiento promedio], DATEADD(Calendario[Date], -1, MONTH))

Cambio de sentimiento =
VAR Actual = [Sentimiento promedio]
VAR Previo = [Sentimiento mes anterior]
RETURN IF(NOT ISBLANK(Previo), Actual - Previo)
```

**El patrón `IF(NOT ISBLANK(Previo), ...)` se repite a propósito.** En el primer
mes de la serie no existe "mes anterior". Sin la comprobación, la variación
saldría como −100% o como un valor sin sentido en vez de quedar en blanco. Un
gráfico que empieza con una caída falsa del 100% es peor que uno que empieza
vacío.

**`ALLSELECTED` en `% del total`** hace que el porcentaje se calcule sobre lo que
el usuario tiene filtrado, no sobre el total absoluto. Si se filtra por cocina
italiana, cada mes muestra su peso *dentro de la italiana*.

### Carpeta `4 Comparación` — en `Aspectos`

```dax
Sentimiento de su cocina =
CALCULATE([Sentimiento promedio], ALLEXCEPT(Restaurantes, Restaurantes[CocinaPrincipal]))

Diferencia vs su cocina = [Sentimiento promedio] - [Sentimiento de su cocina]

Sentimiento de su zona =
CALCULATE([Sentimiento promedio], ALLEXCEPT(Restaurantes, Restaurantes[Zona]))

Diferencia vs su zona = [Sentimiento promedio] - [Sentimiento de su zona]

Ranking por sentimiento =
IF(NOT ISBLANK([Sentimiento promedio]),
   RANKX(ALLSELECTED(Restaurantes[Restaurante]), [Sentimiento promedio], , DESC, DENSE))
```

**`ALLEXCEPT` es el corazón de esta página.** Quita todos los filtros de
`Restaurantes` *excepto* el de cocina. Traducido: estando en la fila de un
restaurante concreto, calcula el sentimiento de **todos** los restaurantes que
comparten su cocina. Así `Diferencia vs su cocina` responde a *"¿este restaurante
está por encima o por debajo de sus pares?"*, que es una pregunta mucho más útil
que *"¿cuál es su sentimiento absoluto?"*.

Un 0.65 no dice nada por sí solo. Un +0.12 sobre la media de su cocina sí.

**`RANKX` con `ALLSELECTED`** hace el ranking dinámico: se recalcula sobre lo que
queda tras aplicar los segmentadores. Si se filtra a comida italiana, el ranking
pasa a ser *dentro de* la italiana. El `IF(NOT ISBLANK(...))` evita que los
restaurantes sin menciones aparezcan empatados en el último puesto.

### Carpeta `5 Desbalance` — en `Aspectos`

```dax
Brecha entre aspectos =
VAR Tabla = ADDCOLUMNS(VALUES(Aspectos[Aspecto]), "@S", [Sentimiento promedio])
VAR Validos = FILTER(Tabla, NOT ISBLANK([@S]))
VAR Mejor = MAXX(Validos, [@S])
VAR Peor = MINX(Validos, [@S])
RETURN IF(COUNTROWS(Validos) > 1, Mejor - Peor)

Mejor aspecto =
VAR Tabla = ADDCOLUMNS(VALUES(Aspectos[Aspecto]), "@S", [Sentimiento promedio])
VAR Validos = FILTER(Tabla, NOT ISBLANK([@S]))
VAR Maximo = MAXX(Validos, [@S])
RETURN CONCATENATEX(FILTER(Validos, [@S] = Maximo), Aspectos[Aspecto], ", ")

Peor aspecto =
VAR Tabla = ADDCOLUMNS(VALUES(Aspectos[Aspecto]), "@S", [Sentimiento promedio])
VAR Validos = FILTER(Tabla, NOT ISBLANK([@S]))
VAR Minimo = MINX(Validos, [@S])
RETURN CONCATENATEX(FILTER(Validos, [@S] = Minimo), Aspectos[Aspecto], ", ")
```

Estas tres responden a una pregunta de negocio concreta: **¿qué restaurantes son
desparejos?** Un local con la comida excelente y el servicio pésimo tiene un
promedio decente que oculta el problema. `Brecha entre aspectos` lo expone.

Cómo funcionan, paso a paso:

1. `ADDCOLUMNS(VALUES(Aspectos[Aspecto]), "@S", [Sentimiento promedio])` construye
   una tabla virtual de 4 filas —una por aspecto— con el sentimiento de cada uno
   *en el contexto de filtro actual*, es decir, del restaurante de esa fila.
2. `FILTER(..., NOT ISBLANK([@S]))` descarta los aspectos que ese restaurante no
   tiene mencionados. Sin esto, un aspecto sin datos contaría como 0 y produciría
   brechas falsas.
3. `MAXX` / `MINX` recorren la tabla virtual y sacan el extremo.
4. `COUNTROWS(Validos) > 1` evita calcular una brecha cuando solo hay un aspecto
   válido: la brecha de un solo elemento no significa nada.
5. `CONCATENATEX` devuelve el **nombre** del aspecto, no el número. Y como filtra
   por `[@S] = Maximo`, si hay empate devuelve los dos separados por coma, en vez
   de elegir uno arbitrariamente.

---

## 7. Página 1 — Evolución en el tiempo

> *Nueva página*. Tamaño del lienzo: **1280 × 720** (*Formato de página → Tamaño
> del lienzo → Personalizado*).

**Qué responde esta página:** ¿cómo evolucionó el conjunto de datos y la
percepción a lo largo del tiempo? Es el eje que el dashboard de Streamlit no
cubre en absoluto.

### Fila superior — tres tarjetas y un segmentador

| Visual | Tipo | Posición | Campo |
|---|---|---|---|
| `tarjetaTotalResenas` | Tarjeta | x=16, y=16, 240×110 | *Campos:* `Total reseñas` |
| `tarjetaTotalRestaurantes` | Tarjeta | x=272, y=16, 240×110 | *Campos:* `Total restaurantes` |
| `tarjetaVariacion` | Tarjeta | x=528, y=16, 240×110 | *Campos:* `Variación mensual` |
| `segmentadorAno` | Segmentación | x=1024, y=16, 240×110 | *Campo:* `Calendario[Año]` |

Pasos para cada tarjeta:

1. *Insertar → Tarjeta* (o icono de tarjeta en el panel de visualizaciones).
2. Arrastrar la medida al contenedor **Campos**.
3. Colocar y dimensionar en *Formato → General → Propiedades*.
4. Poner el título en *Formato → General → Título → Texto*.

El segmentador de `Año` se coloca **a la derecha, separado de las tarjetas**
(x=1024, dejando un hueco desde x=768). Es una convención de las tres páginas:
los controles van siempre en el mismo sitio, así el usuario no los busca al
cambiar de página.

### Fila media — dos gráficas

**`lineaVolumenMensual`** — Gráfico de líneas, x=16, y=142, 620×280
Título: *Reseñas por mes y su tendencia*

| Contenedor | Campo |
|---|---|
| Eje X | `Calendario[AñoMes]` |
| Eje Y | `Total reseñas` |
| Eje Y | `Media móvil 3 meses` |

Dos series en el mismo eje a propósito: la línea cruda es irregular y la media
móvil deja ver la tendencia por debajo del ruido. Es la lectura correcta cuando
el volumen mensual es pequeño y salta mucho.

**`areaAcumulado`** — Gráfico de área, x=652, y=142, 612×280
Título: *Cómo fue creciendo el conjunto de datos*

| Contenedor | Campo |
|---|---|
| Eje X | `Calendario[AñoMes]` |
| Eje Y | `Reseñas acumuladas` |

El área acumulada muestra el crecimiento del corpus. Sirve para explicar de un
vistazo que los datos no están repartidos de forma pareja en el tiempo.

### Fila inferior — sentimiento por aspecto

**`lineaSentimientoAspecto`** — Gráfico de líneas, x=16, y=438, 1248×266
Título: *Evolución del sentimiento por aspecto*

| Contenedor | Campo |
|---|---|
| Eje X | `Calendario[AñoMes]` |
| Leyenda | `Aspecto[Aspecto]` |
| Eje Y | `Sentimiento promedio` |

**Aquí se ve el pago de haber despivotado.** Poner `Aspecto[Aspecto]` en la
leyenda produce las cuatro líneas automáticamente, con una sola medida. Con el
formato original en columnas habría hecho falta crear cuatro medidas y añadirlas
una a una — y no se podrían filtrar con un segmentador.

Nótese que la leyenda usa la columna de la **dimensión** `Aspecto`, no la de la
tabla de hechos. Así respeta el orden Comida → Servicio → Precio → Ambiente.

> **Nota para la defensa.** Las fechas se concentran en los meses recientes
> porque Degusta solo publica las 5 reseñas más nuevas de cada restaurante. La
> serie temporal es real, pero su densidad no es uniforme. Conviene decirlo antes
> de que lo pregunten.

---

## 8. Página 2 — Comparación contra el mercado

**Qué responde:** ¿cómo se sitúa cada restaurante frente a sus pares? Ningún
número absoluto de sentimiento significa gran cosa; comparado con su cocina o su
zona, sí.

### Fila superior — tres segmentadores y una tarjeta

| Visual | Tipo | Posición | Campo |
|---|---|---|---|
| `segmentadorCocina` | Segmentación | x=16, y=16, 240×110 | `Restaurantes[CocinaPrincipal]` |
| `segmentadorBanda` | Segmentación | x=272, y=16, 240×110 | `Restaurantes[BandaPrecio]` |
| `segmentadorZona` | Segmentación | x=528, y=16, 240×110 | `Restaurantes[Zona]` |
| `tarjetaRankingTotal` | Tarjeta | x=1024, y=16, 240×110 | `Total restaurantes` |

La tarjeta de la derecha muestra **cuántos restaurantes quedan tras filtrar**. Es
una salvaguarda contra la lectura ingenua: si los segmentadores dejan 3
restaurantes, cualquier conclusión de la página vale poco, y el número lo hace
evidente.

### Fila media

**`matrizComparativa`** — Matriz, x=16, y=142, 752×280
Título: *Cada restaurante frente al promedio de su cocina*

| Contenedor | Campo |
|---|---|
| Filas | `Restaurantes[Restaurante]` |
| Valores | `Sentimiento promedio` |
| Valores | `Sentimiento de su cocina` |
| Valores | `Diferencia vs su cocina` |
| Valores | `Ranking por sentimiento` |
| Valores | `Total reseñas` |

Las cinco columnas cuentan una historia completa en una sola fila: cuánto tiene
este restaurante, cuánto tienen sus pares, la diferencia, su puesto y —
crucialmente— **sobre cuántas reseñas se apoya todo eso**.

**Se usa una matriz y no una tabla** porque la matriz respeta el contexto de
filtro de las medidas al agrupar por fila, que es lo que necesitan `ALLEXCEPT` y
`RANKX` para calcularse por restaurante.

**`barrasDiferenciaCocina`** — Barras agrupadas, x=784, y=142, 480×280
Título: *Quiénes se despegan más de sus pares*

| Contenedor | Campo |
|---|---|
| Eje Y | `Restaurantes[Restaurante]` |
| Eje X | `Diferencia vs su cocina` |

Es la lectura visual de la columna de diferencia de la matriz. Al ser una medida
que puede ser negativa, las barras salen a ambos lados del cero, y se leen de un
golpe los que destacan y los que se quedan cortos.

### Fila inferior

**`matrizZonaAspecto`** — Matriz, x=16, y=438, 752×266
Título: *Sentimiento por zona y aspecto*

| Contenedor | Campo |
|---|---|
| Filas | `Restaurantes[Zona]` |
| Columnas | `Aspecto[Aspecto]` |
| Valores | `Sentimiento promedio` |

Una matriz cruzada zona × aspecto. Con el **formato condicional** activado
(*Formato → Elementos de celda → Color de fondo*) se convierte en un mapa de
calor: se detecta de un vistazo si alguna zona tiene un problema sistemático con
algún aspecto.

**`dispersionVolumen`** — Dispersión, x=784, y=438, 480×266
Título: *¿Los que destacan tienen suficientes reseñas?*

| Contenedor | Campo |
|---|---|
| Detalles | `Restaurantes[Restaurante]` |
| Eje X | `Diferencia vs su cocina` |
| Eje Y | `Total reseñas` |

**Este visual existe para responder a una objeción antes de que la hagan.** Un
restaurante puede aparecer como el que más se despega de su cocina simplemente
porque tiene 3 reseñas. Cruzar la diferencia contra el volumen deja ver de
inmediato qué puntos son confiables: los de arriba a la derecha destacan *y*
tienen respaldo; los de abajo son ruido.

---

## 9. Página 3 — Dónde está el problema

**Qué responde:** de las críticas que hay, ¿dónde se concentran? Es la página de
diagnóstico.

### Fila superior

| Visual | Tipo | Posición | Campo |
|---|---|---|---|
| `tarjetaQuejas` | Tarjeta | x=16, y=16, 240×110 | `Restaurantes con quejas` |
| `tarjetaCobertura` | Tarjeta | x=272, y=16, 240×110 | `Cobertura de menciones` |
| `barrasNegativas` | Columnas agrupadas | x=528, y=16, 480×110 | Eje: `Aspecto[Aspecto]` · Valor: `% negativas` |
| `segmentadorAspecto` | Segmentación | x=1024, y=16, 240×110 | `Aspecto[Aspecto]` |

`barrasNegativas` usa **`% negativas` y no `Menciones negativas`** a propósito.
El conteo bruto favorecería siempre a Comida, que es el aspecto más mencionado
(1014 menciones frente a 240 de Precio). El porcentaje normaliza y permite
comparar aspectos con volúmenes muy distintos.

### Fila media

**`tablaDesbalance`** — Matriz, x=16, y=142, 752×280
Título: *Restaurantes desparejos: su mejor y su peor aspecto*

| Contenedor | Campo |
|---|---|
| Filas | `Restaurantes[Restaurante]` |
| Valores | `Mejor aspecto` |
| Valores | `Peor aspecto` |
| Valores | `Brecha entre aspectos` |
| Valores | `Total reseñas` |

Aquí se materializan las tres medidas de la carpeta *5 Desbalance*. Ordenando por
`Brecha entre aspectos` de mayor a menor salen arriba los restaurantes más
desparejos. `Total reseñas` va al final, otra vez, para poder descartar los casos
con base insuficiente.

> **Nota histórica.** Este visual empezó siendo una tabla y se cambió a matriz.
> Con una tabla, las medidas `Mejor aspecto` y `Peor aspecto` se evaluaban sin
> contexto de fila y devolvían el mismo valor para todos los restaurantes. La
> matriz agrupa por `Restaurante` y les da el contexto que necesitan.

**`matrizCocinaSaldo`** — Matriz, x=784, y=142, 480×280
Título: *Saldo de opinión por cocina y aspecto*

| Contenedor | Campo |
|---|---|
| Filas | `Restaurantes[CocinaPrincipal]` |
| Columnas | `Aspecto[Aspecto]` |
| Valores | `Saldo de opinión` |

`Saldo de opinión` (= % positivas − % negativas) va de −1 a +1 y es más legible
que dos porcentajes por separado. Con formato condicional divergente
(rojo–blanco–verde) el cruce cocina × aspecto se lee como un mapa de calor.

### Fila inferior

**`arbolDescomposicion`** — Árbol de descomposición, x=16, y=438, 1248×266
Título: *De dónde vienen las menciones negativas*

| Contenedor | Campo |
|---|---|
| Analizar | `Menciones negativas` |
| Explicar por | `Restaurantes[Zona]` |
| Explicar por | `Restaurantes[CocinaPrincipal]` |
| Explicar por | `Restaurantes[BandaPrecio]` |
| Explicar por | `Aspecto[Aspecto]` |

Formato: *Árbol → Barras por nivel = 3*.

**Cómo se usa.** El árbol arranca **colapsado**, mostrando solo la raíz con el
total (80 menciones negativas). Es interactivo por diseño: al pulsar el `+` junto
a un nodo se elige por cuál de los cuatro campos descomponer, y se pueden encadenar
niveles (por ejemplo Zona → Aspecto → Cocina). Con *barras por nivel = 3*, cada
expansión muestra las tres categorías con más menciones negativas.

**Por qué este visual.** Es el único de todo el proyecto que hace *análisis
exploratorio guiado*: en vez de fijar una jerarquía de antemano, deja que quien
mira decida el camino. Cumple el requisito de "visual de IA" del informe y no
tiene equivalente en Streamlit.

> **Nota honesta para la defensa.** Hay 80 menciones negativas sobre 2661 totales
> (3%). Al abrir por Zona, las ramas quedan en números de un dígito. El árbol
> sirve para ver **dónde se concentran** las pocas críticas que hay, no para
> afirmar tendencias sólidas por zona. El sesgo positivo de las reseñas
> publicadas está documentado en las limitaciones del README.

---

## 10. Convenciones de maquetación

Las tres páginas siguen la misma retícula, y no por capricho: una posición
estable reduce el esfuerzo de lectura al cambiar de página.

| Elemento | Regla |
|---|---|
| Lienzo | 1280 × 720 |
| Margen exterior | 16 px |
| Fila superior (KPIs y controles) | y=16, alto 110 |
| Fila media | y=142, alto 280 |
| Fila inferior | y=438, alto 266 |
| Ancho de tarjeta / segmentador | 240 |
| Separación horizontal | 16 px (x = 16, 272, 528, 784, 1024) |
| Segmentadores principales | siempre a la derecha, x=1024 |
| Títulos | tamaño 11, activados en los 22 visuales |

Tres reglas de contenido que se aplicaron en todas las páginas:

1. **Todo promedio va acompañado de su cobertura.** Junto a cualquier
   `Sentimiento promedio` hay un `Total reseñas`, `Menciones` o `Cobertura de
   menciones`. El mismo criterio que sigue el dashboard de Streamlit.
2. **No duplicar Streamlit.** Antes de añadir un visual se comprueba que no
   repita algo que el dashboard ya hace mejor. Power BI aporta tiempo,
   comparación contra referente, ranking dinámico y exploración; Streamlit aporta
   el NLP, el ML y la lectura de reseñas individuales.
3. **Los rankings avisan de su base.** Ningún ranking se presenta sin la columna
   de volumen al lado.

---

## 11. Problemas encontrados y cómo se resolvieron

Esta sección es material directo de defensa: son errores reales del desarrollo y
cómo se diagnosticaron.

### 11.1 — Los títulos de los visuales no se mostraban

**Síntoma.** Los 22 visuales tenían su título definido en el JSON, pero el
informe los mostraba sin título.

**Causa.** El título estaba escrito bajo `visual.objects.title`. En el formato
PBIR, `objects` contiene el formato *propio del tipo de visual* (ejes, leyendas,
puntos de datos); el marco del contenedor —título, subtítulo, fondo, borde— va en
**`visualContainerObjects`**. Una propiedad de contenedor colocada en `objects`
se **ignora en silencio**: no da error, simplemente no se aplica.

**Solución.** Mover el bloque completo de `objects` a `visualContainerObjects` en
los 22 archivos. La forma interna de la propiedad ya era correcta:

```json
"visualContainerObjects": {
  "title": [{
    "properties": {
      "show":     {"expr": {"Literal": {"Value": "true"}}},
      "text":     {"expr": {"Literal": {"Value": "'Restaurantes con quejas'"}}},
      "fontSize": {"expr": {"Literal": {"Value": "11D"}}}
    }
  }]
}
```

**Lección.** JSON válido no garantiza que el visual lo use. Al editar los
archivos a mano hay que verificar la clave exacta contra el esquema declarado en
`$schema`, no suponerla.

### 11.2 — La tabla `Aspecto` no estaba registrada en el modelo

**Síntoma.** La tabla `Aspecto` tenía su archivo `.tmdl` y hasta una relación
declarada (`Aspecto_Aspectos`), pero al abrir el proyecto Power BI la añadía sola
y marcaba el archivo como modificado.

**Causa.** Una edición manual de TMDL creó `tables/Aspecto.tmdl` y la relación,
pero no añadió `ref table Aspecto` en `model.tmdl` ni la incluyó en la anotación
`PBI_QueryOrder`. Para el modelo, la tabla no existía.

**Solución.** Registrarla en `model.tmdl`:

```tmdl
annotation PBI_QueryOrder = ["Restaurantes","Reseñas","Aspectos","RutaDatos","DatosProcesados","Aspecto"]

ref table Aspecto
```

**Lección.** Al crear una tabla editando TMDL a mano hay que tocar **tres**
sitios: el archivo de la tabla, `model.tmdl` y `relationships.tmdl`. Crear solo
el archivo deja el modelo incompleto de una forma que no da error visible.

### 11.3 — La tabla `Calendario` fallaba al abrir en otra máquina

**Síntoma.** Al abrir el proyecto en un equipo distinto, o tras limpiar la caché,
`Calendario` daba error y con ella se caían todas las medidas de tiempo.

**Causa.** `CALENDAR(DATE(YEAR(BLANK()), 1, 1), ...)` produce una fecha inválida.
Cuando `Reseñas` aún no tiene datos cargados, `MIN` y `MAX` devuelven vacío.

**Solución.** Los `IF(ISBLANK(...))` con años de reserva (2019 / año actual)
descritos en la sección 4.

### 11.4 — `Mejor aspecto` y `Peor aspecto` daban el mismo valor para todos

**Síntoma.** En una tabla, las dos medidas devolvían el mismo aspecto en todas
las filas.

**Causa.** El visual de tabla no establecía contexto de fila por restaurante, de
modo que `VALUES(Aspectos[Aspecto])` se evaluaba sobre todo el modelo.

**Solución.** Cambiar el visual de tabla a **matriz** con `Restaurantes[Restaurante]`
en Filas.

### 11.5 — Un `.pbix` conviviendo con el `.pbip`

**Síntoma.** Errores de campos inexistentes que parecían venir del proyecto.

**Causa.** Existían a la vez `Restaurantes.pbix` y `Restaurantes.pbip`, con
nombres que se diferencian en una letra. Al abrir el que no era, Power BI cargaba
un modelo viejo.

**Solución.** No versionar el `.pbix`. Si hace falta uno suelto para entregar, se
exporta **fuera** de esta carpeta.

### 11.6 — Tres calificaciones no fiables en el origen

**Síntoma.** *Aji de Cali* aparecía como el peor calificado (1.1 de 5) pese a
tener reseñas elogiosas.

**Causa.** RestaurantGuru publica en su JSON-LD un `aggregateRating` que
contradice el que muestra en su propia web: la ficha muestra 4.6/5 y el dato
estructurado declara `ratingValue: 1.1`. El scraper lee el JSON-LD.

**Efecto en Power BI.** La columna `Restaurantes[Calificación]` arrastra esos tres
valores. Cualquier ranking por calificación los sitúa arriba de forma indebida.

**Solución.** No se corrigen —no hay forma de recuperar el valor bueno sin volver
a scrapear— sino que se **detectan y se declaran**. Ver
`src/preprocessing/calidad.py` y la sección de limitaciones del README. Los
visuales de este informe rankean por **sentimiento**, no por calificación, así que
no están afectados; la calificación se usa solo como atributo descriptivo.

---

## 12. Cómo verificar que todo sigue bien

Comprobaciones rápidas tras cualquier cambio:

| Qué | Cómo | Resultado esperado |
|---|---|---|
| Filas de las tablas | Vista *Datos* | Restaurantes 241 · Reseñas 1108 · Aspectos 4432 · Aspecto 4 |
| Total reseñas | Tarjeta de la Página 1 | 1108 |
| Total restaurantes | Tarjeta de la Página 1 | 241 |
| Menciones negativas | Raíz del árbol, Página 3 | 80 |
| Relaciones | Vista *Modelo* | 5 relaciones, todas 1:N y de filtro simple |
| Títulos | Las tres páginas | 22 visuales con título visible |

La cifra de 80 menciones negativas se puede contrastar contra los datos con:

```bash
python -c "
import pandas as pd
df = pd.read_csv('data/processed/restaurants_clustered.csv')
print(sum(((df['sentiment_'+a]=='negative') & (df['mentions_'+a].astype(str).str.lower()=='true')).sum() for a in ['comida','servicio','precio','ambiente']))
"
```

Desglose por aspecto: Comida 34, Servicio 26, Precio 10, Ambiente 10.
