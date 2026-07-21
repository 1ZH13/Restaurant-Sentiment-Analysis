"""
Deteccion de calificaciones poco fiables.

Por que existe
--------------
RestaurantGuru publica en su JSON-LD un `aggregateRating` que a veces contradice
la calificacion que muestra en pantalla. Caso verificado contra la web en julio
de 2026: la ficha de "Aji de Cali" muestra 4.6/5, pero su JSON-LD declara
`ratingValue: 1.1` con `bestRating: 5`. El scraper lee el JSON-LD, asi que copio
fielmente un dato que la propia fuente se contradice.

El sintoma en el conjunto de datos es una distribucion imposible: las
calificaciones de RestaurantGuru son 1.1, 1.9, 2.4 y despues saltan a 4.8, 4.9 y
5.0, sin nada en medio. Y los tres restaurantes por debajo de 3 tienen reseñas
claramente positivas.

Que hace este modulo
--------------------
No corrige la calificacion: no tenemos forma de saber el valor bueno sin volver
a scrapear, y la fuente es lenta a proposito. Lo que hace es *detectar* la
contradiccion entre la calificacion y el sentimiento del texto, para que el
dashboard y el asistente puedan avisar en lugar de afirmar un dato falso.

Es preferible declarar una limitacion conocida que presentar un ranking que
sabemos que esta mal.
"""

from typing import List

import pandas as pd

# Por debajo de esto la calificacion ya es mala en un conjunto cuya mediana ronda
# 4.5, asi que el texto deberia acompanar. La comparacion es ESTRICTA a proposito:
# 3.0 es exactamente el minimo de Degusta, y un restaurante mediocre con una
# resena buena es normal, no una contradiccion.
RATING_MALO = 3.0

# El sentimiento del lexico va de -1 a 1. Por encima de esto el texto es
# claramente favorable, no solo neutro.
SENTIMIENTO_FAVORABLE = 0.1


def _columnas_de_sentimiento(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns
            if c.startswith("sentiment_") and c.endswith("_score")]


def sentimiento_medio(df: pd.DataFrame) -> pd.Series:
    """Promedia el sentimiento de todos los aspectos de cada resena."""
    columnas = _columnas_de_sentimiento(df)
    if not columnas:
        return pd.Series(dtype=float, index=df.index)
    return df[columnas].mean(axis=1, skipna=True)


def ratings_sospechosos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve los restaurantes cuya calificacion contradice a sus resenas.

    Se marca el caso que sabemos que ocurre: calificacion baja con texto
    favorable. El caso inverso (5 estrellas con texto pesimo) es mucho mas comun
    de forma legitima -clientes que puntuan alto y se quejan de un detalle-, asi
    que no se marca.
    """
    requeridas = {"restaurant_name", "overall_rating"}
    if not requeridas.issubset(df.columns) or not _columnas_de_sentimiento(df):
        return pd.DataFrame(columns=["restaurant_name", "rating", "sentimiento", "resenas"])

    con_sentimiento = df.assign(_sent=sentimiento_medio(df))
    por_restaurante = (con_sentimiento
                       .groupby("restaurant_name", as_index=False)
                       .agg(rating=("overall_rating", "first"),
                            sentimiento=("_sent", "mean"),
                            resenas=("restaurant_name", "size")))

    contradice = ((por_restaurante["rating"] < RATING_MALO) &
                  (por_restaurante["sentimiento"] >= SENTIMIENTO_FAVORABLE))
    return (por_restaurante[contradice]
            .sort_values("rating")
            .reset_index(drop=True))


def nombres_sospechosos(df: pd.DataFrame) -> set:
    """Atajo: solo los nombres, para filtrar rankings."""
    return set(ratings_sospechosos(df)["restaurant_name"])


def nota_de_limitacion(sospechosos: pd.DataFrame) -> str:
    """Frase corta para mostrar en el dashboard o pasarle al asistente."""
    if sospechosos.empty:
        return ""
    nombres = ", ".join(sospechosos["restaurant_name"].astype(str))
    return (f"Aviso de calidad de datos: {len(sospechosos)} restaurante(s) tienen "
            f"una calificacion que contradice el texto de sus resenas, por una "
            f"inconsistencia en la fuente RestaurantGuru ({nombres}). Su "
            f"calificacion no es fiable y no se usa para rankings.")
