"""
Asistente con modelo de lenguaje.

Dos usos, ambos sobre los datos del proyecto:

- Preguntar en lenguaje natural y obtener una respuesta apoyada en las cifras.
- Pedir un resumen de lo que dicen las resenas de un restaurante.

El modelo recibe un contexto con los agregados del proyecto, no las 1108
resenas. Ademas se le instruye que diga cuando un dato no esta disponible en vez
de inventarlo, y la pagina muestra el contexto exacto que se envio para que
cualquiera pueda verificar de donde sale la respuesta.
"""

import pandas as pd
import streamlit as st

from dashboard.utils.restaurants import restaurant_directory

try:
    from src.llm.asistente import (
        AsistenteDatos,
        LLMNoDisponible,
        construir_contexto,
        hay_clave,
        motivo_no_disponible,
    )
except ImportError:  # pragma: no cover
    AsistenteDatos = None

PREGUNTAS_SUGERIDAS = [
    "¿Qué aspecto sale peor valorado y por qué crees que es?",
    "¿Qué zona concentra más reseñas y cómo es su sentimiento?",
    "¿Los restaurantes más caros tienen mejor sentimiento que los baratos?",
    "¿Cuál es el restaurante peor calificado y qué tan confiable es ese dato?",
]


def _sin_llm() -> None:
    """Explica como habilitar el asistente, sin romper la página."""
    st.warning("El asistente no está disponible en esta máquina.")
    st.markdown(f"**Motivo:** {motivo_no_disponible()}")
    st.markdown("""
    El resto del proyecto funciona sin esto: el análisis de sentimiento se hace
    con un léxico propio y el modelo de clasificación con scikit-learn. El
    asistente es una capa adicional para consultar los datos en lenguaje natural.
    """)


@st.cache_data(show_spinner=False)
def _contexto(df: pd.DataFrame) -> str:
    return construir_contexto(df)


def render(df: pd.DataFrame):
    """Render the LLM assistant page."""

    st.markdown("### Pregunta sobre los datos")

    if AsistenteDatos is None or not hay_clave():
        _sin_llm()
        return

    st.caption("Las respuestas se apoyan solo en los datos del proyecto. "
               "Si algo no está en los datos, el asistente debe decirlo en vez de inventarlo.")

    contexto = _contexto(df)

    pestana_preguntas, pestana_resumen = st.tabs(
        ["Preguntar en lenguaje natural", "Resumir un restaurante"])

    # ------------------------------------------------------------- preguntas
    with pestana_preguntas:
        sugerida = st.selectbox(
            "Preguntas de ejemplo",
            ["(escribir la mía)"] + PREGUNTAS_SUGERIDAS,
            key="llm_sugerida",
        )
        valor = "" if sugerida == "(escribir la mía)" else sugerida

        pregunta = st.text_area(
            "Tu pregunta", value=valor, height=80, key="llm_pregunta",
            placeholder="Por ejemplo: ¿qué cocina tiene el mejor sentimiento en servicio?",
        )

        if st.button("Preguntar", type="primary", key="llm_enviar"):
            if not pregunta.strip():
                st.info("Escribe una pregunta primero.")
            else:
                try:
                    with st.spinner("Consultando..."):
                        respuesta = AsistenteDatos().responder_pregunta(pregunta, contexto)
                    st.session_state["llm_respuesta"] = respuesta.texto
                except LLMNoDisponible as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"No se pudo obtener respuesta: {e}")

        if st.session_state.get("llm_respuesta"):
            st.markdown("#### Respuesta")
            st.markdown(st.session_state["llm_respuesta"])

        with st.expander("Ver exactamente qué datos recibió el modelo"):
            st.code(contexto, language="text")
            st.caption("El modelo no ve las reseñas individuales: recibe estos agregados. "
                       "Así se evita que invente cifras y se mantiene el costo bajo.")

    # --------------------------------------------------------------- resumen
    with pestana_resumen:
        directorio = restaurant_directory(df)
        con_resenas = directorio[directorio["resenas"] >= 2]

        if con_resenas.empty:
            st.info("No hay restaurantes con suficientes reseñas para resumir.")
            return

        busqueda = st.text_input("Buscar restaurante", key="llm_busqueda",
                                 placeholder="Escribe parte del nombre...")
        opciones = con_resenas
        if busqueda.strip():
            mascara = opciones["restaurant_name"].astype(str).str.lower().str.contains(
                busqueda.strip().lower(), regex=False)
            opciones = opciones[mascara]

        if opciones.empty:
            st.warning("Ningún restaurante coincide con esa búsqueda.")
            return

        lookup = opciones.set_index("restaurant_id")
        elegido = st.selectbox(
            "Restaurante",
            options=opciones["restaurant_id"].tolist(),
            format_func=lambda r: f"{lookup.loc[r, 'restaurant_name']} "
                                  f"({int(lookup.loc[r, 'resenas'])} reseñas)",
            key="llm_restaurante",
        )

        if st.button("Resumir sus reseñas", type="primary", key="llm_resumir"):
            resenas = df.loc[df["restaurant_id"] == elegido, "review_text"].dropna().tolist()
            nombre = str(lookup.loc[elegido, "restaurant_name"])
            try:
                with st.spinner("Leyendo las reseñas..."):
                    respuesta = AsistenteDatos().resumir_restaurante(nombre, resenas)
                st.session_state["llm_resumen"] = (nombre, respuesta.texto, respuesta.contexto_usado)
            except LLMNoDisponible as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"No se pudo generar el resumen: {e}")

        if st.session_state.get("llm_resumen"):
            nombre, texto, usado = st.session_state["llm_resumen"]
            st.markdown(f"#### {nombre}")
            st.markdown(texto)
            st.caption(f"Resumen generado a partir de {usado}.")
