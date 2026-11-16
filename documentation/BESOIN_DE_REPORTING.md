# Du besoin de reporting au livrable

Lu avec le [README](../README.md) et le mandat dans `documentation/00_mandat/`.

Cette page part de la demande d'un client, pas du calcul. Pour chaque attente, elle nomme la donnée qui y répond, le calcul, le contrôle qui le vérifie, et le fichier ou la page qui le montre. Les chiffres ne sont pas recopiés ici : ils sont dans les livrables, où le contrôle des nombres les relit.

CLIENT001 est un cas d'école. Les trois livres sont des portefeuilles hypothétiques construits rétrospectivement sur des données publiques. Les cours, les changes et le SARON sont des données réelles et publiques. Il n'y a pas de données de conservation : ni positions réelles, ni transactions, ni frais. Là où une demande suppose un dépositaire, la page le dit.

## Un rapport pour le client, un rapport pour le gérant

Le client du mandat est CLIENT001. Le gérant suit les mêmes livres. Les deux rapports lisent les mêmes fichiers et ne recalculent rien : seule la sélection des pages change.

| | CLIENT001 | Gérant |
|---|---|---|
| Ce que la page montre | Allocation par secteur, zone et devise, limites du mandat | Lignes, contributeurs et détracteurs, mouvements de poids, devises |
| Ce que la page laisse de côté | La performance, le risque, les chocs et le détail des lignes | Les limites et les tests de résistance |
| Livrable | `reports/client/rapport_client.pdf` | `reports/client/rapport_gerant.pdf` |

## Attente, donnée, calcul, contrôle, livrable

| Attente du client | Donnée | Calcul | Contrôle | Livrable |
|---|---|---|---|---|
| Que détient le livre, à quel poids ? | `portfolio_weights.csv`, feuille de positions iShares pour le secteur et le pays | Poids du trimestre, projetés sous les plafonds | Les poids somment à un ; aucun poids sous le plancher n'est compté comme ligne | Rapport gérant, Vue d'ensemble Excel, page Portfolio Overview |
| Dans quelle devise, quel secteur, quelle zone ? | `allocation_by_sector`, `allocation_by_zone`, `exposure` | Somme des poids par groupe | Chaque groupe rejoint un plafond écrit ; un pays hors liste va dans « Non classé » et reste plafonné | Rapport de CLIENT001, Power BI, Excel |
| Les limites sont-elles respectées ? | `limit_watch.csv`, plafonds de `src/config.py` | Comparaison du plus grand poids de chaque famille au plafond, chaque mois | Un dépassement est compté et conservé ; le seuil de vigilance du rapport n'est pas une limite du mandat | Rapport de CLIENT001, commentaires, page Monitoring |
| Qu'est-ce qui a changé depuis le dernier rapport ? | `weight_changes.csv`, `turnover.csv` | Poids avant et après chaque rééquilibrage trimestriel | Les variations absolues reconstituent la rotation brute publiée | Rapport gérant |
| Quelle performance, contre quoi ? | `portfolio_monthly_returns`, `benchmark_monthly_return`, `performance_metrics` | Rendement chaîné, annualisé, Sharpe, Sortino, écart de suivi, ratio d'information contre le fonds iShares en CHF | Excel recalcule à partir des seuls rendements ; Power BI relit la cellule ; écart laissé en EXCEPTION s'il dépasse la tolérance | Rapport exécutif, annexe Excel |
| Quels titres ont contribué, lesquels ont pesé ? | `holding_contribution.csv` | Poids multiplié par rendement en CHF, par titre et par mois | Les titres d'un mois reconstituent le rendement du livre ; les titres d'un secteur reconstituent la ligne du secteur | Rapport gérant |
| Où sont les concentrations et les expositions ? | `concentration.csv`, `top10_positions.csv`, matrice de corrélation | Poids des dix premières lignes, indice de concentration, nombre effectif de lignes, corrélation moyenne | Mêmes valeurs dans le rapport mensuel et dans le suivi des limites | Rapport exécutif, page Risk Analytics |
| Quelle perte dans un mauvais mois ? | `risk_by_strategy`, `var_tail` | VaR historique et expected shortfall mensuels, niveau écrit dans le module de risque | La volatilité rejoint celle de la phase 5 ; la queue est publiée mois par mois | Rapport exécutif, Excel, Power BI |
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
