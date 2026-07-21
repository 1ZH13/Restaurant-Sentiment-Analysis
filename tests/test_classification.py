"""
Pruebas del modelo supervisado y del asistente con LLM.

Las del LLM no llaman a la API: verifican que el modulo se comporte bien cuando
NO hay clave, que es el estado en el que se va a encontrar cualquiera que clone
el repositorio, y que el contexto que se le enviaria al modelo contenga las
cifras correctas.
"""

import numpy as np
import pandas as pd
import pytest

from src.classification.sentiment_classifier import (
    NO_POSITIVA,
    POSITIVA,
    construir_modelo,
    entrenar_y_evaluar,
    etiquetar,
    evaluar,
    preparar_datos,
    terminos_influyentes,
)


@pytest.fixture
def resenas():
    """Conjunto pequeno pero con las dos clases y suficientes filas para entrenar."""
    positivas = [
        "La comida estuvo excelente y el servicio muy amable",
        "Todo delicioso, volveremos sin duda",
        "Excelente ambiente y platos deliciosos",
        "Muy buena atencion, la pasta espectacular",
        "Rico todo, precios justos y buen trato",
        "El mejor sushi que he probado en la ciudad",
        "Servicio rapido y comida sabrosa",
        "Lugar acogedor con muy buena comida",
        "Recomendado, la carne en su punto",
        "Postres exquisitos y personal atento",
    ] * 3
    negativas = [
        "La comida llego fria y el servicio fue lento",
        "Muy caro para lo que ofrecen, no volveria",
        "Pesimo servicio, esperamos una hora",
        "La carne estaba dura y sin sabor",
        "Local sucio y ruidoso, mala experiencia",
    ] * 3

    textos = positivas + negativas
    notas = [5.0] * len(positivas) + [2.0] * len(negativas)
    return pd.DataFrame({"review_text": textos, "review_rating": notas})


class TestEtiquetado:
    """La etiqueta sale de las estrellas del resenador, no del lexico."""

    @pytest.mark.parametrize("estrellas,esperado", [
        (5.0, POSITIVA), (4.0, POSITIVA),
        (3.0, NO_POSITIVA), (2.0, NO_POSITIVA), (1.0, NO_POSITIVA),
    ])
    def test_umbral_de_estrellas(self, estrellas, esperado):
        assert etiquetar(estrellas) == esperado

    def test_sin_calificacion_no_se_etiqueta(self):
        assert etiquetar(float("nan")) is None

    def test_solo_usa_resenas_con_calificacion(self):
        df = pd.DataFrame({
            "review_text": ["buena", "mala", "sin nota"],
            "review_rating": [5.0, 1.0, None],
        })
        textos, etiquetas = preparar_datos(df)
        assert len(textos) == 2
        assert set(etiquetas) == {POSITIVA, NO_POSITIVA}

    def test_descarta_texto_vacio(self):
        df = pd.DataFrame({"review_text": ["buena", "   "], "review_rating": [5.0, 1.0]})
        textos, _ = preparar_datos(df)
        assert len(textos) == 1


class TestModelo:
    def test_aprende_a_separar_las_clases(self, resenas):
        textos, etiquetas = preparar_datos(resenas)
        modelo = construir_modelo()
        modelo.fit(textos, etiquetas)

        assert modelo.predict(["comida deliciosa y excelente servicio"])[0] == POSITIVA
        assert modelo.predict(["pesimo servicio, todo frio y caro"])[0] == NO_POSITIVA

    def test_devuelve_probabilidades(self, resenas):
        textos, etiquetas = preparar_datos(resenas)
        modelo = construir_modelo().fit(textos, etiquetas)
        probabilidades = modelo.predict_proba(["comida excelente"])
        assert probabilidades.shape == (1, 2)
        assert probabilidades.sum() == pytest.approx(1.0)

    def test_terminos_influyentes_son_interpretables(self, resenas):
        textos, etiquetas = preparar_datos(resenas)
        modelo = construir_modelo().fit(textos, etiquetas)
        terminos = terminos_influyentes(modelo, cantidad=5)

        assert set(terminos) == {POSITIVA, NO_POSITIVA}
        assert all(len(v) == 5 for v in terminos.values())
        # El peso empuja hacia su clase, no en contra
        assert all(peso > 0 for _, peso in terminos[POSITIVA]) or \
               all(peso < 0 for _, peso in terminos[POSITIVA])


class TestMetricas:
    def test_la_exactitud_no_basta_con_clases_desbalanceadas(self):
        """Un modelo que responde siempre 'positiva' acierta mucho y no sirve."""
        real = [POSITIVA] * 90 + [NO_POSITIVA] * 10
        constante = [POSITIVA] * 100

        r = evaluar("constante", real, constante)

        assert r.exactitud == pytest.approx(0.90)
        # ...pero no detecta ni una sola de la clase que importa
        assert r.exhaustividad_minoritaria == 0.0
        assert r.f1_macro < 0.5

    def test_matriz_de_confusion_tiene_forma_correcta(self):
        real = [POSITIVA, NO_POSITIVA, POSITIVA]
        predicho = [POSITIVA, POSITIVA, POSITIVA]
        r = evaluar("prueba", real, predicho)
        assert np.array(r.matriz_confusion).shape == (2, 2)


class TestEvaluacionCompleta:
    def test_entrena_compara_y_reporta(self, resenas):
        r = entrenar_y_evaluar(resenas, test_size=0.3)

        assert r["n_entrenamiento"] > 0 and r["n_prueba"] > 0
        assert 0.0 <= r["resultado_modelo"].exactitud <= 1.0
        assert 0.0 <= r["resultado_lexico"].exactitud <= 1.0
        assert 0.1 <= r["umbral"] <= 0.9
        media, desviacion = r["f1_validacion_cruzada"]
        assert 0.0 <= media <= 1.0 and desviacion >= 0.0

    def test_incluye_la_linea_base_del_lexico(self, resenas):
        """Sin comparacion no se puede afirmar que el modelo aporte algo."""
        r = entrenar_y_evaluar(resenas, test_size=0.3)
        assert "resultado_lexico" in r
        assert r["resultado_lexico"].nombre.startswith("Lexico")


class TestAsistenteSinClave:
    """El proyecto debe funcionar sin clave de API."""

    def test_informa_el_motivo_en_lugar_de_fallar(self, monkeypatch):
        from src.llm import asistente

        for nombre in asistente.NOMBRES_DE_CLAVE:
            monkeypatch.delenv(nombre, raising=False)
        monkeypatch.setattr(asistente, "_cargar_env", lambda: None)

        assert asistente.hay_clave() is False
        motivo = asistente.motivo_no_disponible()
        assert "GOOGLE_API_KEY" in motivo or "google-genai" in motivo

    def test_construir_asistente_lanza_error_claro(self, monkeypatch):
        from src.llm import asistente

        for nombre in asistente.NOMBRES_DE_CLAVE:
            monkeypatch.delenv(nombre, raising=False)
        monkeypatch.setattr(asistente, "_cargar_env", lambda: None)

        with pytest.raises(asistente.LLMNoDisponible):
            asistente.AsistenteDatos()

    def test_acepta_la_clave_con_el_nombre_alterno(self, monkeypatch):
        """El SDK acepta GEMINI_API_KEY, asi que el dashboard tambien debe."""
        from src.llm import asistente

        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
        monkeypatch.setattr(asistente, "_cargar_env", lambda: None)

        assert asistente.hay_clave() is True

    def test_el_modelo_por_defecto_coincide_con_env_example(self):
        """Si .env.example documenta un modelo, el default no puede ser otro."""
        from src.llm import asistente

        with open(".env.example", encoding="utf-8") as f:
            documentado = next(l.split("=", 1)[1].strip()
                               for l in f if l.startswith("GEMINI_MODEL="))
        assert asistente.MODELO_POR_DEFECTO == documentado


class TestResumenDeResenas:
    """El resumen no debe mandarle basura al modelo."""

    def _asistente_falso(self, monkeypatch):
        from src.llm import asistente

        monkeypatch.setenv("GOOGLE_API_KEY", "clave-de-prueba")
        monkeypatch.setattr(asistente, "_cargar_env", lambda: None)

        enviados = {}

        class FakeModels:
            def generate_content(self, model, contents):
                enviados["prompt"] = contents
                return type("R", (), {"text": "resumen"})()

        class FakeClient:
            def __init__(self, **kw):
                self.models = FakeModels()

        monkeypatch.setattr(asistente.genai, "Client", FakeClient)
        return asistente.AsistenteDatos(), enviados

    def test_descarta_nulos_en_lugar_de_mandarlos_como_texto(self, monkeypatch):
        """str(None) es 'None': si no se filtra antes, llega al prompt."""
        import numpy as np

        a, _ = self._asistente_falso(monkeypatch)
        respuesta = a.resumir_restaurante("X", [None, np.nan, "   "])
        assert "no tiene resenas con texto" in respuesta.texto

    def test_los_nulos_no_se_cuelan_al_prompt(self, monkeypatch):
        a, enviados = self._asistente_falso(monkeypatch)
        a.resumir_restaurante("X", ["comida rica", None])

        assert "- None" not in enviados["prompt"]
        assert "comida rica" in enviados["prompt"]


class TestContextoDelLLM:
    """El contexto es lo unico que ve el modelo: debe traer las cifras correctas."""

    @pytest.fixture
    def datos(self):
        return pd.DataFrame({
            "restaurant_id": ["r1", "r1", "r2"],
            "restaurant_name": ["Sushi Uno", "Sushi Uno", "Pizza Nova"],
            "review_text": ["excelente", "muy bueno", "regular"],
            "overall_rating": [4.8, 4.8, 3.2],
            "source": ["degusta", "degusta", "restaurantguru"],
            "category_primary": ["Japonesa", "Japonesa", "Italiana"],
            "location": ["Obarrio", "Obarrio", "Marbella"],
            "price_band": ["$$ ($15-$25)"] * 3,
            "sentiment_comida_score": [1.0, 1.0, 0.0],
            "mentions_comida": [True, True, True],
        })

    def test_incluye_totales_reales(self, datos):
        from src.llm.asistente import construir_contexto
        contexto = construir_contexto(datos)
        assert "Resenas: 3" in contexto
        assert "Restaurantes: 2" in contexto

    def test_incluye_ambas_fuentes(self, datos):
        from src.llm.asistente import construir_contexto
        contexto = construir_contexto(datos)
        assert "degusta" in contexto and "restaurantguru" in contexto

    def test_no_incluye_el_texto_de_las_resenas(self, datos):
        """Se envian agregados, no filas: evita alucinaciones y abarata la llamada."""
        from src.llm.asistente import construir_contexto
        contexto = construir_contexto(datos)
        assert "muy bueno" not in contexto
