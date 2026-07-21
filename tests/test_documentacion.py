"""
Comprueba que la documentacion no se desincronice del codigo ni del modelo.

Existe por un defecto real: el README declaraba "997 resenas de 207
restaurantes" cuando el conjunto de datos ya tenia 1108 y 241. Nadie se dio
cuenta porque ningun test miraba la documentacion. Estos tests cierran esa via.
"""

import glob
import io
import json
import re
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "powerbi" / "Restaurantes.SemanticModel" / "definition"
INFORME = RAIZ / "powerbi" / "Restaurantes.Report" / "definition" / "pages"
CSV = RAIZ / "data" / "processed" / "restaurants_clustered.csv"


def leer(ruta):
    return io.open(ruta, encoding="utf-8").read()


@pytest.fixture(scope="module")
def datos():
    if not CSV.exists():
        pytest.skip("hace falta correr el pipeline")
    return pd.read_csv(CSV)


@pytest.fixture(scope="module")
def doc():
    return leer(RAIZ / "powerbi" / "CONSTRUCCION.md")


@pytest.fixture(scope="module")
def tmdl():
    return "".join(leer(f) for f in glob.glob(str(MODELO / "**" / "*.tmdl"), recursive=True))


class TestCifrasDeLaDocumentacion:
    """Las cifras que se citan en los documentos deben ser las reales."""

    @pytest.mark.parametrize("documento", ["README.md", "docs/MODELOS.md"])
    def test_no_quedan_cifras_viejas(self, documento):
        """997 resenas / 207 restaurantes fueron cifras reales de una version
        anterior del dataset. Si reaparecen, alguien copio texto obsoleto."""
        texto = leer(RAIZ / documento)
        assert "997 reseñas" not in texto
        assert "207 restaurantes" not in texto

    def test_el_readme_cita_el_tamano_real(self, datos):
        texto = leer(RAIZ / "README.md")
        assert str(len(datos)) in texto, f"el README no menciona las {len(datos)} reseñas"
        assert str(datos["restaurant_id"].nunique()) in texto


class TestDocumentacionDePowerBI:
    """CONSTRUCCION.md documenta el modelo paso a paso: debe reflejarlo tal cual."""

    def _medidas_del_modelo(self, tmdl):
        return {m.strip("'") for m in re.findall(r"^\tmeasure ('.*?'|\S+) =", tmdl, re.M)}

    def _medidas_documentadas(self, doc):
        encontradas = set()
        for bloque in re.findall(r"```dax\n(.*?)```", doc, re.S):
            for linea in bloque.split("\n"):
                if linea.startswith((" ", "\t", "VAR ", "RETURN")):
                    continue
                m = re.match(r"^([A-Za-zÁÉÍÓÚÑáéíóúñ%][^=]*?) =(?!=)", linea)
                # un nombre de medida no lleva parentesis: si los lleva, es una
                # linea de DAX que continua de la anterior
                if m and not re.search(r"[()\[\]]", m.group(1)):
                    encontradas.add(m.group(1).strip())
        encontradas.discard("Calendario")  # tabla calculada, no medida
        return encontradas

    def test_todas_las_medidas_estan_documentadas(self, doc, tmdl):
        faltan = self._medidas_del_modelo(tmdl) - self._medidas_documentadas(doc)
        assert not faltan, f"medidas sin documentar en CONSTRUCCION.md: {sorted(faltan)}"

    def test_no_se_documentan_medidas_inexistentes(self, doc, tmdl):
        sobran = self._medidas_documentadas(doc) - self._medidas_del_modelo(tmdl)
        assert not sobran, f"documentadas pero no existen en el modelo: {sorted(sobran)}"

    def test_todos_los_visuales_estan_documentados(self, doc):
        for vf in glob.glob(str(INFORME / "*" / "visuals" / "*" / "visual.json")):
            nombre = json.loads(leer(vf))["name"]
            assert nombre in doc, f"visual sin documentar: {nombre}"

    def test_el_codigo_m_documentado_es_el_real(self, doc, tmdl):
        """Cada linea de Power Query citada debe existir literalmente en el TMDL."""
        normalizar = lambda s: re.sub(r"\s+", " ", s).strip()
        tmdl_n = normalizar(tmdl)
        prefijos = ("Origen =", "Encabezados =", "ConIndice =", "Columnas =", "Unicos =",
                    "Renombrado =", "Tipos =", "Todos =", "Etiquetas =", "Logico =",
                    "Orden =", "Sel =", "Ren =", "Con =")
        for bloque in re.findall(r"```m\n(.*?)```", doc, re.S):
            for linea in bloque.split("\n"):
                linea = linea.strip()
                if linea.startswith(prefijos):
                    assert normalizar(linea) in tmdl_n, f"código M desactualizado: {linea[:70]}"


class TestCoherenciaDelModelo:
    """Defectos reales que el modelo tuvo y no deben volver."""

    def test_toda_tabla_esta_registrada_en_el_modelo(self):
        """La tabla Aspecto existia como archivo y tenia relacion, pero faltaba
        'ref table Aspecto' en model.tmdl, asi que el modelo la ignoraba."""
        modelo = leer(MODELO / "model.tmdl")
        for archivo in glob.glob(str(MODELO / "tables" / "*.tmdl")):
            nombre = re.search(r"^table (.+)$", leer(archivo), re.M).group(1).strip()
            assert f"ref table {nombre}" in modelo, f"tabla no registrada en model.tmdl: {nombre}"

    def test_las_relaciones_apuntan_a_tablas_existentes(self):
        rel = leer(MODELO / "relationships.tmdl")
        tablas = {re.search(r"^table (.+)$", leer(f), re.M).group(1).strip()
                  for f in glob.glob(str(MODELO / "tables" / "*.tmdl"))}
        for referencia in re.findall(r"(?:from|to)Column: (.+?)\.", rel):
            assert referencia.strip() in tablas, f"relación a tabla inexistente: {referencia}"

    def test_los_titulos_van_en_visualcontainerobjects(self):
        """En PBIR el titulo del contenedor va en visualContainerObjects. Puesto
        en 'objects' se ignora en silencio y el visual sale sin titulo."""
        for vf in glob.glob(str(INFORME / "*" / "visuals" / "*" / "visual.json")):
            visual = json.loads(leer(vf)).get("visual", {})
            assert "title" not in visual.get("objects", {}), (
                f"{Path(vf).parent.name}: el título está en 'objects' y no se mostrará")

    def test_todos_los_visuales_tienen_titulo(self):
        for vf in glob.glob(str(INFORME / "*" / "visuals" / "*" / "visual.json")):
            visual = json.loads(leer(vf)).get("visual", {})
            assert visual.get("visualContainerObjects", {}).get("title"), (
                f"{Path(vf).parent.name}: sin título")

    def test_los_archivos_del_informe_son_utf8_sin_bom(self):
        """El BOM rompe la lectura de Power BI y la ñ se corrompe sin UTF-8."""
        for vf in glob.glob(str(INFORME / "**" / "*.json"), recursive=True):
            crudo = io.open(vf, "rb").read()
            assert not crudo.startswith(b"\xef\xbb\xbf"), f"{vf} tiene BOM"
            crudo.decode("utf-8")  # lanza si no es UTF-8 valido
