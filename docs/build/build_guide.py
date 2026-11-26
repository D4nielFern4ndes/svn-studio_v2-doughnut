"""Construit docs/guide_methodologique.pdf à partir de docs/guide_methodologique.md.

Usage (depuis la racine du dépôt) :
    python -m pip install markdown weasyprint
    python docs/build/build_guide.py

Le texte vient uniquement du fichier Markdown : modifiez le .md puis relancez ce
script. La mise en page (couverture, sommaire paginé, couleurs UTT) est dans
guide.css. Les copies d'écran viennent de docs/build/img/ (à régénérer avec
capture_screenshots.py quand l'interface change) et sont placées après les
titres d'étape listés dans FIGURES ; une image absente est simplement ignorée.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
SRC = DOCS / "guide_methodologique.md"
OUT = DOCS / "guide_methodologique.pdf"
VERSION = "2.0"

# Début du titre de niveau 3  ->  (image dans img/, légende)
FIGURES = {
    "Étape 1": ("accueil.png", "Page « Accueil » : trois façons de démarrer, puis la démarche en 6 étapes."),
    "Étape 2": ("parties_prenantes.png", "Étape 2 « Parties prenantes » : projet central, ajout rapide et tableau éditable."),
    "Étape 3": ("flux.png", "Étape 3 « Flux de valeur » : formulaire d'ajout, aide au score et liste des flux."),
    "Étape 4": ("reseau.png", "Étape 4 « Carte du réseau » : un cycle mis en évidence (exemple pédagogique)."),
    "Étape 5": ("cycles.png", "Étape 5 « Cycles de valeur » : une ligne sélectionnée affiche le détail du calcul."),
    "Étape 6": ("priorisation.png", "Étape 6 « Priorisation » : indicateur WSO sur l'exemple pédagogique."),
    "Étape 7": ("exporter.png", "Étape 1 « Importer / exporter », onglet Exporter."),
    "Outil": ("comparaison.png", "Outil « Comparer deux scénarios » : le projet actuel (A) face à un projet importé (B)."),
}

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


def split_source(text: str) -> tuple[str, str, str]:
    """Sépare le titre, l'introduction (avant le sommaire) et le corps (à partir du 1er ##)."""
    head, sep, body = text.partition("\n## ")
    body = "## " + body if sep else ""
    title_match = re.search(r"^#\s+(.+)$", head, re.M)
    title = title_match.group(1).strip() if title_match else "Guide méthodologique"
    intro = re.sub(r"^#\s+.+$", "", head, count=1, flags=re.M)
    intro = re.split(r"\*\*Sommaire\*\*", intro)[0].strip()
    return title, intro, body


def add_figures(body_html: str) -> str:
    def repl(m: re.Match) -> str:
        heading = html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
        for prefix, (img, caption) in FIGURES.items():
            if heading.startswith(prefix):
                path = HERE / "img" / img
                if not path.exists():
                    print(f"  (image absente, ignorée : {img})", file=sys.stderr)
                    break
                label, _, rest = caption.partition(" : ")
                cap = f"<b>{label}</b> : {rest}" if rest else caption
                return (f"{m.group(0)}<figure><img src=\"{path.as_uri()}\">"
                        f"<figcaption>{cap}</figcaption></figure>")
        return m.group(0)
    return re.sub(r"<h3 id=\"([^\"]+)\">(.*?)</h3>", repl, body_html)


def bold_leads_to_h4(body_html: str) -> str:
    """Un paragraphe fait seulement de gras (« **Cycles attendus.** ») devient un intertitre."""
    return re.sub(r"<p><strong>([^<]{1,60})</strong></p>", r"<h4>\1</h4>", body_html)


def join_lines(body_html: str) -> str:
    """Remplace les retours à la ligne du .md dans les paragraphes et listes par des espaces
    (sinon WeasyPrint peut mal justifier une ligne qui finit dans du gras)."""
    body_html = re.sub(r"<(p|li|td)>(.*?)</\1>", lambda m: m.group(0).replace("\n", " "),
                       body_html, flags=re.S)
    # Intertitre en gras en début de paragraphe (« **Gros réseaux.** ... ») : insécable,
    # pour éviter une première ligne étirée par la justification.
    return re.sub(r"<p><strong>([^<]{1,45})</strong>",
                  lambda m: "<p><strong>" + m.group(1).replace(" ", "\u00a0") + "</strong>", body_html)


def number_h2(body_html: str) -> str:
    return re.sub(r"(<h2 id=\"[^\"]+\">)(\d+\.)\s*", r'\1<span class="num">\2</span> ', body_html)


def toc(tokens: list[dict]) -> str:
    items = []
    for t in tokens:
        items.append(f'<li class="l2"><a href="#{t["id"]}">{t["name"]}</a></li>')
        for c in t["children"]:
            items.append(f'<li class="l3"><a href="#{c["id"]}">{c["name"]}</a></li>')
    return f'<section class="toc"><h2>Sommaire</h2><ul>{"".join(items)}</ul></section>'


def cover(title: str, intro_html: str) -> str:
    name = title.split("—")[-1].strip() if "—" in title else "SVN Studio"
    today = dt.date.today()
    return f"""
<section class="cover">
  <div class="band"></div>
  <div class="inner">
    <div class="top">Stakeholder Value Network · outil open source</div>
    <div class="middle">
      <div class="kicker">Guide méthodologique</div>
      <h1>{html.escape(name)}</h1>
      <div class="rule"></div>
      <div class="subtitle">Construire un Stakeholder Value Network, calculer les cycles de valeur
        et prioriser les parties prenantes et les flux</div>
      <div class="lead">{intro_html}</div>
    </div>
    <table class="meta">
      <tr><td>Version</td><td>{VERSION} — {MOIS[today.month - 1]} {today.year}</td></tr>
      <tr><td>Outil</td><td>application web open source (licence MIT)</td></tr>
    </table>
  </div>
</section>"""


def main() -> None:
    title, intro, body = split_source(SRC.read_text(encoding="utf-8"))
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": "2-3"}})
    body_html = md.convert(body)
    body_html = number_h2(add_figures(bold_leads_to_h4(join_lines(body_html))))
    intro_html = markdown.markdown(intro)
    doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>{html.escape(title)}</title></head><body>
{cover(title, intro_html)}{toc(md.toc_tokens)}{body_html}</body></html>"""
    HTML(string=doc, base_url=str(DOCS)).write_pdf(
        OUT, stylesheets=[str(HERE / "guide.css")])
    print(f"PDF écrit : {OUT.relative_to(DOCS.parent)}")


if __name__ == "__main__":
    main()
