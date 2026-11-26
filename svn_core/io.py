"""Import et export : JSON (projet complet ou liste de flux), CSV/TXT et XLSX (flux), .dat MatrixPath."""

from __future__ import annotations

import csv
import io
import json
import unicodedata
from dataclasses import dataclass

from .cycles import CycleResult
from .metrics import Row
from .model import CATEGORIES, Flow, Project, is_valid_score, new_id

# Noms de colonnes acceptés dans un CSV de flux (français ou anglais).
HEADER_ALIASES = {"origine": "source", "destination": "target", "nom": "name",
                  "categorie": "category", "note": "score"}
REQUIRED = ["source", "target", "name", "score"]


# --- JSON -----------------------------------------------------------------
def load_json(text: str) -> Project:
    return Project.from_dict(json.loads(text))


def dump_json(project: Project) -> str:
    return json.dumps(project.to_dict(), ensure_ascii=False, indent=2)


# --- CSV ------------------------------------------------------------------
def _norm(h: str) -> str:
    h = unicodedata.normalize("NFD", h.strip().lower())
    h = "".join(c for c in h if unicodedata.category(c) != "Mn")
    return HEADER_ALIASES.get(h, h)


def _parse_score(raw: str) -> float | None:
    try:
        v = float(str(raw).strip().replace(",", "."))
    except ValueError:
        return None
    return v if is_valid_score(v) else None


def decode_bytes(data: bytes) -> str:
    """Décode un fichier texte : UTF-8 (avec ou sans BOM), sinon Windows-1252 (Excel français)."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encodage du fichier non reconnu.")


def detect_delimiter(first_line: str) -> str:
    """Séparateur le plus fréquent dans la première ligne parmi ; tabulation , |"""
    counts = {d: first_line.count(d) for d in (";", "\t", ",", "|")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ";"


@dataclass
class ParsedTable:
    """Résultat de la lecture d'un fichier de flux, avant import (pour l'aperçu)."""
    rows: list[dict]              # lignes valides : source, target, name, score, category, description
    errors: list[tuple[int, str]]  # (numéro de ligne dans le fichier, raison)
    delimiter: str                 # "" pour Excel et JSON
    has_header: bool
    sheet: str | None = None       # feuille Excel utilisée


def _records_from_rows(raw: list[list[str]]) -> tuple[list[dict], int, bool]:
    """Transforme les lignes brutes d'un tableau en enregistrements (dictionnaires).

    Retourne (enregistrements, numéro de la première ligne de données, en-tête présent).
    """
    headers = [_norm(h) for h in raw[0]]
    if all(h in headers for h in REQUIRED):
        records = [{h: (r[i].strip() if i < len(r) else "") for i, h in enumerate(headers)}
                   for r in raw[1:]]
        return records, 2, True
    if len(raw[0]) >= 4 and _parse_score(raw[0][3]) is not None:
        records = [{"name": r[0].strip(), "source": r[1].strip(), "target": r[2].strip(),
                    "score": r[3].strip()} if len(r) >= 4 else {} for r in raw]
        return records, 1, False
    raise ValueError("Colonnes non reconnues. Le tableau doit avoir l'en-tête "
                     "origine;destination;nom;score (ou source;target;name;score), "
                     "ou 4 colonnes sans en-tête nom;source;cible;score.")


def _validate_records(records: list[dict], start: int) -> tuple[list[dict], list[tuple[int, str]]]:
    rows, errors = [], []
    for n, o in enumerate(records, start=start):
        o = {k: ("" if v is None else str(v).strip()) for k, v in o.items()}
        if not o.get("source") or not o.get("target") or not o.get("name"):
            errors.append((n, "origine, destination ou nom manquant"))
            continue
        if o["source"].lower() == o["target"].lower():
            errors.append((n, "origine et destination identiques"))
            continue
        score = _parse_score(o.get("score", ""))
        if score is None:
            errors.append((n, f"score invalide « {o.get('score', '')} » (attendu entre 0 et 1)"))
            continue
        cat = o.get("category", "")
        rows.append({"source": o["source"], "target": o["target"], "name": o["name"], "score": score,
                     "category": cat if cat in CATEGORIES else "Autre",
                     "description": o.get("description", "")})
    if not rows and not errors:
        raise ValueError("Le fichier ne contient aucune ligne de données.")
    return rows, errors


def parse_flows_table(text: str) -> ParsedTable:
    """Lit un tableau de flux texte (CSV, TXT, TSV ou .dat MatrixPath).

    - Avec en-tête : colonnes origine;destination;nom;score (ou source;target;name;score),
      facultatives categorie;description.
    - Sans en-tête : 4 colonnes nom;source;cible;score (format input_edge.dat de MatrixPath).
    Le séparateur (; tabulation , |) est détecté automatiquement.
    """
    text = text.lstrip("\ufeff")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Le fichier est vide.")
    delim = detect_delimiter(lines[0])
    raw = [r for r in csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)]
    records, start, has_header = _records_from_rows(raw)
    rows, errors = _validate_records(records, start)
    return ParsedTable(rows, errors, delim, has_header)


# --- Excel (.xlsx) ----------------------------------------------------------
def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def parse_flows_xlsx(data: bytes) -> ParsedTable:
    """Lit un classeur Excel : la première feuille qui contient un tableau de flux est utilisée.

    Mêmes colonnes que pour un CSV. Les lignes entièrement vides sont ignorées.
    """
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:  # fichier corrompu, autre format, etc.
        raise ValueError("Classeur Excel illisible (format .xlsx attendu).") from e
    try:
        first_error = None
        for ws in wb.worksheets:
            raw = [[_cell(v) for v in row] for row in ws.iter_rows(values_only=True)]
            raw = [r for r in raw if any(c.strip() for c in r)]
            if not raw:
                continue
            try:
                records, start, has_header = _records_from_rows(raw)
            except ValueError as e:
                first_error = first_error or e
                continue
            rows, errors = _validate_records(records, start)
            return ParsedTable(rows, errors, "", has_header, sheet=ws.title)
    finally:
        wb.close()
    if first_error:
        raise ValueError(f"Aucune feuille du classeur ne contient un tableau de flux. {first_error}")
    raise ValueError("Le classeur est vide.")


# --- JSON sous forme de liste de flux -----------------------------------------
def parse_flows_records(items: list, stakeholders: list | None = None) -> ParsedTable:
    """Lit une liste JSON de flux ``[{"source": ..., "target": ..., "name": ..., "score": ...}]``.

    Les extrémités peuvent être des noms, ou des identifiants présents dans ``stakeholders``.
    """
    names = {str(s.get("id")): str(s.get("name")) for s in (stakeholders or [])
             if isinstance(s, dict) and s.get("id") and s.get("name")}
    records = []
    for it in items:
        if not isinstance(it, dict):
            records.append({})
            continue
        o = {_norm(str(k)): v for k, v in it.items()}
        for end in ("source", "target"):
            if o.get(end) is not None:
                o[end] = names.get(str(o[end]), o[end])
        records.append(o)
    rows, errors = _validate_records(records, 1)
    return ParsedTable(rows, errors, "", True)


# --- Lecture d'un fichier quelconque ------------------------------------------
SUPPORTED_TYPES = ["csv", "txt", "tsv", "dat", "json", "xlsx"]


@dataclass
class LoadedFile:
    """Contenu d'un fichier importé : soit un projet complet (JSON), soit un tableau de flux."""
    format: str                   # csv, txt, json, xlsx...
    project: Project | None = None
    table: ParsedTable | None = None

    def to_project(self, name: str, focal_name: str | None = None) -> Project:
        """Projet prêt à l'emploi. Pour un tableau, le projet central est ``focal_name`` s'il
        existe dans les flux, sinon la première partie prenante rencontrée."""
        if self.project is not None:
            return self.project
        p = Project(name=name)
        add_parsed_flows(p, self.table)
        focal = p.find_by_name(focal_name) if focal_name else None
        if focal:
            p.focal = focal.id
        return p


def read_file(filename: str, data: bytes) -> LoadedFile:
    """Lit un fichier CSV, TXT, TSV, DAT, JSON ou XLSX déposé par l'utilisateur.

    - JSON : projet sauvegardé par SVN Studio, ou liste de flux (``[...]`` ou ``{"flows": [...]}``).
    - XLSX : première feuille contenant un tableau de flux.
    - Autres : tableau de flux texte, séparateur détecté automatiquement.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "xlsx" or data[:2] == b"PK":
        return LoadedFile("xlsx", table=parse_flows_xlsx(data))
    text = decode_bytes(data)
    stripped = text.lstrip("\ufeff").lstrip()
    if ext == "json" or stripped[:1] in ("{", "["):
        try:
            d = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON mal formé (ligne {e.lineno}).") from e
        if isinstance(d, list):
            return LoadedFile("json", table=parse_flows_records(d))
        if isinstance(d, dict) and isinstance(d.get("flows"), list):
            try:
                return LoadedFile("json", project=Project.from_dict(d))
            except ValueError:
                # Flux désignant les parties prenantes par leur nom, ou projet incomplet.
                sh = d.get("stakeholders") if isinstance(d.get("stakeholders"), list) else None
                table = parse_flows_records(d["flows"], sh)
                if not table.rows:
                    raise
                return LoadedFile("json", table=table)
        raise ValueError("Ce fichier JSON ne correspond ni à un projet SVN Studio, "
                         "ni à une liste de flux.")
    return LoadedFile(ext or "txt", table=parse_flows_table(text))


def read_csv_rows(text: str) -> list[dict]:
    """Compatibilité : lignes valides d'un tableau de flux."""
    return parse_flows_table(text).rows


def add_parsed_flows(project: Project, table: ParsedTable) -> int:
    for o in table.rows:
        src = project.find_or_add(o["source"], "Importé depuis un fichier")
        dst = project.find_or_add(o["target"], "Importé depuis un fichier")
        project.flows.append(Flow(id=new_id("f"), source=src.id, target=dst.id, name=o["name"],
                                  score=o["score"], category=o["category"],
                                  description=o["description"]))
    if not project.focal and project.stakeholders:
        project.focal = project.stakeholders[0].id
    return len(table.rows)


def import_flows_csv(project: Project, text: str) -> tuple[int, int]:
    """Ajoute au projet les flux d'un fichier CSV/TXT. Les parties prenantes absentes sont créées.

    Retourne (nombre de flux importés, nombre de lignes ignorées).
    """
    table = parse_flows_table(text)
    return add_parsed_flows(project, table), len(table.errors)


def _csv(rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerows(rows)
    return "﻿" + buf.getvalue()  # BOM : Excel ouvre correctement les accents


def flows_csv(p: Project) -> str:
    return _csv(_flow_rows(p))


def _flow_rows(p: Project) -> list[list]:
    return [["origine", "destination", "nom", "score", "categorie", "description"]] + \
        [[p.name_of(f.source), p.name_of(f.target), f.name, f.score, f.category, f.description]
         for f in p.flows]


def flows_xlsx(p: Project) -> bytes:
    """Classeur Excel : feuille « Flux » (réimportable) et feuille « Parties prenantes »."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Flux"
    for r in _flow_rows(p):
        ws.append(r)
    ws2 = wb.create_sheet("Parties prenantes")
    ws2.append(["nom", "profil", "description", "central"])
    for s in p.stakeholders:
        ws2.append([s.name, s.type, s.description, "OUI" if s.id == p.focal else "NON"])
    for sheet, widths in ((ws, [28, 28, 34, 8, 16, 40]), (ws2, [28, 22, 40, 8])):
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for i, w in enumerate(widths):
            sheet.column_dimensions[chr(65 + i)].width = w
        sheet.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def stakeholders_csv(p: Project) -> str:
    return _csv([["identifiant", "nom", "profil", "description", "central"]] +
                [[s.id, s.name, s.type, s.description, "OUI" if s.id == p.focal else "NON"]
                 for s in p.stakeholders])


def cycles_csv(p: Project, res: CycleResult) -> str:
    return _csv([["rang", "cycle", "score", "longueur", "flux"]] +
                [[i + 1, " → ".join(p.name_of(n) for n in c.nodes), c.score, c.length,
                  " | ".join(f.name for f in c.flows)] for i, c in enumerate(res.cycles)])


def indicators_csv(all_rows: dict[str, list[Row]]) -> str:
    out = [["indicateur", "rang", "element", "valeur", "nb_flux", "somme_scores"]]
    for key, rows in all_rows.items():
        out += [[key, i + 1, r.name, r.value, "" if r.count is None else r.count,
                 "" if r.total is None else r.total] for i, r in enumerate(rows)]
    return _csv(out)


# --- MatrixPath (format .dat) --------------------------------------------
def mit_vertex_dat(p: Project) -> str:
    return "\n".join(s.name for s in p.stakeholders) + "\n"


def mit_edge_dat(p: Project) -> str:
    return "\n".join(f"{f.name};{p.name_of(f.source)};{p.name_of(f.target)};{f.score}"
                     for f in p.flows) + "\n"


def import_mit_edge_dat(text: str, focal_name: str | None = None, name: str = "Import MatrixPath") -> Project:
    """Construit un projet à partir d'un fichier input_edge.dat (nom;source;cible;score)."""
    p = Project(name=name)
    for line in text.lstrip("﻿").splitlines():
        parts = [x.strip() for x in line.split(";")]
        if len(parts) < 4 or not parts[0]:
            continue
        score = _parse_score(parts[3])
        if score is None or parts[1].lower() == parts[2].lower():
            continue
        src, dst = p.find_or_add(parts[1]), p.find_or_add(parts[2])
        p.flows.append(Flow(new_id("f"), src.id, dst.id, parts[0], score))
    focal = p.find_by_name(focal_name) if focal_name else None
    p.focal = focal.id if focal else (p.stakeholders[0].id if p.stakeholders else None)
    return p
