"""
Asistente basado en un modelo de lenguaje (Google Gemini).

Cubre los tres usos que el proyecto necesita del LLM:

1. Resumir las resenas de un restaurante en unas pocas frases.
2. Responder preguntas en lenguaje natural sobre el conjunto de datos.
3. Clasificar el sentimiento de una resena, para poder comparar al LLM contra el
   lexico y contra el modelo supervisado.

Sobre como se responden las preguntas
-------------------------------------
El modelo NO recibe las 1108 resenas: no cabrian y saldria caro. Se le arma un
contexto compacto con los agregados que ya calcula el proyecto (totales,
sentimiento por aspecto, mejores restaurantes, cocinas, zonas) y se le pide que
responda usando solo eso. Si la respuesta no esta en el contexto, se le indica
que lo diga en lugar de inventar.

Es la diferencia entre un asistente util y uno que alucina cifras, que en un
trabajo de analisis de datos seria peor que no tenerlo.
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

try:
    # SDK actual de Google. El anterior (google.generativeai) esta descontinuado:
    # avisa en cada importacion que ya no recibe correcciones.
    from google import genai
except ImportError:  # pragma: no cover
    genai = None

# Google retira modelos para las claves nuevas sin previo aviso: gemini-2.0-flash
# y gemini-2.5-flash ya devuelven 404/429 aunque sigan apareciendo en el listado
# de la API. Si el asistente empieza a fallar, comprobar cual sigue vivo con:
#     python -m src.llm.modelos_disponibles
MODELO_POR_DEFECTO = "gemini-3.5-flash"

# El SDK de Google acepta la clave con cualquiera de estos dos nombres, asi que
# los aceptamos tambien aqui: si solo estuviera GEMINI_API_KEY, el dashboard
# diria "no disponible" aunque la libreria si pudiera conectarse.
NOMBRES_DE_CLAVE = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


class LLMNoDisponible(RuntimeError):
    """Se lanza cuando falta la clave o el paquete del LLM."""


def _cargar_env() -> None:
    """Lee el archivo .env si existe, sin exigir python-dotenv."""
    ruta = ".env"
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def _leer_clave() -> str:
    """Devuelve la clave de la API, mirando los dos nombres que acepta el SDK."""
    for nombre in NOMBRES_DE_CLAVE:
        valor = os.environ.get(nombre)
        if valor:
            return valor
    return ""


def hay_clave() -> bool:
    """Indica si el asistente puede funcionar en esta maquina."""
    _cargar_env()
    return genai is not None and bool(_leer_clave())


def motivo_no_disponible() -> str:
    """Explica en una frase por que no se puede usar el asistente."""
    if genai is None:
        return ("Falta el paquete google-genai. "
                "Instalalo con: pip install -r requirements.txt")
    _cargar_env()
    if not _leer_clave():
        return ("Falta la clave de la API. Crea un archivo .env en la raiz del "
                "proyecto con GOOGLE_API_KEY=tu_clave. La clave es gratuita y se "
                "obtiene en https://aistudio.google.com/apikey")
    return ""


@dataclass
class Respuesta:
    """Respuesta del asistente junto con el contexto que se le paso."""

    texto: str
    contexto_usado: str = ""


class AsistenteDatos:
    """Envuelve al modelo de lenguaje con el contexto del proyecto."""

    def __init__(self, modelo: Optional[str] = None):
        if not hay_clave():
            raise LLMNoDisponible(motivo_no_disponible())
        _cargar_env()
        self.cliente = genai.Client(api_key=_leer_clave())
        self.nombre_modelo = modelo or os.environ.get("GEMINI_MODEL", MODELO_POR_DEFECTO)

    # ------------------------------------------------------------------ interno
    def _generar(self, prompt: str) -> str:
        respuesta = self.cliente.models.generate_content(
            model=self.nombre_modelo, contents=prompt)
        return (respuesta.text or "").strip()

    # ------------------------------------------------------------------ resumen
    def resumir_restaurante(self, nombre: str, resenas: List[str],
                            maximo: int = 25) -> Respuesta:
        """Resume que dicen las resenas de un restaurante."""
        # Ojo con el orden: hay que descartar los nulos ANTES de convertir a
        # texto, porque str(None) es "None" y str(nan) es "nan" -- ambos son
        # cadenas no vacias que se colarian al prompt como si fueran resenas.
        muestra = [texto for texto in (str(r).strip() for r in resenas
                                       if r is not None and not pd.isna(r))
                   if texto][:maximo]
        if not muestra:
            return Respuesta("Este restaurante no tiene resenas con texto.")

        listado = "\n".join(f"- {r}" for r in muestra)
        prompt = f"""Eres un analista de datos que resume opiniones de clientes.

Resenas de "{nombre}" ({len(muestra)} de {len(resenas)}):
{listado}

Escribe en espanol de Panama, en un parrafo corto y directo:
1. Que destacan los clientes como lo mejor.
2. Que critican, si es que critican algo.
3. Para quien recomendarias el lugar.

Reglas:
- Basate SOLO en las resenas de arriba.
- No inventes cifras ni platos que no aparezcan.
- Si las resenas no critican nada, dilo en lugar de inventar una critica.
- Maximo 120 palabras."""
        return Respuesta(self._generar(prompt), f"{len(muestra)} resenas")

    # ------------------------------------------------- preguntas sobre los datos
    def responder_pregunta(self, pregunta: str, contexto: str) -> Respuesta:
        """Responde una pregunta en lenguaje natural usando el contexto dado."""
        prompt = f"""Eres un analista de datos. Respondes preguntas sobre un conjunto
de resenas de restaurantes de Ciudad de Panama usando UNICAMENTE los datos que
se te entregan abajo.

DATOS DISPONIBLES:
{contexto}

PREGUNTA: {pregunta}

Reglas:
- Usa solo los datos de arriba. No uses conocimiento general sobre restaurantes.
- Si la respuesta no esta en los datos, di exactamente que dato faltaria para
  responderla. No la inventes ni la estimes.
- Cita las cifras concretas en las que te apoyas.
- Responde en espanol, en pocas frases.
- El sentimiento va de -1 a 1 y solo promedia las resenas que mencionan el aspecto."""
        return Respuesta(self._generar(prompt), contexto)

    # ------------------------------------------------------------ clasificacion
    def clasificar_sentimiento(self, texto: str) -> Dict[str, str]:
        """Clasifica una resena por aspecto, en el mismo formato que el lexico."""
        prompt = f"""Clasifica el sentimiento de esta resena de restaurante para cada aspecto.

Resena: "{texto}"

Responde SOLO con un JSON valido, sin explicaciones ni markdown:
{{"comida": "positive|negative|neutral", "servicio": "positive|negative|neutral",
"precio": "positive|negative|neutral", "ambiente": "positive|negative|neutral"}}

Usa "neutral" si la resena no habla de ese aspecto."""
        crudo = self._generar(prompt)
        aspectos = ("comida", "servicio", "precio", "ambiente")
        try:
            encontrado = re.search(r"\{.*\}", crudo, re.DOTALL)
            datos = json.loads(encontrado.group(0)) if encontrado else {}
        except (json.JSONDecodeError, AttributeError):
            datos = {}
        return {a: str(datos.get(a, "neutral")).lower() for a in aspectos}


# --------------------------------------------------------------------- contexto
def construir_contexto(df: pd.DataFrame, maximo_filas: int = 12) -> str:
    """Resume el conjunto de datos en un texto compacto para el modelo.

    Se envian agregados, no filas crudas: alcanza para responder la mayoria de
    las preguntas y mantiene el prompt en un tamano razonable.
    """
    from dashboard.utils.aspects import all_aspect_summaries
    from src.preprocessing.calidad import nota_de_limitacion, ratings_sospechosos

    partes: List[str] = []
    partes.append(
        f"RESUMEN GENERAL\n"
        f"- Resenas: {len(df)}\n"
        f"- Restaurantes: {df['restaurant_id'].nunique()}\n"
        f"- Fuentes: {', '.join(sorted(df['source'].dropna().unique()))}\n"
    )

    if "overall_rating" in df.columns:
        notas = df["overall_rating"].dropna()
        if len(notas):
            partes.append(f"- Calificacion promedio: {notas.mean():.2f} de 5\n")

    resumenes = all_aspect_summaries(df)
    if resumenes:
        lineas = [f"  {r['label']}: sentimiento {r['mean']:+.2f}, "
                  f"lo mencionan {r['mentions']} resenas ({r['coverage']*100:.0f}%)"
                  for r in resumenes]
        partes.append("SENTIMIENTO POR ASPECTO\n" + "\n".join(lineas) + "\n")

    mejores = (df.dropna(subset=["overall_rating"])
                 .groupby("restaurant_name", as_index=False)
                 .agg(nota=("overall_rating", "mean"), resenas=("review_text", "size"))
                 .sort_values("nota", ascending=False)
                 .head(maximo_filas))
    if len(mejores):
        lineas = [f"  {r.restaurant_name}: {r.nota:.1f} ({int(r.resenas)} resenas)"
                  for r in mejores.itertuples()]
        partes.append("MEJOR CALIFICADOS\n" + "\n".join(lineas) + "\n")

    # Los restaurantes con la calificacion corrupta de RestaurantGuru se apartan
    # del ranking: si entraran, el asistente afirmaria con total seguridad que el
    # peor restaurante es uno cuyas resenas son elogiosas.
    sospechosos = ratings_sospechosos(df)
    nombres_dudosos = set(sospechosos["restaurant_name"])

    peores = (df.dropna(subset=["overall_rating"])
                .loc[lambda d: ~d["restaurant_name"].isin(nombres_dudosos)]
                .groupby("restaurant_name", as_index=False)
                .agg(nota=("overall_rating", "mean"), resenas=("review_text", "size"))
                .sort_values("nota")
                .head(6))
    if len(peores):
        lineas = [f"  {r.restaurant_name}: {r.nota:.1f} ({int(r.resenas)} resenas)"
                  for r in peores.itertuples()]
        partes.append("PEOR CALIFICADOS\n" + "\n".join(lineas) + "\n")

    aviso = nota_de_limitacion(sospechosos)
    if aviso:
        partes.append("LIMITACION CONOCIDA DE LOS DATOS\n  " + aviso +
                      "\n  Si te preguntan por el peor restaurante, menciona esta "
                      "limitacion en lugar de dar por buena esa calificacion.\n")

    columna_cocina = "category_primary" if "category_primary" in df.columns else "category"
    if columna_cocina in df.columns:
        cocinas = df[columna_cocina].dropna().value_counts().head(10)
        partes.append("COCINAS CON MAS RESENAS\n" +
                      "\n".join(f"  {c}: {n}" for c, n in cocinas.items()) + "\n")

    if "location" in df.columns:
        zonas = df["location"].dropna().value_counts().head(10)
        partes.append("ZONAS CON MAS RESENAS\n" +
                      "\n".join(f"  {z}: {n}" for z, n in zonas.items()) + "\n")

    if "price_band" in df.columns:
        precios = df["price_band"].dropna().value_counts().sort_index()
        partes.append("RANGOS DE PRECIO\n" +
                      "\n".join(f"  {p}: {n} resenas" for p, n in precios.items()) + "\n")

    if "cluster_name" in df.columns:
        grupos = (df.groupby("cluster_name")
                    .agg(restaurantes=("restaurant_id", "nunique"))
                    .sort_values("restaurantes", ascending=False))
        partes.append("GRUPOS DEL CLUSTERING\n" +
                      "\n".join(f"  {g}: {r.restaurantes} restaurantes"
                                for g, r in grupos.iterrows()) + "\n")

    return "\n".join(partes)
