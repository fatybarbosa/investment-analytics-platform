# Guide d'utilisation

Lu avec le [README](../README.md). Les textes produits par le pipeline portent la mention « généré automatiquement, à relire avant diffusion ».

## Préparer la machine

- Windows, Python 3.12.
- Dépendances : `pip install -r requirements/requirements.txt`.
- Excel, pour le recalcul de l'annexe par COM.
- Power BI Desktop, pour lire les mesures. Le script n'enregistre pas le rapport.

Fermer `reports/excel/annexe_reporting.xlsx` avant de lancer le pipeline. Un classeur ouvert verrouille le fichier et la commande s'arrête.

## Reconstruire

```bash
python -m src.pipeline.refresh
```

L'ordre est celui de `src/pipeline/refresh.py` : acquisition due, base SQLite, livres, suivi, performance, risque, chocs, qualité, annexe Excel, rapport et présentation, puis le dictionnaire de données. `--force` relance aussi la préparation des documents d'éligibilité, lorsque ces documents sont à relire.

Contrôles automatisés :

```bash
python -m pytest tests
```

Le test d'injection travaille sur une copie. Il ne modifie pas les fichiers de production.

## Lire les restitutions

| Restitution | Ouverture |
|---|---|
| Pages HTML | `reports/monitoring`, `reports/performance`, `reports/risk`, `reports/stress` |
| Annexe Excel | `reports/excel/annexe_reporting.xlsx`, après Actualiser tout |
| Explications de l'annexe | `reports/excel/EXPLICATIONS.md` |
| Power BI | `dashboards/powerbi/Investment Analytics.pbip`, puis Actualiser |
| Rapport | `reports/executive/rapport_executif.pdf` |
| Rapports clients, français et anglais | `reports/clients/` |
| Présentation | `reports/management/presentation_management.pptx` |
| Commentaires | `reports/executive/commentaires_automatises.md` |
| Rapports clients | `reports/clients/rapport_mensuel_caisse_de_pension.pdf`, `reports/clients/rapport_mensuel_gerant.pdf` |
| Cas d'investigation | `reports/executive/cas_d_investigation.md` |

Les pages Power BI sont : Portfolio Overview, Suivi, Performance Analytics, Risk Analytics, Stress Testing, Data Quality. Le filtre des pages d'allocation, de suivi et de chocs ne propose pas le fonds. Les pages de performance et de risque le proposent, parce qu'elles lisent une série de rendement.

La colonne Power BI de l'annexe reste en attente tant qu'une valeur n'a pas été lue dans Desktop :

```bash
python -m src.reporting.power_bi_export
```

Power BI Desktop doit être ouvert et le modèle actualisé. La commande ne calcule pas les mesures elle-même. Elle interroge le moteur. Si Desktop est fermé, elle s'arrête et n'écrit rien.

## SQL

La base `database/sdg_investment.db` n'est pas dans le dépôt. Le rafraîchissement la reconstruit. Les requêtes de `sql/` s'exécutent alors. `python -m src.reporting.data_dictionary` les exécute et réécrit le dictionnaire. Une requête qui échoue arrête la commande.

Pour les lire dans un client SQLite, ouvrir la base locale et exécuter le fichier. Les requêtes interrogent le contrôle qualité, le registre, le SARON publié, la feuille de positions du fonds, et les trois livres une fois leurs fichiers chargés dans la base. Elles ne recalculent pas le Sharpe ni la VaR.

## Dictionnaire

```bash
python -m src.reporting.data_dictionary
```

Le fichier écrit est `documentation/DICTIONNAIRE_DONNEES.md`. Les nombres de lignes viennent du comptage du fichier, pas d'une saisie.

## Captures Power BI

Les images de `documentation/captures/` sont exportées depuis Power BI Desktop, après Actualiser, une page à la fois. Le pipeline ne les produit pas. Le dossier contient la note de dépôt tant que les images n'y ont pas été ajoutées.

## Règles de restitution

- La tolérance est l'agreement du pipeline, écrite avant la comparaison.
- Un nombre d'un rapport est lu dans un fichier du pipeline. Le contrôle le relit après l'écriture.
- Les trois livres sont des portefeuilles hypothétiques construits rétrospectivement sur des données publiques.
- Le rapport Power BI est ouvert et actualisé dans Desktop. Aucun script ne l'enregistre.
