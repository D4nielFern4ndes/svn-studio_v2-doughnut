"""Jeu de données de référence externe, utilisé seulement pour la validation automatique.

Réseau partiel (6 parties prenantes, 15 flux) reconstruit à partir des 10 chemins
critiques publiés dans un article de la littérature SVN. Il n'apparaît pas dans
l'application ; il sert à vérifier que le calcul des cycles retrouve un résultat publié.
"""

from svn_core.examples import _build
from svn_core.model import Project

def reference_network() -> Project:
    """Réseau partiel reconstruit à partir des 10 chemins critiques publiés.

    La publication ne donne pas tous ses flux : on reconstruit seulement les 15 flux
    qui composent les 10 chemins critiques, avec les scores publiés.
    """
    return _build(
        "Réseau de référence — réseau partiel",
        "Reconstruction des 10 chemins critiques publiés (6 parties prenantes, 15 flux).",
        [("Amélioration du transport", "Projet central", "Amélioration du transport public (projet focal)."),
         ("Population", "Bénéficiaire", "Usagers et habitants."),
         ("Gouvernement local", "Institution publique", "Gouvernement local."),
         ("Opérateurs de bus", "Partenaire", "Opérateurs de bus."),
         ("Pouvoir judiciaire", "Régulateur", "Pouvoir judiciaire."),
         ("Presse", "Autre", "Presse.")],
        [("Meilleure qualité", "Amélioration du transport", "Population", 0.56, "Performance"),
         ("Impôts", "Population", "Gouvernement local", 0.56, "Économique"),
         ("Soutien politique", "Population", "Gouvernement local", 0.44, "Social"),
         ("Hausse des recettes tarifaires", "Population", "Opérateurs de bus", 0.76, "Économique"),
         ("Prise de décision", "Gouvernement local", "Amélioration du transport", 0.96, "Gestion"),
         ("Financement des infrastructures", "Gouvernement local", "Amélioration du transport", 0.56, "Économique"),
         ("Appels d'offres", "Gouvernement local", "Pouvoir judiciaire", 0.96, "Gestion"),
         ("Contrôle du respect des contrats", "Pouvoir judiciaire", "Amélioration du transport", 0.56, "Gestion"),
         ("Attraction de voyageurs", "Amélioration du transport", "Opérateurs de bus", 0.44, "Social"),
         ("Fonds pour la flotte et la technologie", "Opérateurs de bus", "Amélioration du transport", 0.56, "Technologique"),
         ("Soutien politique (opérateurs)", "Opérateurs de bus", "Amélioration du transport", 0.32, "Social"),
         ("Capital politique renforcé", "Amélioration du transport", "Gouvernement local", 0.19, "Social"),
         ("Information sur le projet", "Amélioration du transport", "Presse", 0.56, "Autre"),
         ("Opinion publique", "Presse", "Gouvernement local", 0.32, "Social"),
         ("Information sur les changements", "Presse", "Population", 0.56, "Autre")],
        "Amélioration du transport",
    )


# Les 10 chemins critiques publiés :
# suite des noms de flux -> (nom du chemin, score publié).
REFERENCE_PATHS = {
    ("Meilleure qualité", "Impôts", "Prise de décision"): ("CP1", 0.3011),
    ("Attraction de voyageurs", "Fonds pour la flotte et la technologie"): ("CP2", 0.2464),
    ("Meilleure qualité", "Hausse des recettes tarifaires", "Fonds pour la flotte et la technologie"): ("CP3", 0.2383),
    ("Meilleure qualité", "Soutien politique", "Prise de décision"): ("CP4", 0.2365),
    ("Meilleure qualité", "Impôts", "Financement des infrastructures"): ("CP5", 0.1824),
    ("Capital politique renforcé", "Prise de décision"): ("CP6", 0.1756),
    ("Information sur le projet", "Opinion publique", "Prise de décision"): ("CP7", 0.1720),
    ("Information sur le projet", "Information sur les changements", "Impôts", "Prise de décision"): ("CP8", 0.1686),
    ("Meilleure qualité", "Impôts", "Appels d'offres", "Contrôle du respect des contrats"): ("CP9", 0.1686),
    ("Attraction de voyageurs", "Soutien politique (opérateurs)"): ("CP10", 0.1408),
}

