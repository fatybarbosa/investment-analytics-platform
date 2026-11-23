# Guide d'utilisation

Lu avec le [README](../README.md). Les textes produits par le pipeline portent la mention « généré automatiquement, à relire avant diffusion ».

## Préparer la machine

- Python 3.12. Windows pour l'annexe Excel et les rapports.
- Dépendances : `pip install -r requirements/requirements.txt`, et `requirements/requirements-dev.txt` pour les tests.
- Excel, pour le recalcul de l'annexe par COM. Sans Excel : `python -m src.pipeline.refresh --skip-office`.
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

Le test d'injection travaille sur une copie. Il ne modifie pas les fichiers de production. Les tests marqués `office` (Excel par COM) et `needs_inputs` (prix bruts et base locale, non versionnés) sont ignorés quand la machine ne les a pas. Les notebooks de validation des phases s'exécutent sous pytest quand les entrées sont là : `python -m pytest -m notebook`. Une machine sans ces entrées lance `python -m pytest -m "not office and not needs_inputs"`.

## Reconstruction mensuelle

La fenêtre de mesure est mensuelle : un nouveau mois n'entre que lorsque le SARON et le rendement du fonds l'ont publié. Une reconstruction par mois suffit. Elle se fait en deux temps.

**1. Les données, sans personne.** Sur la machine de travail, une tâche Windows `InvestmentAnalytics-MonthlyRefresh` lance `scripts/monthly_refresh.cmd` le 5 de chaque mois à 8 h. Si la machine est éteinte à ce moment, elle part au prochain démarrage. Le script lance `python -m src.pipeline.refresh --skip-office` et écrit dans `logs/monthly_refresh.log`. Il reconstruit les données, la base, les livres, le suivi, la performance, le risque, les chocs et la qualité. Il ne touche ni à l'annexe Excel ni aux rapports, n'ouvre pas Power BI et ne valide rien dans git. Un message à l'écran rappelle l'étape suivante.

**2. Le passage complet, devant l'écran.**

```bash
python -m src.pipeline.full_refresh
```

La commande vérifie que l'annexe n'est pas ouverte dans Excel, refait l'étape 1, ouvre Power BI Desktop s'il est fermé, actualise le modèle en mémoire, exporte les mesures, referme Desktop sans enregistrer s'il a été ouvert par la commande, puis lance le `refresh` complet : annexe, rapprochement Python, Excel et Power BI, rapports. Elle s'arrête si une ligne de rapprochement reste ouverte ou si un nombre d'un texte n'est dans aucun fichier. À la fin, elle liste les fichiers modifiés. Elle ne commite rien : les textes portent « à relire avant diffusion », une personne les lit, puis les versionne.

Pour arrêter la tâche mensuelle : `schtasks /Delete /TN "InvestmentAnalytics-MonthlyRefresh" /F`.

## Lire les restitutions

| Restitution | Ouverture |
|---|---|
| Pages HTML | `reports/monitoring`, `reports/performance`, `reports/risk`, `reports/stress` |
| Annexe Excel | `reports/excel/annexe_reporting.xlsx`, après Actualiser tout |
| Explications de l'annexe | `reports/excel/EXPLICATIONS.md` |
| Power BI | `dashboards/powerbi/Investment Analytics.pbip`, puis Actualiser |
| Rapport exécutif | `reports/executive/rapport_executif.pdf` |
| Rapport de CLIENT001 | `reports/client/rapport_client.pdf` |
| Rapport du gérant | `reports/client/rapport_gerant.pdf` |
| Présentation | `reports/management/presentation_management.pptx` |
| Commentaires | `reports/executive/commentaires_automatises.md` |
| Cas d'investigation | `reports/executive/cas_d_investigation.md` |

Les pages Power BI sont : Portfolio Overview, Suivi, Performance Analytics, Risk Analytics, Stress Testing, Data Quality. Le filtre des pages d'allocation, de suivi et de chocs ne propose pas le fonds. Les pages de performance et de risque le proposent, parce qu'elles lisent une série de rendement.

## Ouvrir Power BI, puis exporter les mesures

1. Ouvrir Power BI Desktop.
2. Fichier, Ouvrir, puis `dashboards/powerbi/Investment Analytics.pbip`.
3. Régler le paramètre `ProjectRoot` sur le dossier du clone (Transformer les données, Gérer les paramètres), puis Actualiser. Les données ne sont pas dans le fichier : elles sont relues dans les CSV du projet. Le dépôt garde une valeur neutre pour ce paramètre.
4. Laisser Desktop ouvert.
5. Dans le dossier du projet, lancer :

```bash
python -m src.reporting.power_bi_export
```

La commande interroge le moteur de Desktop. Elle ne calcule pas les mesures elle-même, et elle n'enregistre pas le rapport. Si Desktop est fermé, elle s'arrête et n'écrit rien. Le résultat est `reports/excel/power_bi_export.csv`. L'annexe Excel s'en sert à la génération suivante pour la colonne Power BI.

## SQL

La base `database/sdg_investment.db` n'est pas dans le dépôt. Le rafraîchissement la reconstruit. Les requêtes de `sql/` s'exécutent alors. `python -m src.reporting.data_dictionary` les exécute et réécrit le dictionnaire. Une requête qui échoue arrête la commande.

Pour les lire dans un client SQLite, ouvrir la base locale et exécuter le fichier. Les requêtes interrogent le contrôle qualité, le registre, le SARON publié, la feuille de positions du fonds, et les trois livres une fois leurs fichiers chargés dans la base. Elles ne recalculent pas le Sharpe ni la VaR. Une requête chaîne la richesse en SQL et la compare à celle de la phase 6.

## Entrées non versionnées

Les prix bruts de Yahoo Finance (`data/01_raw/market/market_prices.csv`), les cours en francs de `data/02_processed/` et la base SQLite ne sont pas dans le dépôt. Une nouvelle acquisition peut donner d'autres chiffres, parce que les sources révisent leurs séries. `data/input_manifest.json` garde le SHA-256 et la taille des entrées brutes du dernier passage : un hash différent explique un résultat différent.

## Dictionnaire

```bash
python -m src.reporting.data_dictionary
```

Le fichier écrit est `documentation/DICTIONNAIRE_DONNEES.md`. Les nombres de lignes viennent du comptage du fichier, pas d'une saisie.

## Règles de restitution

- La tolérance est l'agreement du pipeline, écrite avant la comparaison.
- Un nombre d'un rapport est lu dans un fichier du pipeline. Le contrôle le relit après l'écriture.
- Les trois livres sont des portefeuilles hypothétiques construits rétrospectivement sur des données publiques.
- Le rapport Power BI est ouvert et actualisé dans Desktop. Aucun script ne l'enregistre.
