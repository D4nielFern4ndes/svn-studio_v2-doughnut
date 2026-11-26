"""Test de fumée de l'interface : chaque page s'ouvre sans erreur, avec les deux exemples."""
from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(p.name for p in (ROOT / "views").glob("*.py"))


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("example", ["essai_de_jeu", "vide"])
def test_page(page, example):
    from svn_core import examples

    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    from svn_core import Project

    at.session_state["project"] = examples.essai_de_jeu() if example == "essai_de_jeu" else Project()
    at.run()
    at.switch_page(f"views/{page}")
    at.run()
    assert not at.exception, at.exception


def test_page_comparaison_avec_deux_scenarios():
    """La page de comparaison s'affiche avec T0 (scénario A) et T1 (scénario B)."""
    from svn_core import io as svn_io

    d = ROOT / "data" / "examples" / "doughnut"
    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    at.session_state["project"] = svn_io.load_json((d / "T0_base.json").read_text(encoding="utf-8"))
    at.session_state["compare_b"] = svn_io.load_json(
        (d / "T1_doughnut_global.json").read_text(encoding="utf-8"))
    at.run()
    at.switch_page("views/comparaison.py")
    at.run()
    assert not at.exception, at.exception
    assert len(at.dataframe) >= 3
    assert any("Doughnut" in c.value for c in at.caption)


@pytest.mark.parametrize("page", ["cycles.py", "priorisation.py"])
def test_avertissement_acteur_hors_cycles(page):
    """Avec T1, les pages Cycles et Priorisation (WSO) signalent le Doughnut hors des cycles."""
    from svn_core import io as svn_io

    d = ROOT / "data" / "examples" / "doughnut"
    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    at.session_state["project"] = svn_io.load_json(
        (d / "T1_doughnut_global.json").read_text(encoding="utf-8"))
    at.run()
    at.switch_page(f"views/{page}")
    at.run()
    assert not at.exception, at.exception
    assert any("Doughnut" in i.value and "aucun cycle" in i.value for i in at.info)


def test_page_comparaison_avec_tableau_de_flux_en_scenario_b():
    """Scénario B construit à partir d'un tableau de flux (sans projet central dans le fichier)."""
    from svn_core import examples
    from svn_core import io as svn_io

    a = examples.essai_de_jeu()
    b = svn_io.read_file("b.xlsx", svn_io.flows_xlsx(a)).to_project("B", a.name_of(a.focal))
    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    at.session_state["project"] = a
    at.session_state["compare_b"] = b
    at.run()
    at.switch_page("views/comparaison.py")
    at.run()
    assert not at.exception, at.exception
    assert len(at.dataframe) >= 3


@pytest.mark.parametrize("couleur", ["Par catégorie", "Par origine", "Uniforme"])
@pytest.mark.parametrize("mode", ["Rien", "Un cycle", "Une partie prenante"])
def test_carte_du_reseau_options(couleur, mode):
    """La carte s'affiche avec chaque couleur de flèches et chaque mise en évidence, zoom molette actif."""
    import json as _json

    from svn_core import examples

    at = st_testing.AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    at.session_state["project"] = examples.essai_de_jeu()
    at.run()
    at.switch_page("views/reseau.py")
    at.run()
    at.radio(key="net_edge_color").set_value(couleur)
    at.radio(key="net_mode").set_value(mode)
    at.run()
    assert not at.exception, at.exception
    chart = at.get("plotly_chart")[0].proto
    assert _json.loads(chart.spec)["layout"]["dragmode"] == "pan"
    assert _json.loads(chart.config)["scrollZoom"] is True
