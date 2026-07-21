# Plataforma de Análisis de Reseñas de Restaurantes — Panamá

Proyecto Integrador (Segundo Parcial) — **Grupo 5**

Sistema que recopila reseñas reales de restaurantes de Ciudad de Panamá desde
**dos fuentes independientes**, las procesa con un pipeline ETL, aplica **análisis
de sentimiento por aspecto** y **tres modelos de aprendizaje automático**, y las
presenta en un **dashboard de Streamlit** y un **informe de Power BI**.

---

## El problema

Una calificación de 4.2 estrellas no dice *por qué*. Un restaurante con la comida
excelente y el servicio pésimo puede tener la misma nota que uno mediocre en todo.
Este proyecto separa esos componentes: extrae de cada reseña qué opina el cliente
sobre **comida, servicio, precio y ambiente** por separado.

## Las cifras

| | |
|---|---|
| Reseñas reales | **1108** |
| Restaurantes | **241** |
| Fuentes | Degusta (973) · RestaurantGuru (135) |
| Rango de fechas | 2019 – 2026 |
| Calificación promedio | 4.49 de 5 |
| Medidas DAX en Power BI | 30 |
| Páginas de dashboard | 7 (Streamlit) + 3 (Power BI) |
| Pruebas automatizadas | **263** |

Cobertura de los campos:

| Campo | Cobertura |
|---|---|
| Rango de precio · Zona · Calificación del restaurante | 100% |
| Categoría de cocina | 97% |
| Fecha de la reseña | 90% |
| Calificación propia de la reseña | 88% |

Para regenerar estas cifras: `python run_pipeline.py`.

---

## Inicio rápido

```bash
pip install -r requirements.txt
python run_pipeline.py            # genera los datos
streamlit run dashboard/app.py    # levanta el dashboard
```

Para Power BI: abrir `powerbi/Restaurantes.pbip` y ajustar el parámetro `RutaDatos`.

Para el asistente con LLM (opcional), crear un `.env` en la raíz:

```
GOOGLE_API_KEY=tu_clave
GEMINI_MODEL=gemini-3.5-flash
```

---

## Documentación

Cada documento cubre un componente y no repite a los demás.

| Documento | Qué cubre |
|---|---|
| **[docs/PROYECTO.md](docs/PROYECTO.md)** | Manual completo: datos, scrapers, pipeline, análisis de sentimiento, pruebas, limitaciones y preguntas frecuentes |
| **[docs/MODELOS.md](docs/MODELOS.md)** | Los tres modelos de ML: qué hacen, por qué se eligieron y qué resultados dan |
| **[docs/DASHBOARD.md](docs/DASHBOARD.md)** | El dashboard de Streamlit, página por página |
| **[docs/PREGUNTAS.md](docs/PREGUNTAS.md)** | 87 preguntas y respuestas para la defensa |
| **[powerbi/CONSTRUCCION.md](powerbi/CONSTRUCCION.md)** | Cómo se construyó el informe de Power BI, paso a paso |
| **[powerbi/POWERBI.md](powerbi/POWERBI.md)** | Referencia del modelo de Power BI: tablas, medidas y relaciones |
| [PRD.md](PRD.md) | Documento de planificación original *(histórico)* |

---

## Estructura del repositorio

```
├── src/
│   ├── ingestion/          scrapers y unificación de fuentes
│   ├── preprocessing/      limpieza, normalización, características, calidad
│   ├── sentiment/          léxico propio de análisis por aspecto
│   ├── classification/     modelo supervisado y comparación de enfoques
│   ├── clustering/         K-Means por restaurante
│   ├── recommendation/     motor de recomendación
│   └── llm/                asistente con Gemini
├── dashboard/              aplicación de Streamlit (7 páginas)
├── powerbi/                proyecto Power BI (.pbip) en formato texto
├── tests/                  263 pruebas
├── data/
│   ├── raw/                salida directa de los scrapers
│   └── processed/          salida del pipeline
└── run_pipeline.py         ejecuta el pipeline completo
```

---

## Cumplimiento de la rúbrica

| Componente | Cómo se cumple |
|---|---|
| **Técnica de ML + justificación** | Tres enfoques comparados contra la misma verdad de referencia: K-Means (*k*=4 por silhouette), TF-IDF + regresión logística (F1 macro 0.713 ± 0.020, AUC 0.794) y un LLM. La justificación de cada elección está en [docs/MODELOS.md](docs/MODELOS.md) |
| **Modelo estrella en Power BI** | Dos tablas de hechos (`Reseñas`, `Aspectos`) sobre tres dimensiones conformadas (`Restaurantes`, `Calendario`, `Aspecto`), sin copo de nieve. Ver [powerbi/CONSTRUCCION.md](powerbi/CONSTRUCCION.md#5-relaciones-armar-la-estrella) |
| **Dashboards claros e interactivos** | 3 páginas en Power BI con 5 segmentadores y un árbol de descomposición, más 7 páginas en Streamlit con filtros que afectan a todo el contenido |
| **Ampliación de KPIs** | 30 medidas DAX organizadas en cinco carpetas: base, sentimiento, tiempo, comparación y desbalance |
| **Uso de LLM** | Consultas en lenguaje natural sobre los datos, resúmenes de reseñas y clasificación de sentimiento, con guardarraíles contra la invención de cifras. Ver [docs/DASHBOARD.md](docs/DASHBOARD.md#10-página-7--asistente) |

### Por qué Power BI además del dashboard

No repiten lo mismo, a propósito. **Streamlit produce el análisis** (NLP,
clustering, recomendador, asistente); **Power BI explora el resultado** en ejes que
el dashboard no cubre: evolución temporal, comparación contra un referente,
ranking dinámico y descomposición interactiva.

El argumento más fuerte: el dashboard no tiene ninguna gráfica temporal, y el
conjunto de datos abarca de 2019 a 2026.

---

## Limitaciones

El proyecto declara sus límites en vez de maquillarlos. Los principales:

- **Tres calificaciones de RestaurantGuru no son fiables.** La fuente publica en su
  JSON-LD un valor que contradice el que muestra en su web (*Aji de Cali*: 4.6 en
  pantalla, 1.1 en el dato estructurado). Se detectan automáticamente, se excluyen
  de los rankings y se avisa en la interfaz.
- **El sentimiento está sesgado a positivo** porque las reseñas publicadas lo están
  (~87%). Se muestra tal cual.
- **El precio se menciona en el 22% de las reseñas.** Su promedio se calcula solo
  sobre esas, y siempre se indica la cobertura.
- **El silhouette del clustering es 0.17**: los grupos describen un continuo, no
  fronteras nítidas.

La lista completa, con su explicación, está en
[docs/PROYECTO.md](docs/PROYECTO.md#10-limitaciones-conocidas).

---

## Equipo y licencia

- **Grupo 5** — Plataforma de Análisis de Reseñas de Restaurantes
- Licencia: **MIT**
