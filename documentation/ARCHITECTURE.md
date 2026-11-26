# Architecture

Lu avec le [README](../README.md) et la note de la phase 2, `documentation/02_data_architecture.ipynb`.

## Le flux

```text
Profil, politique d'investissement, méthode d'éligibilité
        |
Registre des sources (audit/source_registry.xlsx)
        |
Acquisition : iShares, Yahoo Finance, Banque nationale suisse, rapports publics
        |
data/01_raw  et  base SQLite locale (non versionnée)
        |
Contrôle qualité, puis prix en CHF et univers
        |
Trois livres (phase 5), sur la fenêtre où le SARON et le rendement du fonds existent tous les deux
        |
Suivi, performance, risque, chocs
        |
Pages HTML, annexe Excel, modèle Power BI, rapport PDF, présentation
```

Une commande enchaîne cet ordre : `python -m src.pipeline.refresh`. `python -m src.pipeline.full_refresh` y ajoute l'ouverture de Power BI Desktop, l'actualisation du modèle et l'export des mesures avant l'annexe. Un jeu qui échoue à l'acquisition n'arrête pas les autres. La commande s'arrête si un contrôle de réconciliation reste ouvert, ou si un nombre d'un texte n'est pas dans un fichier.

## Les dossiers

| Dossier | Rôle |
|---|---|
| `src/governance` | Registre des sources, et ce qu'il refuse |
| `src/acquisition` | Connecteurs iShares, Yahoo Finance, BNS |
| `src/database` | Schéma SQLite et chargement des jeux autorisés |
| `src/preparation` | Référentiel titres, éligibilité, traitement qualité |
| `src/portfolio_construction` | Les trois livres |
| `src/portfolio_monitoring` | Poids, expositions, concentration, rotation |
| `src/performance` | Rendement, écart au fonds, drawdown |
| `src/risk` | VaR historique, expected shortfall, corrélation |
| `src/stress_testing` | Quatre chocs illustratifs, paramètres écrits dans `src/config.py` |
| `src/quality` | Centre de contrôle |
| `src/reporting` | Annexe Excel, rapport, présentation, dictionnaire, export Power BI |
| `src/pipeline` | L'ordre ci-dessus, et le passage complet avec Power BI |
| `src/utils` | Journal et remplacement de fichiers |
| `scripts` | Reconstruction mensuelle des données par le planificateur Windows |
| `dashboards/powerbi` | Rapport Power BI. Les données ne sont pas dans le fichier : chaque ouverture demande Actualiser |
| `documentation` | Le récit de chaque phase |
| `sql` | Requêtes de contrôle sur la base locale |
| `tests` | Contrôles automatisés, dont l'injection d'erreurs sur une copie |

## Trois restitutions, une définition

Les pages HTML, l'annexe Excel et Power BI lisent les mêmes fichiers publiés. Excel recalcule les indicateurs à partir des rendements mensuels. Il ne lit pas le chiffre déjà calculé par Python. Power BI lit la cellule publiée pour le Sharpe, la VaR et les chocs. Quelques mesures de la page Performance recalculent en DAX le multiple contre le SARON, le multiple contre le fonds et le rendement glissant, à partir des mêmes rendements. L'annexe compare les deux résultats. La tolérance est celle du pipeline, écrite avant la comparaison. On ne la change pas pour faire passer un contrôle.

## Identité et périmètre

L'identité d'un titre est le ticker et la place de cotation. Les livres sont long only, entièrement investis, rééquilibrés chaque trimestre. L'équipondéré n'est pas soumis à la bande de nombre de titres. Les deux livres optimisés le sont. La cible d'écart de suivi est écrite dans la politique. Elle n'entre pas dans le choix des poids. Le volume, dix pour cent du volume moyen sur vingt séances, est écrit et n'est pas appliqué.

Le fonds iShares est la référence de rendement. Ce n'est pas un quatrième livre de poids. Il entre dans les graphiques qui ont une série de rendement. Il n'entre pas dans l'allocation, la rotation ni les chocs.

## Ce qui reste hors du calcul

Pas de fichier de conservation. Pas de frais. Les livres sont mesurés en rendement total brut : dividendes réinvestis, avant frais et avant impôt à la source. Les quatre chocs sont illustratifs : ce ne sont pas des scénarios datés. Les rapports de société qui fondent l'éligibilité restent sur le disque de travail et ne sont pas versionnés.
