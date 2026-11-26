"""Lecteur unique des fichiers importés (étape 1 et comparaison) : CSV, TXT, JSON et XLSX."""
import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from svn_core import examples, find_cycles
from svn_core import io as svn_io

ROOT = Path(__file__).resolve().parents[1]
CSV = "origine;destination;nom;score\nProjet;Population;Service;0,57\nPopulation;Projet;Usage;0.4\n"


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _names(p):
    return sorted(s.name for s in p.stakeholders)


def test_csv():
    f = svn_io.read_file("flux.csv", CSV.encode())
    assert f.format == "csv" and f.project is None
    assert len(f.table.rows) == 2 and f.table.delimiter == ";"
    p = f.to_project("Essai")
    assert _names(p) == ["Population", "Projet"] and len(p.flows) == 2
    assert p.name_of(p.focal) == "Projet"


def test_txt_tabulation_cp1252():
    data = "source\ttarget\tname\tscore\nÉcole\tMairie\tDemande\t0,3\n".encode("cp1252")
    f = svn_io.read_file("flux.txt", data)
    assert f.format == "txt" and f.table.delimiter == "\t"
    assert f.table.rows[0]["source"] == "École"


def test_json_projet_complet():
    d = ROOT / "data" / "examples" / "doughnut" / "T0_base.json"
    f = svn_io.read_file(d.name, d.read_bytes())
    assert f.project is not None and f.table is None
    assert f.to_project("ignoré") is f.project


def test_json_liste_de_flux():
    data = json.dumps([{"source": "Projet", "target": "Population", "name": "Service", "score": 0.57},
                       {"origine": "Population", "destination": "Projet", "nom": "Usage",
                        "score": "0,4", "categorie": "Social"},
                       {"source": "Projet", "target": "Projet", "name": "Boucle", "score": 0.5}])
    f = svn_io.read_file("flux.json", data.encode())
    assert f.format == "json" and len(f.table.rows) == 2 and len(f.table.errors) == 1
    assert f.table.rows[1]["category"] == "Social"


def test_json_flux_par_nom_dans_un_objet():
    data = {"name": "X", "flows": [{"source": "A", "target": "B", "name": "n", "score": 1}]}
    f = svn_io.read_file("x.json", json.dumps(data).encode())
    assert f.project is None and _names(f.to_project("X")) == ["A", "B"]


def test_json_flux_par_identifiant_avec_parties_prenantes_sans_projet_central():
    data = {"stakeholders": [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}],
            "flows": [{"source": "a", "target": "b", "name": "n", "score": 0.5}]}
    f = svn_io.read_file("x.json", json.dumps(data).encode())
    assert f.table.rows[0]["source"] == "Alpha" and f.table.rows[0]["target"] == "Beta"


def test_json_invalide():
    with pytest.raises(ValueError, match="JSON mal formé"):
        svn_io.read_file("x.json", b"{pas du json")
    with pytest.raises(ValueError):
        svn_io.read_file("x.json", b'{"autre": 1}')


def test_xlsx_aller_retour():
    """L'export Excel se réimporte à l'identique (mêmes cycles)."""
    p = examples.essai_de_jeu()
    f = svn_io.read_file("modele.xlsx", svn_io.flows_xlsx(p))
    assert f.format == "xlsx" and f.table.sheet == "Flux" and not f.table.errors
    q = f.to_project("copie", p.name_of(p.focal))
    assert _names(q) == _names(p) and len(q.flows) == len(p.flows)
    assert [c.score for c in find_cycles(q).cycles] == pytest.approx(
        [c.score for c in find_cycles(p).cycles])


def test_xlsx_premiere_feuille_de_flux_et_scores_numeriques():
    data = _xlsx({"Notes": [["Ceci n'est pas un tableau"]],
                  "Données": [[], ["Source", "Target", "Name", "Score"],
                              ["Projet", "Population", "Service", 0.57],
                              ["Population", "Projet", "Usage", 1],
                              ["Projet", "Mairie", "Trop", 1.5]]})
    f = svn_io.read_file("classeur.xlsx", data)
    assert f.table.sheet == "Données"
    assert [r["score"] for r in f.table.rows] == [0.57, 1.0]
    assert len(f.table.errors) == 1


def test_xlsx_sans_tableau_de_flux():
    with pytest.raises(ValueError, match="Aucune feuille"):
        svn_io.read_file("c.xlsx", _xlsx({"A": [["x", "y"], ["1", "2"]]}))
    with pytest.raises(ValueError, match="illisible"):
        svn_io.read_file("c.xlsx", b"PK pas un classeur")


def test_projet_central_par_nom():
    f = svn_io.read_file("flux.csv", CSV.encode())
    p = f.to_project("Essai", "population")
    assert p.name_of(p.focal) == "Population"
    p = f.to_project("Essai", "Inconnu")
    assert p.name_of(p.focal) == "Projet"
