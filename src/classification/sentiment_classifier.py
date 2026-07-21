"""
Modelo supervisado que predice si una resena es positiva a partir de su texto.

A diferencia del clustering, que solo describe grupos, este si es un modelo de
prediccion: aprende de ejemplos etiquetados y clasifica textos que nunca vio.

Sobre la etiqueta
-----------------
El objetivo NO se construye con el analizador lexico del proyecto. Hacerlo seria
circular: el modelo aprenderia a imitar al lexico y las metricas solo dirian
cuanto se parecen entre si, no cuanto aciertan.

La etiqueta sale de la calificacion que el propio resenador puso (1 a 5
estrellas), que es una opinion humana independiente del texto:

    positiva     = 4 o 5 estrellas
    no positiva  = 1, 2 o 3 estrellas

Eso permite medir al lexico y al modelo contra la misma verdad y compararlos.

Sobre el desbalance
-------------------
De 973 resenas con calificacion, 846 son positivas y solo 19 tienen 1 o 2
estrellas. Por eso:

- El problema se plantea binario. Con tres clases, "negativa" tendria 19
  ejemplos y el modelo no aprenderia a reconocerla.
- Se usa class_weight="balanced", que penaliza mas equivocarse en la clase
  minoritaria.
- La metrica principal NO es la exactitud. Un modelo que responda siempre
  "positiva" acierta el 87% y no sirve para nada. Se reportan precision y
  exhaustividad de la clase minoritaria, que es la dificil y la util.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

POSITIVA = "positiva"
NO_POSITIVA = "no positiva"

# Palabras vacias del espanol. Se listan aqui para no depender de la descarga de
# NLTK, que exige conexion y falla en una maquina limpia.
STOPWORDS_ES = [
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "durante", "e",
    "el", "ella", "ellas", "ellos", "en", "entre", "era", "es", "esa", "ese",
    "eso", "esta", "estaba", "estan", "este", "esto", "estos", "fue", "fueron",
    "ha", "habia", "han", "hasta", "hay", "la", "las", "le", "les", "lo", "los",
    "mas", "me", "mi", "mucho", "muy", "nos", "o", "otra", "otro", "para",
    "pero", "poco", "por", "porque", "que", "se", "ser", "si", "sin", "sobre",
    "solo", "son", "su", "sus", "tambien", "te", "tiene", "todo", "un", "una",
    "uno", "unos", "y", "ya",
]


@dataclass
class ResultadoEvaluacion:
    """Metricas de un clasificador sobre el mismo conjunto de prueba."""

    nombre: str
    exactitud: float
    precision_minoritaria: float
    exhaustividad_minoritaria: float
    f1_minoritaria: float
    f1_macro: float
    matriz_confusion: List[List[int]]
    auc: Optional[float] = None
    reporte: str = ""

    def resumen(self) -> str:
        return (f"{self.nombre:24s} exactitud={self.exactitud:.3f}  "
                f"F1 macro={self.f1_macro:.3f}  "
                f"'{NO_POSITIVA}': precision={self.precision_minoritaria:.3f} "
                f"exhaustividad={self.exhaustividad_minoritaria:.3f} "
                f"F1={self.f1_minoritaria:.3f}")


def etiquetar(calificacion: float) -> Optional[str]:
    """Convierte estrellas en la etiqueta binaria."""
    if pd.isna(calificacion):
        return None
    return POSITIVA if calificacion >= 4 else NO_POSITIVA


def preparar_datos(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Devuelve (textos, etiquetas) de las resenas que traen calificacion propia."""
    if "review_rating" not in df.columns or "review_text" not in df.columns:
        raise KeyError("El DataFrame necesita las columnas review_rating y review_text")

    datos = df[["review_text", "review_rating"]].copy()
    datos["etiqueta"] = datos["review_rating"].apply(etiquetar)
    datos = datos.dropna(subset=["etiqueta", "review_text"])
    datos = datos[datos["review_text"].astype(str).str.strip().str.len() > 0]

    return datos["review_text"].astype(str), datos["etiqueta"]


def construir_modelo(C: float = 1.0) -> Pipeline:
    """Arma el pipeline TF-IDF + regresion logistica.

    Por que esta combinacion y no otra:

    - TF-IDF sobre palabras y bigramas captura expresiones que cambian el
      sentido ("no recomiendo", "muy lento"), algo que perderia una bolsa de
      palabras simple.
    - La regresion logistica funciona bien con muchas caracteristicas y pocos
      ejemplos, que es exactamente este caso: cientos de resenas y miles de
      terminos. Modelos mas complejos, como un bosque aleatorio o una red, se
      sobreajustarian con 973 filas.
    - Ademas es interpretable: se puede leer que palabras empujan hacia cada
      clase, cosa que un modelo de caja negra no permite y que aqui importa
      para justificar el resultado.
    """
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
            sublinear_tf=True,
            stop_words=STOPWORDS_ES,
            strip_accents="unicode",
            lowercase=True,
        )),
        ("clf", LogisticRegression(
            C=C,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        )),
    ])


def evaluar(nombre: str, y_real, y_predicho, y_probabilidad=None) -> ResultadoEvaluacion:
    """Calcula las metricas centrandose en la clase minoritaria."""
    etiquetas = [NO_POSITIVA, POSITIVA]
    auc = None
    if y_probabilidad is not None:
        try:
            auc = float(roc_auc_score((np.asarray(y_real) == NO_POSITIVA).astype(int),
                                      y_probabilidad))
        except ValueError:
            auc = None

    return ResultadoEvaluacion(
        nombre=nombre,
        exactitud=float(accuracy_score(y_real, y_predicho)),
        precision_minoritaria=float(precision_score(
            y_real, y_predicho, pos_label=NO_POSITIVA, zero_division=0)),
        exhaustividad_minoritaria=float(recall_score(
            y_real, y_predicho, pos_label=NO_POSITIVA, zero_division=0)),
        f1_minoritaria=float(f1_score(
            y_real, y_predicho, pos_label=NO_POSITIVA, zero_division=0)),
        f1_macro=float(f1_score(y_real, y_predicho, average="macro", zero_division=0)),
        matriz_confusion=confusion_matrix(y_real, y_predicho, labels=etiquetas).tolist(),
        auc=auc,
        reporte=classification_report(y_real, y_predicho, zero_division=0),
    )


def predecir_con_lexico(textos: pd.Series) -> np.ndarray:
    """Linea base: convierte la salida del analizador lexico en la misma etiqueta.

    Sirve para responder si el modelo supervisado aporta algo por encima de las
    reglas que ya tenia el proyecto.
    """
    from src.sentiment.fallback_classifier import SpanishLexiconAnalyzer

    analizador = SpanishLexiconAnalyzer()
    predicciones = []
    for texto in textos:
        detalles = analizador.get_aspect_details(texto)
        puntajes = [1 if d["label"] == "positive" else -1 if d["label"] == "negative" else 0
                    for d in detalles.values() if d["mentioned"]]
        if not puntajes:
            puntajes = [1 if detalles["comida"]["label"] == "positive"
                        else -1 if detalles["comida"]["label"] == "negative" else 0]
        predicciones.append(POSITIVA if np.mean(puntajes) > 0 else NO_POSITIVA)
    return np.array(predicciones)


def terminos_influyentes(modelo: Pipeline, cantidad: int = 12) -> Dict[str, List[Tuple[str, float]]]:
    """Palabras que mas empujan hacia cada clase, para poder explicar el modelo."""
    vectorizador = modelo.named_steps["tfidf"]
    clasificador = modelo.named_steps["clf"]

    nombres = np.array(vectorizador.get_feature_names_out())
    pesos = clasificador.coef_[0]
    orden = np.argsort(pesos)

    positiva_es = clasificador.classes_[1] == POSITIVA
    hacia_positiva = orden[::-1][:cantidad] if positiva_es else orden[:cantidad]
    hacia_negativa = orden[:cantidad] if positiva_es else orden[::-1][:cantidad]

    return {
        POSITIVA: [(nombres[i], float(pesos[i])) for i in hacia_positiva],
        NO_POSITIVA: [(nombres[i], float(pesos[i])) for i in hacia_negativa],
    }


def elegir_umbral(modelo_base, X_entrena, y_entrena, random_state: int = 42) -> float:
    """Busca el umbral de decision que maximiza el F1 macro.

    El 0.5 por defecto no tiene nada de especial: es solo el punto medio. Con
    clases desbalanceadas casi siempre conviene bajarlo, porque el modelo
    necesita mucha evidencia antes de arriesgarse con la clase rara.

    El umbral se elige con predicciones fuera de muestra sobre el conjunto de
    ENTRENAMIENTO (validacion cruzada). Elegirlo mirando el de prueba seria
    hacer trampa: las metricas finales dejarian de ser una estimacion honesta.
    """
    from sklearn.model_selection import cross_val_predict

    probabilidades = cross_val_predict(
        modelo_base, X_entrena, y_entrena,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state),
        method="predict_proba",
    )
    # La columna de la clase minoritaria segun el orden alfabetico de sklearn
    indice = sorted(set(y_entrena)).index(NO_POSITIVA)
    puntajes = probabilidades[:, indice]

    mejor_umbral, mejor_f1 = 0.5, -1.0
    for umbral in np.arange(0.10, 0.91, 0.01):
        prediccion = np.where(puntajes >= umbral, NO_POSITIVA, POSITIVA)
        f1 = f1_score(y_entrena, prediccion, average="macro", zero_division=0)
        if f1 > mejor_f1:
            mejor_f1, mejor_umbral = f1, float(umbral)

    return mejor_umbral


def entrenar_y_evaluar(df: pd.DataFrame, test_size: float = 0.25,
                       random_state: int = 42) -> Dict:
    """Entrena el modelo, lo compara contra el lexico y devuelve todo el detalle."""
    textos, etiquetas = preparar_datos(df)

    X_entrena, X_prueba, y_entrena, y_prueba = train_test_split(
        textos, etiquetas, test_size=test_size,
        random_state=random_state, stratify=etiquetas,
    )

    umbral = elegir_umbral(construir_modelo(), X_entrena, y_entrena, random_state)

    modelo = construir_modelo()
    modelo.fit(X_entrena, y_entrena)

    indice_minoritaria = list(modelo.classes_).index(NO_POSITIVA)
    y_probabilidad = modelo.predict_proba(X_prueba)[:, indice_minoritaria]

    y_predicho_05 = modelo.predict(X_prueba)
    y_predicho = np.where(y_probabilidad >= umbral, NO_POSITIVA, POSITIVA)

    resultado_umbral_fijo = evaluar("Modelo (umbral 0.50)", y_prueba, y_predicho_05, y_probabilidad)
    resultado_modelo = evaluar(f"Modelo (umbral {umbral:.2f})", y_prueba, y_predicho, y_probabilidad)
    resultado_lexico = evaluar("Lexico (linea base)", y_prueba, predecir_con_lexico(X_prueba))

    # Validacion cruzada para no depender de una sola particion
    validacion = cross_val_score(
        construir_modelo(), textos, etiquetas,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state),
        scoring="f1_macro",
    )

    # El lexico no entrena, asi que puede evaluarse sobre las 973 resenas. Es la
    # comparacion mas justa contra el F1 de validacion cruzada del modelo, porque
    # ambas cifras se apoyan en todo el conjunto y no en una sola particion.
    resultado_lexico_total = evaluar(
        "Lexico (973 resenas)", etiquetas, predecir_con_lexico(textos))

    return {
        "modelo": modelo,
        "umbral": umbral,
        "n_entrenamiento": len(X_entrena),
        "n_prueba": len(X_prueba),
        "distribucion": etiquetas.value_counts().to_dict(),
        "resultado_modelo": resultado_modelo,
        "resultado_umbral_fijo": resultado_umbral_fijo,
        "resultado_lexico": resultado_lexico,
        "resultado_lexico_total": resultado_lexico_total,
        "f1_validacion_cruzada": (float(validacion.mean()), float(validacion.std())),
        "terminos": terminos_influyentes(modelo),
    }


def main():
    df = pd.read_csv("data/processed/restaurants_clustered.csv")
    r = entrenar_y_evaluar(df)

    print("=" * 68)
    print("CLASIFICACION SUPERVISADA DE SENTIMIENTO")
    print("=" * 68)
    print(f"\nEtiqueta tomada de la calificacion del resenador (4-5 = positiva).")
    print(f"Distribucion: {r['distribucion']}")
    print(f"Entrenamiento: {r['n_entrenamiento']} resenas | Prueba: {r['n_prueba']}")

    print(f"\n{'-' * 68}\nRESULTADOS SOBRE EL CONJUNTO DE PRUEBA\n{'-' * 68}")
    print(r["resultado_lexico"].resumen())
    print(r["resultado_umbral_fijo"].resumen())
    print(r["resultado_modelo"].resumen())
    print(f"\nUmbral elegido por validacion cruzada sobre el entrenamiento: "
          f"{r['umbral']:.2f} (el 0.50 por defecto no es optimo con clases desbalanceadas)")

    print("\nComparacion sobre TODO el conjunto "
          "(el lexico no entrena, asi que no necesita particion):")
    print("  " + r["resultado_lexico_total"].resumen())

    media, desviacion = r["f1_validacion_cruzada"]
    print(f"\nF1 macro en validacion cruzada (5 particiones): {media:.3f} +/- {desviacion:.3f}")

    print(f"\nMatriz de confusion del modelo (filas = real, columnas = predicho)")
    print(f"                    {NO_POSITIVA:>12s} {POSITIVA:>12s}")
    for etiqueta, fila in zip([NO_POSITIVA, POSITIVA], r["resultado_modelo"].matriz_confusion):
        print(f"  {etiqueta:16s} {fila[0]:12d} {fila[1]:12d}")

    if r["resultado_modelo"].auc:
        print(f"\nAUC: {r['resultado_modelo'].auc:.3f}")

    print(f"\n{'-' * 68}\nQUE APRENDIO EL MODELO\n{'-' * 68}")
    for clase, terminos in r["terminos"].items():
        palabras = ", ".join(t for t, _ in terminos[:10])
        print(f"\n  Empujan hacia '{clase}':\n    {palabras}")


if __name__ == "__main__":
    main()
