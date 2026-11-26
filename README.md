# SVN Studio

Outil open source d'analyse des **Stakeholder Value Networks (SVN)** : parties prenantes, flux de
valeur, cycles de valeur et indicateurs de priorisation. Utilisable pour tout projet, quel que soit
le domaine, sans programmation.

- Construire un réseau de parties prenantes reliées par des flux de valeur notés de 0 à 1.
- Trouver tous les cycles qui partent du projet central et y reviennent ; score d'un cycle =
  produit des scores de ses flux.
- Classer parties prenantes et flux : WSO, WOO, WIO, WVFO (fondés sur les cycles) et influence
  moyenne par les flux émis, reçus, ou les deux.
- Comparer deux scénarios d'un même réseau (par exemple sans et avec le Doughnut comme partie
  prenante).
- Importer en CSV, TXT, JSON ou XLSX (Excel) ; exporter en JSON, XLSX, CSV et au format `.dat` de
  MatrixPath.

## Contexte

Projet d'études (PE) réalisé à l'Université de Technologie de Troyes (UTT) en 2026 par
Daniel Oliveira Fernandes et Beatriz de Sousa Gomes. L'outil accompagne l'étude du croisement
entre Stakeholder Value Network et Doughnut de Kate Raworth.

## Documentation

- [Guide méthodologique (PDF)](docs/guide_methodologique.pdf) : mener une analyse pas à pas et
  refaire l'exemple pédagogique. Également disponible dans le menu de l'application.
- [Explication du code](docs/explication_du_code.md) : organisation du code, pour le lire, le
  modifier et l'étendre.
- [Construction du guide PDF](docs/build/README.md) : régénérer le PDF et ses copies d'écran.

## Installation et lancement sur son ordinateur

Prérequis : Python 3.10 ou plus récent ([python.org](https://www.python.org/downloads/) ; sous
Windows, cocher « Add Python to PATH » pendant l'installation).

1. Télécharger le dépôt (bouton **Code › Download ZIP** sur GitHub), puis le décompresser.
2. Ouvrir un terminal dans le dossier décompressé (sous Windows : clic droit dans le dossier ›
   *Ouvrir dans le Terminal*).
3. Installer les dépendances (une seule fois, connexion Internet nécessaire) :

   ```
   python -m pip install -r requirements.txt
   ```

4. Lancer l'application :

   ```
   python -m streamlit run app.py
   ```

L'application s'ouvre dans le navigateur à l'adresse `http://localhost:8501`. Elle fonctionne
ensuite **sans connexion Internet** : les données restent sur l'ordinateur. Pour l'arrêter,
fermer le terminal ou taper `Ctrl+C`.

La forme `python -m ...` évite le message « commande introuvable » qui apparaît souvent sous
Windows avec `pip` ou `streamlit` seuls. Si `python` n'est pas reconnu sous Windows, remplacer
`python` par `py`.

## Organisation du dépôt

```
app.py, ui_state.py, views/   interface Streamlit (une page par fichier)
svn_core/                     moteur de calcul, indépendant de l'interface
data/examples/                exemple pédagogique et scénarios Doughnut (T0, T1, T2)
tests/                        tests automatiques (pytest)
docs/                         guide méthodologique, explication du code, construction du PDF
```

## Tests

```
python -m pip install pytest
python -m pytest
```

Les tests vérifient que les résultats sont identiques à ceux de l'outil MatrixPath sur l'exemple
pédagogique, retrouvent les chemins critiques d'un réseau de référence publié et rejouent les
premiers tests d'intégration du Doughnut.

## Licence

MIT, voir [LICENSE](LICENSE).
