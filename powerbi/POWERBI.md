# Modelo de Power BI

Documentación del componente de Business Intelligence del proyecto: qué contiene
el modelo, por qué está armado así, y cómo trabajar con él.

> **Estado actual:** el modelo (tablas, relaciones y las 30 medidas DAX) está
> construido y verificado, y su definición está en `modelo.tmdl`. Lo que falta es
> el archivo `Restaurantes.pbix` con los visuales armados: las secciones 2 y 5 de
> este documento describen cómo abrirlo y qué construir. Mientras el `.pbix` no
> esté en el repositorio, el modelo puede reproducirse desde `modelo.tmdl`.

---

## 1. Por qué Power BI si ya existe el dashboard

Streamlit y Power BI **no muestran lo mismo**. Repetir las mismas gráficas en dos
herramientas no agrega valor y obliga a mantener dos veces lo mismo. El reparto es:

| | Streamlit | Power BI |
|---|---|---|
| Sentimiento por aspecto extraído del texto | ✅ lo produce | consume el resultado |
| Agrupamiento K-Means de restaurantes | ✅ lo produce | consume el resultado |
| Recomendador interactivo | ✅ | — |
| Lectura de reseñas individuales | ✅ | — |
| **Evolución en el tiempo** | ❌ no existe | ✅ |
| **Comparación contra un referente** | ❌ | ✅ |
| **Ranking dinámico según lo filtrado** | ❌ | ✅ |
| **Segmentar por aspecto de forma nativa** | ❌ | ✅ |
| **Árbol de descomposición / IA visual** | ❌ | ✅ |

En resumen: **Streamlit hace el análisis (Python, ML, NLP), Power BI hace la
exploración** de ese resultado.

El punto más importante: **el dashboard no tiene ningún análisis temporal**, y el
dataset tiene fechas desde 2019 hasta 2026. Todo ese eje está sin explotar y es
exactamente lo que Power BI hace mejor.

---

## 2. Cómo abrir el modelo

1. Abrí `powerbi/Restaurantes.pbix` en Power BI Desktop.
2. **Cambiá la ruta de los datos** (cada quien tiene el repo en otro lugar):
   - *Inicio → Transformar datos → Administrar parámetros*
   - Editá `RutaDatos` y poné la carpeta `data/processed` de **tu** copia del repo.
     Ejemplo: `C:\Users\TuUsuario\Documentos\Restaurant-Sentiment-Analysis\data\processed`
   - Cerrar y aplicar.
3. *Inicio → Actualizar*.

Si el pipeline de Python se vuelve a correr (`python run_pipeline.py`), basta con
actualizar en Power BI: el modelo lee los mismos CSV.

---

## 3. Estructura del modelo

Esquema en estrella con una tabla de hechos principal:

```
                  ┌──────────────┐
                  │ Calendario   │  (tabla de fechas, marcada como tal)
                  └──────┬───────┘
                         │ 1
                         │
                         ▼ *
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Restaurantes │──►│   Resenas    │◄──│   Aspectos   │
│  241 filas   │ 1 │  1108 filas  │ 1 │  4432 filas  │
└──────────────┘  *└──────────────┘  *└──────────────┘
```

### `Restaurantes` — dimensión (241 filas)

Una fila por restaurante. Sale de deduplicar el CSV por `restaurant_id`, que ya
es un **id canónico**: si el mismo local aparece en Degusta y en RestaurantGuru,
el pipeline de Python lo unificó antes.

Campos: `Restaurante`, `Cocina`, `CocinaPrincipal`, `Zona`, `Direccion`,
`BandaPrecio`, `NivelPrecio`, `Calificacion`, `Grupo` (nombre del cluster),
`GrupoID`, `Fuente`.

### `Resenas` — hechos (1108 filas)

Una fila por reseña, con `ResenaID` agregado como índice.

Campos: `Fecha`, `CalificacionResena`, `Texto`, `Autor`, `Fuente`, `Idioma`,
`Palabras`, `Caracteres`.

### `Aspectos` — hechos despivotados (4432 filas = 1108 × 4)

**Esta es la tabla que hace posible el análisis por aspecto en Power BI.**

El CSV trae los aspectos "a lo ancho": ocho columnas
(`sentiment_comida_score`, `mentions_comida`, `sentiment_servicio_score`, …). Con
ese formato no se puede poner "Aspecto" en un eje ni usarlo como segmentador.

Al despivotar queda una fila por reseña **y** aspecto:

| ResenaID | Aspecto | Sentimiento | Puntaje | Mencionado |
|---|---|---|---|---|
| 1 | Comida | Positivo | 1 | ✔ |
| 1 | Servicio | Neutral | 0 | ✔ |
| 1 | Precio | Neutral | 0 | ✘ |
| 1 | Ambiente | Positivo | 1 | ✔ |

Ahora `Aspecto` es una columna común y sirve como eje, leyenda o filtro.

**`Mencionado` es clave.** Marca si la reseña habló realmente del aspecto. Una
reseña que nunca menciona el precio no es evidencia de que el precio sea
promedio; contarla como "neutral" arrastra todos los promedios hacia cero. Por eso
`[Sentimiento promedio]` filtra por `Mencionado = TRUE()`.

La diferencia es grande: el precio se menciona solo en el **21,7%** de las
reseñas. Promediando todo daría 0,06; promediando solo a quienes opinaron da
**0,27**.

### `Calendario` — dimensión de fechas

Tabla calculada en DAX que cubre de enero de 2019 a diciembre de 2026 (derivado
del rango real de los datos), marcada como tabla de fechas para habilitar la
inteligencia de tiempo.

### Relaciones

| Desde | Hacia | Cardinalidad |
|---|---|---|
| `Resenas[RestauranteID]` | `Restaurantes[RestauranteID]` | * : 1 |
| `Aspectos[ResenaID]` | `Resenas[ResenaID]` | * : 1 |
| `Resenas[Fecha]` | `Calendario[Date]` | * : 1 |

`Aspectos` se conecta a `Restaurantes` **a través de** `Resenas`, no directo. Si
tuviera las dos relaciones se formaría un camino ambiguo y Power BI no sabría por
cuál filtrar.

---

## 4. Medidas DAX

Organizadas en carpetas dentro del panel de campos.

### 1 Base

| Medida | Qué hace |
|---|---|
| `Total resenas` | Reseñas en el contexto actual |
| `Total restaurantes` | Restaurantes distintos con reseñas |
| `Calificacion promedio` | Promedio de la nota que dio cada reseña |
| `Resenas con calificacion` | Cuántas traen nota propia (para declarar cobertura) |
| `Palabras por resena` | Longitud media |

### 2 Sentimiento

| Medida | Qué hace |
|---|---|
| `Sentimiento promedio` | Promedio de −1 a 1, **solo** sobre quienes mencionaron el aspecto |
| `Menciones` | Cuántas reseñas hablaron del aspecto |
| `Cobertura de menciones` | Qué % de reseñas lo mencionan |
| `Menciones positivas` / `negativas` | Conteos por signo |
| `% positivas` / `% negativas` | Proporción sobre las menciones |
| `Saldo de opinion` | `% positivas − % negativas` |

### 3 Tiempo — *lo que Streamlit no tiene*

| Medida | Qué hace |
|---|---|
| `Resenas mes anterior` | Mes previo, con `DATEADD` |
| `Variacion mensual` | Crecimiento % contra el mes anterior |
| `Resenas ano anterior` | Mismo periodo del año pasado (`SAMEPERIODLASTYEAR`) |
| `Resenas acumuladas` | Total acumulado hasta la fecha |
| `Media movil 3 meses` | Suaviza la serie para ver tendencia |
| `Sentimiento mes anterior` | Sentimiento del mes previo |
| `Cambio de sentimiento` | Si la percepción mejora o empeora |

### 4 Comparación — *contra un referente*

| Medida | Qué hace |
|---|---|
| `Sentimiento de su cocina` | Promedio de todos los de la misma cocina (`ALLEXCEPT`) |
| `Diferencia vs su cocina` | Cuánto se despega de sus pares. Positivo = mejor |
| `Sentimiento de su zona` / `Diferencia vs su zona` | Lo mismo por barrio |
| `Ranking por sentimiento` | Posición con `RANKX`, recalculada según lo filtrado |
| `% del total de resenas` | Peso dentro de la selección |

### 5 Desbalance — *detectar restaurantes desparejos*

| Medida | Qué hace |
|---|---|
| `Brecha entre aspectos` | Distancia entre el mejor y el peor aspecto |
| `Mejor aspecto` / `Peor aspecto` | Nombre del aspecto (texto) |
| `Restaurantes con quejas` | Cuántos acumulan menciones negativas |

Una brecha alta señala un restaurante que hace una cosa muy bien y otra mal.
Ejemplo real del dataset: *Naked Lukas Obarrio* → mejor **Ambiente**, peor
**Servicio**, brecha **1,5**. Eso no se ve en ninguna vista de Streamlit.

---

## 5. Páginas del informe propuestas

Las tres evitan deliberadamente repetir lo que ya está en Streamlit.

### Página 1 — Evolución en el tiempo

*Streamlit no tiene ninguna gráfica temporal.*

| Visual | Campos |
|---|---|
| Gráfico de líneas | Eje `Calendario[AnoMes]` · Valores `Total resenas` y `Media movil 3 meses` |
| Gráfico de área | Eje `Calendario[AnoMes]` · Valor `Resenas acumuladas` |
| Líneas | Eje `Calendario[AnoMes]` · Valor `Sentimiento promedio` · Leyenda `Aspectos[Aspecto]` |
| Tarjetas | `Total resenas`, `Variacion mensual`, `Cambio de sentimiento` |
| Segmentadores | `Calendario[Ano]`, `Restaurantes[CocinaPrincipal]`, `Aspectos[Aspecto]` |

> **Ojo al interpretar:** Degusta solo publica las 5 reseñas más recientes de cada
> restaurante, así que los meses recientes concentran casi todo el volumen. La
> serie describe *cuándo se escribieron las reseñas disponibles*, no la actividad
> real de los restaurantes. Conviene aclararlo en el informe.

### Página 2 — Comparación contra el mercado

*Streamlit compara hasta 5 restaurantes elegidos a mano; acá se comparan los 241 contra su propio grupo.*

| Visual | Campos |
|---|---|
| Matriz | Filas `Restaurantes[Restaurante]` · Valores `Sentimiento promedio`, `Sentimiento de su cocina`, `Diferencia vs su cocina`, `Ranking por sentimiento` |
| Gráfico de dispersión | X `Diferencia vs su cocina` · Y `Total resenas` · Detalles `Restaurante` |
| Barras | `Restaurante` ordenado por `Diferencia vs su cocina` (arriba y abajo) |
| Matriz | Filas `Restaurantes[Zona]` · Columnas `Aspectos[Aspecto]` · Valor `Sentimiento promedio`, con formato condicional |

La última matriz es **zona × aspecto**; el mapa de calor de Streamlit es
**cocina × aspecto**. Distinto corte, distinta conclusión.

### Página 3 — Dónde está el problema

*Diagnóstico por aspecto. No existe en Streamlit.*

| Visual | Campos |
|---|---|
| Tabla | `Restaurante`, `Mejor aspecto`, `Peor aspecto`, `Brecha entre aspectos`, `Total resenas` |
| Barras | Eje `Aspectos[Aspecto]` · Valor `% negativas` |
| Matriz | Filas `CocinaPrincipal` · Columnas `Aspecto` · Valor `Saldo de opinion` |
| **Árbol de descomposición** | Analizar `Menciones negativas` · Explicar por `Zona`, `CocinaPrincipal`, `BandaPrecio`, `Aspecto` |
| **Influenciadores clave** | Analizar `Aspectos[Sentimiento]` · Explicar por `BandaPrecio`, `Zona`, `CocinaPrincipal`, `Fuente` |
| Tarjetas | `Restaurantes con quejas`, `Cobertura de menciones` |

El árbol de descomposición y los influenciadores clave son visuales **exclusivos
de Power BI**: no se pueden reproducir en Streamlit sin programarlos a mano.

---

## 6. Buenas prácticas al armar los visuales

- **Mostrar siempre la cobertura.** Junto a cualquier promedio de sentimiento,
  poner `Menciones` o `Cobertura de menciones`. Es el mismo criterio que sigue el
  dashboard: una barra debe decir sobre cuántas reseñas se apoya.
- **Filtrar restaurantes con muy pocas reseñas** cuando se hagan rankings. Con 3
  reseñas el promedio es ruido. Se puede usar un filtro de nivel de visual sobre
  `Total resenas >= 5`.
- **No duplicar Streamlit.** Antes de agregar un visual, revisar la tabla de la
  sección 1.

---

## 7. Archivos

| Archivo | Qué es |
|---|---|
| `powerbi/Restaurantes.pbix` | El informe. Binario: **no se puede revisar en un pull request**. *Pendiente de agregar* |
| `powerbi/modelo.tmdl` | El mismo modelo en texto. Sí se puede revisar y comparar en git |
| `powerbi/POWERBI.md` | Este documento |

El `.tmdl` se regenera exportando el modelo desde Power BI Desktop
(*Inicio → Modelo → Exportar*) o con herramientas externas. Conviene actualizarlo
cuando se agreguen medidas, para que los cambios queden visibles en git.

---

## 8. Limitaciones conocidas

- **La ruta de datos es absoluta.** Power BI no maneja rutas relativas; por eso
  existe el parámetro `RutaDatos`. Cada integrante debe ajustarlo una vez.
- **El modelo es de importación**, no DirectQuery: los datos quedan dentro del
  `.pbix`. Hay que actualizar manualmente tras correr el pipeline.
- **`Calificacion promedio` cubre el 88% de las reseñas.** Solo Degusta publica la
  nota individual; las de RestaurantGuru vienen sin ella.
- **El sentimiento viene calculado desde Python**, no de Power BI. Power BI no
  reprocesa el texto: consume `sentiment_*` y `mentions_*` del CSV.
- **Las fechas se concentran en meses recientes** por cómo publica Degusta (ver
  nota de la Página 1).
