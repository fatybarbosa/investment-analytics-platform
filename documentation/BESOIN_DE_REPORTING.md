# Du besoin de reporting au livrable

Lu avec le [README](../README.md) et le mandat dans `documentation/00_mandat/`.

Cette page part de la demande d'un client, pas du calcul. Pour chaque attente, elle nomme la donnée qui y répond, le calcul, le contrôle qui le vérifie, et le fichier ou la page qui le montre. Les chiffres ne sont pas recopiés ici : ils sont dans les livrables, où le contrôle des nombres les relit.

CLIENT001 est un cas d'école. Les trois livres sont des portefeuilles hypothétiques construits rétrospectivement sur des données publiques. Les cours, les changes et le SARON sont des données réelles et publiques. Il n'y a pas de données de conservation : ni positions réelles, ni transactions, ni frais. Là où une demande suppose un dépositaire, la page le dit.

## Deux lectures du mandat CLIENT001

Le client du mandat est CLIENT001. Il n'y en a pas d'autre. Les deux rapports lisent les mêmes fichiers et ne recalculent rien : seule la sélection des pages change.

| | Lecture allocation | Lecture lignes |
|---|---|---|
| Ce que la page montre | Allocation, limites du mandat, performance contre le fonds, risque | Lignes, contributeurs et détracteurs, mouvements de poids, devises |
| Ce que la page laisse de côté | Le détail des lignes | Les limites, les tests de résistance |
| Livrable | `reports/clients/rapport_mensuel_allocation.pdf` | `reports/clients/rapport_mensuel_lignes.pdf` |
| Même livrable en anglais | `reports/clients/monthly_report_allocation.pdf` | `reports/clients/monthly_report_lines.pdf` |

## Attente, donnée, calcul, contrôle, livrable

| Attente du client | Donnée | Calcul | Contrôle | Livrable |
|---|---|---|---|---|
| Que détient le livre, à quel poids ? | `portfolio_weights.csv`, feuille de positions iShares pour le secteur et le pays | Poids du trimestre, projetés sous les plafonds | Les poids somment à un ; aucun poids sous le plancher n'est compté comme ligne | Lecture lignes, Vue d'ensemble Excel, page Portfolio Overview |
| Dans quelle devise, quel secteur, quelle zone ? | `allocation_by_sector`, `allocation_by_zone`, `exposure` | Somme des poids par groupe | Chaque groupe rejoint un plafond écrit ; un pays hors liste va dans « Non classé » et reste plafonné | Lecture allocation, Power BI, Excel |
| Les limites sont-elles respectées ? | `limit_watch.csv`, plafonds de `src/config.py` | Comparaison du plus grand poids de chaque famille au plafond, chaque mois | Un dépassement est compté et conservé ; le seuil de vigilance du rapport n'est pas une limite du mandat | Lecture allocation, commentaires, page Monitoring |
| Qu'est-ce qui a changé depuis le dernier rapport ? | `weight_changes.csv`, `turnover.csv` | Poids avant et après chaque rééquilibrage trimestriel | Les variations absolues reconstituent la rotation brute publiée | Lecture lignes |
| Quelle performance, contre quoi ? | `portfolio_monthly_returns`, `benchmark_monthly_return`, `performance_metrics` | Rendement chaîné, annualisé, Sharpe, Sortino, écart de suivi, ratio d'information contre le fonds iShares en CHF | Excel recalcule à partir des seuls rendements ; Power BI relit la cellule ; écart laissé en EXCEPTION s'il dépasse la tolérance | Les deux rapports, rapport exécutif, annexe Excel |
| Quels titres ont contribué, lesquels ont pesé ? | `holding_contribution.csv` | Poids multiplié par rendement en CHF, par titre et par mois | Les titres d'un mois reconstituent le rendement du livre ; les titres d'un secteur reconstituent la ligne du secteur | Lecture lignes |
| Où sont les concentrations et les expositions ? | `concentration.csv`, `top10_positions.csv`, matrice de corrélation | Poids des dix premières lignes, indice de concentration, nombre effectif de lignes, corrélation moyenne | Mêmes valeurs dans le rapport mensuel et dans le suivi des limites | Lecture allocation, page Risk Analytics |
| Quelle perte dans un mauvais mois ? | `risk_by_strategy`, `var_tail` | VaR historique et expected shortfall mensuels, niveau écrit dans le module de risque | La volatilité rejoint celle de la phase 5 ; la queue est publiée mois par mois | Les deux rapports, Excel, Power BI |
| Que devient le livre sous un choc ? | `stress_results`, `stress_paths`, paramètres de `src/config.py` | Quatre chocs appliqués aux rendements publiés | La ligne sans choc rejoint la phase 5 | Rapport exécutif, page Stress Testing. Étiquetés « illustratifs » |
| Les données sont-elles fiables ? | Centre de contrôle `audit/data_control_center.xlsx` | Six contrôles sur chaque table chargée | Un écart est enregistré avec sa cause ; aucune tolérance n'est modifiée | Page Data Quality, rapport exécutif, `cas_d_investigation.md` |
| Les chiffres du rapport sont-ils ceux du pipeline ? | `controle_des_nombres.csv` | Chaque nombre d'un texte est relu dans son fichier | Un nombre sans source arrête la commande | Tous les livrables de la phase 11 |

## Ce qu'un dépositaire apporterait, et que le projet n'a pas

| Attente | Situation |
|---|---|
| Positions réellement détenues | Absentes. Les livres sont hypothétiques. |
| Transactions entre deux dates | Absentes. Les mouvements publiés sont des changements de poids, pas des ordres. |
| Rapprochement de la valeur du portefeuille contre le dépositaire | Impossible sans relevé. Le rapprochement existant porte sur les formules : Python, Excel, Power BI. |
| Frais, impôts, dividendes encaissés | Absents du rendement des livres. Le fonds de comparaison publie un rendement total. |
| Identifiants ISIN | Absents. L'identité d'un titre est le ticker et la place de cotation. |

## Comment une demande entre dans le projet

1. La demande est écrite dans cette page, avec la donnée qui y répond. Si la donnée n'existe pas dans une source nommée, la ligne va dans le tableau précédent.
2. Le calcul est placé dans le module de la phase concernée, avec son contrôle. Un calcul sans contrôle n'est pas publié.
3. Le livrable lit le fichier publié. Il ne recalcule pas.
4. Le contrôle des nombres relit le livrable. La relecture humaine vient après, avant diffusion.
