"""
Comprueba que modelos de Gemini funcionan de verdad con la clave de esta maquina.

Existe porque Google retira modelos para las claves nuevas sin previo aviso, y
el listado de la API no basta para saberlo: `gemini-2.5-flash` aparece en
`client.models.list()` pero al llamarlo devuelve 404 "no longer available to new
users". La unica prueba fiable es intentar generar contenido.

Uso:
    python -m src.llm.modelos_disponibles
"""

import sys
import time

from src.llm.asistente import (
    MODELO_POR_DEFECTO,
    LLMNoDisponible,
    _cargar_env,
    _leer_clave,
    hay_clave,
    motivo_no_disponible,
)

# Candidatos en orden de preferencia para este proyecto: rapidos, baratos y sin
# sufijo -preview, que es el que Google descontinua primero.
CANDIDATOS = (
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
)


def probar(cliente, modelo: str):
    """Devuelve (funciona, detalle) tras una llamada real y minima."""
    inicio = time.time()
    try:
        cliente.models.generate_content(model=modelo, contents="Responde solo: OK")
        return True, f"{time.time() - inicio:.2f}s"
    except Exception as e:
        primera_linea = str(e).split("\n")[0]
        if "404" in primera_linea:
            return False, "retirado para claves nuevas (404)"
        if "429" in primera_linea:
            return False, "sin cuota disponible (429)"
        return False, primera_linea[:70]


def main() -> int:
    if not hay_clave():
        print(f"No se puede comprobar: {motivo_no_disponible()}")
        return 1

    from google import genai

    _cargar_env()
    cliente = genai.Client(api_key=_leer_clave())

    print(f"Modelo configurado ahora: {MODELO_POR_DEFECTO}\n")
    vivos = []
    for modelo in CANDIDATOS:
        funciona, detalle = probar(cliente, modelo)
        marca = "OK   " if funciona else "FALLA"
        print(f"  {marca} {modelo:<24} {detalle}")
        if funciona:
            vivos.append(modelo)

    print()
    if not vivos:
        print("Ningun candidato responde. Revisa la clave o la cuota en "
              "https://aistudio.google.com/apikey")
        return 1

    if MODELO_POR_DEFECTO in vivos:
        print(f"El modelo configurado funciona. No hay nada que cambiar.")
    else:
        print(f"El modelo configurado NO funciona. Pon esto en tu .env:\n"
              f"    GEMINI_MODEL={vivos[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
