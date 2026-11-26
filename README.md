# Portfolio Construction, Monitoring & Risk Analytics Platform

Plateforme d'analyse d'un mandat discrétionnaire fictif, en francs suisses. Elle part du profil du client, construit trois livres sur des cours publics, mesure la performance et le risque, en tire des recommandations, et restitue le résultat dans des pages, une annexe Excel, un modèle Power BI et un rapport court.

**Autrice :** Faty Barbosa

CLIENT001 est un cas d'école. Aucun compte n'est ouvert. Les trois livres sont des portefeuilles hypothétiques construits rétrospectivement : ils n'ont pas été détenus. Les cours, les changes, le SARON et le rendement publié du fonds iShares sont des données réelles et publiques. Il n'y a pas de relevé de dépositaire, pas de frais, pas de flux. Le rendement des livres est un rendement total brut : dividendes déclarés réinvestis au jour de détachement, avant frais et avant impôt à la source. Le rendement du fonds est celui de sa valeur liquidative publiée par iShares, net de ses frais, converti en francs.

Les textes constatent, alertent par rapport aux limites écrites du mandat et recommandent. Chaque recommandation est écrite par une règle à partir des chiffres du pipeline : quel livre proposer, lesquels ne pas retenir, ce qu'explique le lien avec le fonds, ce qu'il ne faut pas promettre, et quoi faire du plafond de secteur. Quand les chiffres changent, la phrase change. Elles portent sur le mandat fictif CLIENT001 et reposent sur une simulation rétrospective : elles ne constituent ni un conseil en placement ni un ordre.

English summary: [README_EN.md](README_EN.md). Les rapports sont en français.

## Ce qu'un lecteur ouvre d'abord

| Question | Fichier |
|---|---|
| Comment c'est construit | [documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md) |
| Comment le relancer | [documentation/GUIDE_UTILISATEUR.md](documentation/GUIDE_UTILISATEUR.md) |
| Quelles colonnes existent | [documentation/DICTIONNAIRE_DONNEES.md](documentation/DICTIONNAIRE_DONNEES.md) |
| Quelles requêtes SQL interrogent la base et les livres | [sql/](sql/) |
| Le mandat et les limites | [documentation/00_mandat/](documentation/00_mandat/) |
| Le récit de chaque phase | [documentation/](documentation/) |
| Du besoin d'un client au livrable | [documentation/BESOIN_DE_REPORTING.md](documentation/BESOIN_DE_REPORTING.md) |
| Le processus manuel que la commande remplace | [documentation/AUTOMATISATION_AVANT_APRES.md](documentation/AUTOMATISATION_AVANT_APRES.md) |
| Le rapport pour un comité | [reports/executive/rapport_executif.pdf](reports/executive/rapport_executif.pdf) |
| Les recommandations et leurs chiffres | [reports/executive/commentaires_automatises.md](reports/executive/commentaires_automatises.md) |
| Rapport de CLIENT001, et rapport du gérant | [reports/client/](reports/client/) |
| Cinq défauts de données, instruits | [reports/executive/cas_d_investigation.md](reports/executive/cas_d_investigation.md) |
| La présentation | [reports/management/presentation_management.pptx](reports/management/presentation_management.pptx) |
| L'annexe qui rapproche Python, Excel et Power BI | [reports/excel/EXPLICATIONS.md](reports/excel/EXPLICATIONS.md) |

Les chiffres du rapport et de la présentation ne sont pas recopiés ici. Ils sont lus dans les fichiers du pipeline au moment de l'écriture, puis relus par `src/reporting/number_check.py`. Un nombre qui ne s'y retrouve pas arrête la commande.

## Reconstruire

Windows, Python 3.12. Le détail, les prérequis et l'ordre des commandes sont dans le guide.

```bash
python -m src.pipeline.refresh
python -m pytest tests
```

Le passage complet en une commande, avec l'actualisation et l'export Power BI :

```bash
python -m src.pipeline.full_refresh
```

Cette commande demande Excel et Power BI Desktop. La reconstruction mensuelle des données est décrite dans le guide.

Sans Excel ni Windows, `python -m src.pipeline.refresh --skip-office` reconstruit tout sauf l'annexe Excel et les rapports, qui lisent l'annexe. Les prix bruts (Yahoo Finance) ne sont pas versionnés : `data/input_manifest.json` garde l'empreinte des entrées du dernier passage, pour qu'un écart entre deux passages puisse être rattaché à un changement des données.

Les tests lisent les fichiers publiés du dépôt, dont le centre de contrôle qualité `audit/data_control_center.xlsx`. Ils passent sur un clone frais sans lancer le pipeline. Les tests qui demandent Excel (COM) ou les prix bruts sont marqués `office` et `needs_inputs` : ils sont ignorés quand la machine ne les a pas. `.github/workflows/tests.yml` lance le reste sur Linux.

Fermer `reports/excel/annexe_reporting.xlsx` avant le rafraîchissement. Un classeur ouvert verrouille le fichier.

## Périmètre

La série macro du mandat est le SARON, le taux sans risque. Les cours, les changes et le rendement publié du fonds viennent des sources nommées dans le registre. Le périmètre s'arrête à ces données publiques.

## Où chaque partie du travail se lit

| Sujet | Emplacement |
|---|---|
| Mandat, profil, limites | `documentation/00_mandat/` |
| Python, de l'acquisition au rapport | `src/` |
| SQL | Base SQLite locale et [sql/](sql/) |
| Power BI | `dashboards/powerbi/` |
| Indicateurs de performance et de risque | Phases 7, 8 et 9 |
| Qualité des données | Phase 4, centre de contrôle, page Data Quality |
| Rapport et présentation | `reports/executive/`, `reports/management/` |
| Enchaînement complet | `python -m src.pipeline.refresh` |
| Tolérance et écarts | Écrits avant la comparaison, laissés visibles |
