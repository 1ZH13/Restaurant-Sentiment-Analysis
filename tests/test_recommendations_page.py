"""
Regression tests for the Recommendations page.

st.button is only True on the run that handled the click. The results block was
rendered inside that condition, so touching any other control made the whole
list vanish - which reads to a user as if the page did nothing. Results are now
kept in session state.
"""

from pathlib import Path

import pandas as pd
import pytest

APP = Path(__file__).parent / "_apps" / "recommendations_app.py"


@pytest.fixture(scope="module")
def app_file(tmp_path_factory):
    """A minimal Streamlit script that renders only this page."""
    directory = tmp_path_factory.mktemp("reco")
    script = directory / "app.py"
    script.write_text(
        "import os, sys\n"
        f"sys.path.insert(0, {str(Path.cwd())!r})\n"
        "import pandas as pd\n"
        "from dashboard.utils.i18n import translate_dashboard_dataframe\n"
        "from src.sentiment.aspect_scores import derive_aspect_sentiment_scores\n"
        "from dashboard.views import recomendaciones\n"
        "df = pd.read_csv('data/processed/restaurants_clustered.csv')\n"
        "df = translate_dashboard_dataframe(df)\n"
        "df = derive_aspect_sentiment_scores(df)\n"
        "recomendaciones.render(df)\n",
        encoding="utf-8",
    )
    return str(script)


@pytest.fixture
def app(app_file):
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    if not Path("data/processed/restaurants_clustered.csv").exists():
        pytest.skip("No hay datos procesados")

    at = AppTest.from_file(app_file, default_timeout=120)
    at.run()
    if at.exception:
        pytest.fail(f"La pagina fallo al iniciar: {at.exception}")
    return at


def _results(at):
    return [str(m.value) for m in at.markdown if "coincidencia" in str(m.value)]


class TestRecommendationsFlow:
    def test_starts_empty(self, app):
        assert _results(app) == []

    def test_button_produces_recommendations(self, app):
        app.button[0].click().run()
        assert not app.exception
        assert len(_results(app)) > 0

    def test_results_survive_other_widget_changes(self, app):
        """The bug: changing a filter erased the list until the button was pressed again."""
        app.button[0].click().run()
        before = len(_results(app))
        assert before > 0

        app.selectbox(key="rec_zone").set_value("Casco Antiguo").run()

        assert not app.exception
        assert len(_results(app)) == before, "las recomendaciones desaparecieron al tocar un filtro"

    def test_stale_results_are_flagged(self, app):
        app.button[0].click().run()
        app.selectbox(key="rec_zone").set_value("Casco Antiguo").run()

        info = " ".join(str(i.value) for i in app.info)
        assert "actualizar" in info.lower()

    def test_match_score_is_a_percentage(self, app):
        import re

        app.button[0].click().run()
        scores = [int(m.group(1)) for r in _results(app)
                  if (m := re.search(r"(\d+)% coincidencia", r))]

        assert scores, "no se encontro ningun porcentaje"
        assert all(0 <= s <= 100 for s in scores)
        # The old scoring landed around 1-3, so a real match must clear that.
        assert max(scores) > 10
