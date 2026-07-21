"""
Compara los tres enfoques de analisis de sentimiento contra la misma verdad.

Los tres predicen lo mismo -si una resena es positiva o no- pero por caminos
distintos:

    Lexico          reglas escritas a mano, sin aprendizaje
    Supervisado     TF-IDF + regresion logistica entrenada con ejemplos
    LLM (Gemini)    modelo de lenguaje sin entrenamiento especifico

La verdad de referencia es la calificacion en estrellas que puso el propio
resenador, que ninguno de los tres ve. Eso permite medirlos con la misma vara.

El LLM se evalua sobre una MUESTRA, no sobre las 973 resenas: cada llamada tarda
y consume cuota. La muestra es estratificada para que conserve la proporcion
real de resenas no positivas, que es la clase dificil.

Uso:
    python -m src.classification.comparar_enfoques --muestra 80
"""

import argparse
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.classification.sentiment_classifier import (
    NO_POSITIVA,
    POSITIVA,
    construir_modelo,
    evaluar,
    predecir_con_lexico,
    preparar_datos,
)


def predecir_con_llm(textos: pd.Series, pausa: float = 0.6) -> Optional[np.ndarray]:
    """Clasifica con el LLM y reduce los cuatro aspectos a la etiqueta binaria.

    Devuelve None si el asistente no esta disponible, para que el resto de la
    comparacion siga funcionando sin clave de API.
    """
    from src.llm.asistente import AsistenteDatos, LLMNoDisponible, motivo_no_disponible

    try:
        asistente = AsistenteDatos()
    except LLMNoDisponible:
        print(f"  LLM no disponible: {motivo_no_disponible()}")
        return None

    predicciones: List[str] = []
    for i, texto in enumerate(textos, 1):
        try:
            aspectos = asistente.clasificar_sentimiento(str(texto))
            puntajes = [1 if v == "positive" else -1 if v == "negative" else 0
                        for v in aspectos.values()]
            predicciones.append(POSITIVA if np.mean(puntajes) > 0 else NO_POSITIVA)
        except Exception as e:
            print(f"  fila {i}: fallo la llamada ({type(e).__name__}), se asume positiva")
            predicciones.append(POSITIVA)

        if i % 10 == 0:
            print(f"  {i}/{len(textos)} resenas clasificadas por el LLM...")
        time.sleep(pausa)

    return np.array(predicciones)


def comparar(df: pd.DataFrame, tamano_muestra: int = 80,
             random_state: int = 42) -> Dict:
    """Evalua los tres enfoques sobre la misma muestra estratificada."""
    textos, etiquetas = preparar_datos(df)

    # Muestra estratificada: conserva la proporcion de la clase minoritaria
    if tamano_muestra < len(textos):
        _, textos_muestra, _, etiquetas_muestra = train_test_split(
            textos, etiquetas, test_size=tamano_muestra,
            random_state=random_state, stratify=etiquetas,
        )
    else:
        textos_muestra, etiquetas_muestra = textos, etiquetas

    print(f"Muestra: {len(textos_muestra)} resenas "
          f"({(etiquetas_muestra == NO_POSITIVA).sum()} no positivas)\n")

    resultados = {}

    print("Evaluando el lexico...")
    resultados["lexico"] = evaluar(
        "Lexico", etiquetas_muestra, predecir_con_lexico(textos_muestra))

    print("Entrenando y evaluando el modelo supervisado...")
    # Se entrena con las resenas que NO estan en la muestra, para no evaluar
    # sobre datos que el modelo ya vio.
    en_muestra = textos.index.isin(textos_muestra.index)
    modelo = construir_modelo()
    modelo.fit(textos[~en_muestra], etiquetas[~en_muestra])
    resultados["supervisado"] = evaluar(
        "Supervisado", etiquetas_muestra, modelo.predict(textos_muestra))

    print("Consultando al LLM (esto tarda)...")
    prediccion_llm = predecir_con_llm(textos_muestra)
    if prediccion_llm is not None:
        resultados["llm"] = evaluar("LLM (Gemini)", etiquetas_muestra, prediccion_llm)

    return {
        "n_muestra": len(textos_muestra),
        "n_minoritaria": int((etiquetas_muestra == NO_POSITIVA).sum()),
        "resultados": resultados,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muestra", type=int, default=80,
                        help="cuantas resenas evaluar (el LLM cobra por llamada)")
    args = parser.parse_args()

    df = pd.read_csv("data/processed/restaurants_clustered.csv")
    r = comparar(df, tamano_muestra=args.muestra)

    print("\n" + "=" * 78)
    print("COMPARACION DE ENFOQUES")
    print("=" * 78)
    print(f"Verdad de referencia: la calificacion en estrellas del resenador.")
    print(f"Muestra: {r['n_muestra']} resenas, {r['n_minoritaria']} no positivas\n")

    encabezado = f"{'Enfoque':<16}{'Exactitud':>11}{'F1 macro':>11}{'Precision*':>12}{'Exhaust.*':>11}{'F1*':>8}"
    print(encabezado)
    print("-" * len(encabezado))
    for resultado in r["resultados"].values():
        print(f"{resultado.nombre:<16}{resultado.exactitud:>11.3f}{resultado.f1_macro:>11.3f}"
              f"{resultado.precision_minoritaria:>12.3f}"
              f"{resultado.exhaustividad_minoritaria:>11.3f}{resultado.f1_minoritaria:>8.3f}")
    print("\n* columnas referidas a la clase 'no positiva', que es la minoritaria "
          "y la que interesa detectar.")

    if "llm" not in r["resultados"]:
        print("\nEl LLM no se evaluo porque falta la clave de la API. "
              "Ver src/llm/asistente.py para configurarla.")


if __name__ == "__main__":
    main()
