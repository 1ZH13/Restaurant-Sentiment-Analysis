# Contexto para continuar en otra sesión

Copia el bloque de abajo como primer mensaje de la nueva sesión.

---

## Prompt

> Estoy trabajando en el Proyecto Integrador del repo
> `C:\Users\ZH\Desktop\Restaurant-Sentiment-Analysis` (Grupo 5, análisis de
> reseñas de restaurantes de Panamá). Ya está todo en `main` y funcionando.
> Quiero seguir revisándolo a fondo antes de la entrega.
>
> **Antes de proponerme nada, audita el estado real:** corre los tests, revisa
> el pipeline y abre los documentos. No te fíes de lo que diga esta descripción
> ni de la documentación del repo — ya nos pasó que el README afirmaba cosas
> que el código no hacía.
>
> Contexto que te ahorra tiempo:
>
> - **No hay Python en el PATH.** Usa `.venv\Scripts\python.exe` y antepón
>   `$env:PYTHONPATH = (Get-Location).Path` para correr módulos.
> - El proyecto tiene **240 tests** (`pytest -m "not e2e" -q`), un dashboard de
>   Streamlit de 7 páginas, y un proyecto de Power BI en `powerbi/Restaurantes.pbip`.
> - Para diagnosticar Power BI, **conéctate al modelo en vivo por el MCP**
>   (`powerbi-modeling-mcp`) en vez de razonar sobre capturas: devuelve el error
>   exacto del motor. Ojo: ese MCP **corrompe la ñ** al enviar o escribir
>   expresiones DAX, así que los cambios al modelo hay que hacerlos editando los
>   archivos TMDL con Power BI **cerrado**.
> - Lee `docs/MODELOS.md` y `powerbi/POWERBI.md`: ahí está el porqué de cada
>   decisión, no solo el qué.
>
> Lo que quiero revisar ahora: **[ESCRIBE AQUÍ LO QUE QUIERAS MIRAR]**

---

## Cosas que quedaron pendientes

Por si quieres retomar alguna, ordenadas por lo que más suma frente al examen:

### 1. Configurar la clave de Gemini y correr la comparación

El asistente y la comparación de los tres enfoques están implementados pero
**nunca se han ejecutado con un LLM real**, porque falta la clave.

```bash
# .env en la raíz del proyecto
GOOGLE_API_KEY=tu_clave     # gratis en https://aistudio.google.com/apikey
```

Luego:
```bash
python -m src.classification.comparar_enfoques --muestra 80
```

Eso da la tabla de léxico vs. supervisado vs. LLM con cifras reales, que es
material fuerte para la sustentación. Hoy la fila del LLM está vacía.

### 2. Dos ajustes en Power BI que dejé anotados y no hice

- **Filtro `Total reseñas >= 5`** en la matriz y las barras de la página 2. Con
  3 reseñas un promedio no significa nada. Son dos clics, pero el umbral es una
  decisión tuya.
- **Visual de Influenciadores clave** en la página 3. Está documentado en
  `POWERBI.md` pero no en el archivo: su configuración es más delicada de
  escribir a mano que de arrastrar en la interfaz.

### 3. El grupo de 3 restaurantes con calificación 1.80

El clustering produce un grupo con solo 3 restaurantes (los peor calificados del
dataset). Es correcto pero llama la atención. Vale la pena revisar si conviene
tratarlos como atípicos o si el grupo aporta información.

### 4. Cosas del proyecto que nunca se auditaron a fondo

- `src/recommendation/recommender.py` — se corrigió el puntaje y las
  preferencias, pero la lógica de explicación (`_generate_explanation`) sigue
  siendo bastante básica.
- `src/preprocessing/normalizer.py` — es el único módulo del pipeline que no se
  revisó en detalle.
- `PRD.md` — documento de requisitos original; puede tener afirmaciones
  desactualizadas como las que tenía el README.
- Las pruebas `e2e` con Playwright (`pytest -m e2e`) nunca se corrieron.

### 5. Limitaciones conocidas que podrían mejorarse

- **RestaurantGuru aporta 135 de 1108 reseñas.** El sitio bloquea agresivamente;
  45 de sus 86 fichas respondieron. Correr el scraper por tandas sumaría más.
- **El silhouette del clustering es 0.17**, que es bajo. Está explicado y es
  honesto, pero si aparecen más datos con variación real podría subir.
- **Solo 19 reseñas de 1-2 estrellas.** Ese desbalance es lo que limita al
  modelo supervisado; más datos negativos lo mejorarían más que cualquier
  ajuste de hiperparámetros.

---

## Lecciones de esta sesión (para no repetirlas)

- **Verificar antes de afirmar.** El README decía "130 pruebas" y "k elegido por
  silhouette" cuando el código entrenaba con k=5 fijo. Los tests llegaron a
  codificar el bug: afirmaban que el clustering agrupaba reseñas.
- **Power BI sobrescribe los archivos del `.pbip`** si está abierto. Hay que
  cerrarlo antes de editar y commitear antes de pedir que lo abra.
- **El reporte de error de Power BI (el de "Enviar comentarios") es la mejor
  pista.** Trae la clase que falla y el número de línea; con eso el diagnóstico
  es directo en vez de por tanteo.
- **Los identificadores de código van en ASCII, el texto visible con tildes.**
  Mezclarlos rompió tres tests cuando se acentuó el dashboard.
