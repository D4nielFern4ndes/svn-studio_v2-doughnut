import re
import unicodedata

import pandas as pd
import streamlit as st

import ui_state
from svn_core import examples
from svn_core import io as svn_io
from svn_core.model import Project

STEP = 0
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
p = ui_state.project()
ui_state.header(STEP)

tab_in, tab_out = st.tabs([":material/upload: Importer", ":material/download: Exporter"])

# --- Importer ---------------------------------------------------------------------
with tab_in:
    kind = st.segmented_control(
        "Que voulez-vous faire ?", ["Importer un fichier", "Nouveau projet"],
        default="Importer un fichier", key="import_kind")

    if kind == "Importer un fichier":
        with st.expander("Formats acceptés", icon=":material/help:", expanded=False):
            st.markdown(
                "**Tableau de flux** (`.csv`, `.txt`, `.tsv`, `.dat` ou `.xlsx`) : une ligne par flux, "
                "première ligne = noms des colonnes :\n\n"
                "| origine | destination | nom | score | categorie *(facultatif)* | description *(facultatif)* |\n"
                "|---|---|---|---|---|---|\n"
                "| Projet | Population | Qualité du service | 0,57 | Performance | |\n\n"
                "- Texte : séparateur `;`, tabulation, `,` ou `|`, **détecté automatiquement**.\n"
                "- Excel : la **première feuille** qui contient ces colonnes est lue.\n"
                "- Score entre 0 et 1, écrit `0,57` ou `0.57`.\n"
                "- En-têtes anglais acceptés : `source;target;name;score`.\n"
                "- Un fichier `input_edge.dat` de MatrixPath (sans en-tête, `nom;source;cible;score`) "
                "est aussi reconnu.\n"
                "- Les parties prenantes sont créées à partir des **noms** trouvés dans les flux.\n\n"
                "**JSON** (`.json`) : un projet sauvegardé par SVN Studio (parties prenantes, flux et "
                "projet central), ou une simple liste de flux "
                "`[{\"source\": \"Projet\", \"target\": \"Population\", \"name\": \"Qualité\", "
                "\"score\": 0.57}]`.")
            d1, d2 = st.columns(2)
            model = examples.essai_de_jeu()
            d1.download_button("Modèle rempli (CSV)", svn_io.flows_csv(model), "modele_flux.csv",
                               "text/csv", icon=":material/download:", use_container_width=True)
            d2.download_button("Modèle rempli (Excel)", svn_io.flows_xlsx(model), "modele_flux.xlsx",
                               XLSX_MIME, icon=":material/download:", use_container_width=True)
        up = st.file_uploader("Choisissez un fichier", type=svn_io.SUPPORTED_TYPES, key="up_table",
                              help="Fichiers .csv, .txt, .tsv, .dat, .json ou .xlsx, 4 Mo maximum.")
        loaded = None
        if up:
            try:
                loaded = svn_io.read_file(up.name, up.getvalue())
            except ValueError as e:
                st.error(f"Lecture impossible : {e}", icon=":material/error:")
        if loaded is not None and loaded.project is not None:
            new = loaded.project
            st.success(f"Projet sauvegardé **{new.name}** : {len(new.stakeholders)} parties prenantes, "
                       f"{len(new.flows)} flux.", icon=":material/check:")
            if st.button("Ouvrir ce projet", type="primary", icon=":material/folder_open:"):
                ui_state.replace_project(new, "Projet ouvert.")
        elif loaded is not None:
            table = loaded.table
            names = {r["source"].lower() for r in table.rows} | {r["target"].lower() for r in table.rows}
            sep = {";": "point-virgule", "\t": "tabulation", ",": "virgule", "|": "barre verticale"}
            c1, c2, c3 = st.columns(3)
            c1.metric("Flux lus", len(table.rows), border=True)
            c2.metric("Parties prenantes", len(names), border=True)
            c3.metric("Lignes ignorées", len(table.errors), border=True)
            if loaded.format == "xlsx":
                detail = f"Classeur Excel · feuille « {table.sheet} »"
            elif loaded.format == "json":
                detail = "Liste de flux JSON"
            else:
                detail = f"Séparateur détecté : {sep.get(table.delimiter, table.delimiter)}"
            st.caption(f"{detail} · {'avec' if table.has_header else 'sans'} ligne d'en-tête")
            if table.errors:
                with st.expander(f"{len(table.errors)} ligne(s) ignorée(s) — voir pourquoi",
                                 icon=":material/warning:"):
                    st.dataframe(pd.DataFrame(table.errors, columns=["Ligne", "Raison"]),
                                 hide_index=True, use_container_width=True)
            st.markdown("**Aperçu**")
            st.dataframe(pd.DataFrame(table.rows).rename(columns={
                "source": "Origine", "target": "Destination", "name": "Nom", "score": "Score",
                "category": "Catégorie", "description": "Description"}),
                hide_index=True, use_container_width=True, height=min(38 * (len(table.rows) + 1), 320),
                column_config={"Score": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="%.2f")})
            mode = st.radio("Que faire de ces flux ?",
                            ["Créer un nouveau projet avec ces flux", "Les ajouter au projet actuel"],
                            horizontal=True)
            if table.rows and st.button("Importer", type="primary", icon=":material/upload:"):
                if mode.startswith("Créer"):
                    target = loaded.to_project(up.name.rsplit(".", 1)[0])
                    ui_state.replace_project(target, f"{len(table.rows)} flux importés. "
                                             "Vérifiez le projet central (étape 2).")
                else:
                    svn_io.add_parsed_flows(p, table)
                    ui_state.touch()
                    ui_state.flash(f"{len(table.rows)} flux ajoutés au projet.")
                    st.rerun()

    elif kind == "Nouveau projet":
        with st.form("new"):
            name = st.text_input("Nom du projet", "Mon projet SVN")
            desc = st.text_area("Contexte (facultatif)", "")
            if st.form_submit_button("Créer le projet vide", type="primary"):
                ui_state.replace_project(Project(name=name.strip() or "Mon projet SVN",
                                                 description=desc), "Projet vide créé.")

# --- Exporter ----------------------------------------------------------------------
with tab_out:
    res, metrics = ui_state.results()
    base = unicodedata.normalize("NFD", p.name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")[:50] or "svn"
    with st.container(border=True):
        st.markdown("#### :material/save: Sauvegarde du projet")
        st.caption("Le seul fichier à garder pour reprendre votre travail plus tard (onglet Importer).")
        st.download_button("Télécharger le projet (JSON)", svn_io.dump_json(p), f"{base}.json",
                           "application/json", type="primary", icon=":material/download:")
    c1, c2 = st.columns(2)
    with c1, st.container(border=True, height="stretch"):
        st.markdown("#### :material/table: Tableaux (Excel)")
        st.caption("Classeur Excel réimportable, ou fichiers CSV séparés par des points-virgules.")
        st.download_button("Flux et parties prenantes (Excel)", svn_io.flows_xlsx(p), f"{base}.xlsx",
                           XLSX_MIME, use_container_width=True, icon=":material/grid_on:")
        st.download_button("Flux", svn_io.flows_csv(p), f"{base}_flux.csv", "text/csv",
                           use_container_width=True)
        st.download_button("Parties prenantes", svn_io.stakeholders_csv(p),
                           f"{base}_parties_prenantes.csv", "text/csv", use_container_width=True)
        st.download_button("Cycles", svn_io.cycles_csv(p, res), f"{base}_cycles.csv", "text/csv",
                           use_container_width=True)
        st.download_button("Indicateurs", svn_io.indicators_csv(metrics), f"{base}_indicateurs.csv",
                           "text/csv", use_container_width=True)
    with c2, st.container(border=True, height="stretch"):
        st.markdown("#### :material/compare_arrows: Autres outils")
        st.caption("Fichiers d'entrée de l'outil MatrixPath, pour comparer les résultats.")
        st.download_button("input_vertex.dat", svn_io.mit_vertex_dat(p), "input_vertex.dat",
                           use_container_width=True)
        st.download_button("input_edge.dat", svn_io.mit_edge_dat(p), "input_edge.dat",
                           use_container_width=True)

ui_state.footer_nav(STEP)
