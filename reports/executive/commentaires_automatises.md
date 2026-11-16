# Commentaires automatisés

**Généré automatiquement, à relire avant diffusion.**

Produit par `python -m src.pipeline.refresh` le 2026-11-16 07:47 UTC. Portefeuilles hypothétiques construits rétrospectivement sur des données publiques : ils n'ont jamais été détenus. Les cours, les cours de change et le SARON sont des données réelles et publiques. Pas de données de conservation, pas de frais, pas de dividendes dans le rendement des livres.

Chaque nombre de ce texte est relu dans un fichier du pipeline par `src/reporting/number_check.py`. La liste des nombres et de leur source est dans `controle_des_nombres.csv`.

## Faits marquants

- La fenêtre couvre 120 mois, de 2016-11 à 2026-10. Les trois livres, hypothétiques et construits rétrospectivement sur des données publiques, partagent la même liste de 29 titres : ce sont les titres au statut Eligible du registre ODD qui ont un historique complet en CHF, sur 120 titres examinés.
- Rendement annualisé en CHF : Équipondéré 5,29 %, Volatilité minimale 3,87 %, Sharpe maximal 4,35 %, contre 6,08 % pour le fonds iShares, rendement de la valeur liquidative converti en CHF. Aucun livre ne dépasse le fonds sur la fenêtre. La comparaison n'est pas à périmètre égal : le rendement des livres n'inclut pas les dividendes, celui du fonds est un rendement total publié.
- Ratio de Sharpe contre le SARON : Équipondéré 0,49, Volatilité minimale 0,39, Sharpe maximal 0,41, fonds 0,52. Le livre Équipondéré a le Sharpe le plus élevé des trois livres.
- Richesse finale pour une unité investie au début de la fenêtre, sans choc : Équipondéré 1,67, Volatilité minimale 1,46, Sharpe maximal 1,53.
- Contrôle des calculs : sur 102 lignes de réconciliation, 101 sont OK entre Python et Excel, 0 en EXCEPTION et 1 non publiée. La tolérance est de 1e-8, fixée avant la comparaison.

## Risques identifiés

- Volatilité annualisée : Équipondéré 12,37 %, Volatilité minimale 11,79 %, Sharpe maximal 12,61 %, fonds 13,24 %.
- Perte mensuelle historique, lue sur les 5 % de mois les plus défavorables : Équipondéré VaR -5,52 % et expected shortfall -8,02 %; Volatilité minimale VaR -6,25 % et expected shortfall -7,60 %; Sharpe maximal VaR -6,53 % et expected shortfall -8,58 %; Fonds iShares (CHF) VaR -5,50 % et expected shortfall -7,42 %. Ce sont des rendements mensuels observés, sans loi normale et sans annualisation.
- Pire mois de la fenêtre : Équipondéré -11,85 % en 2020-03, Volatilité minimale -10,55 % en 2020-03, Sharpe maximal -12,76 % en 2022-09.
- Drawdown maximal : Équipondéré -26,44 %, du sommet de 2021-08 au creux de 2023-10; Volatilité minimale -25,68 %, du sommet de 2021-08 au creux de 2023-10; Sharpe maximal -30,32 %, du sommet de 2021-08 au creux de 2025-06. À la fin de la fenêtre, le sommet n'est pas retrouvé pour : Équipondéré, Volatilité minimale, Sharpe maximal.
- Corrélation : la moyenne des paires de la liste est de 0,17 sur 29 titres. La paire la plus liée est COVIVIO SA et GECINA SA, à 0,77. Une corrélation moyenne basse ne protège pas dans un mois de baisse générale : les pires mois des trois livres sont proches.
- Concentration au mois de 2026-10 : Équipondéré 34,48 % sur les 10 premières lignes, 29,0 lignes effectives, premier secteur Health Care à 34,48 %; Volatilité minimale 50,00 % sur les 10 premières lignes, 22,3 lignes effectives, premier secteur Health Care à 39,71 %; Sharpe maximal 49,03 % sur les 10 premières lignes, 22,5 lignes effectives, premier secteur Health Care à 39,79 %.
- Tests de résistance, illustratifs : richesse finale la plus basse des quatre chocs, pour une unité investie. Équipondéré 1,29 avec le choc récession, contre 1,67 sans choc; Volatilité minimale 1,16 avec le choc récession, contre 1,46 sans choc; Sharpe maximal 1,18 avec le choc récession, contre 1,53 sans choc. Les chocs sont des paramètres écrits à l'avance, appliqués aux rendements déjà publiés. Ce ne sont pas des prévisions.

## Alertes

- Aucun dépassement de plafond sur la fenêtre. Nombre de mois-livres au-dessus d'une limite : émetteur 0, secteur 0, zone 0, devise 0, bande de lignes 0. Plafonds du mandat : émetteur 5 %, secteur 40 %, zone 50 %, devise 40 %, 25 à 40 lignes pour les livres optimisés.
- **Alerte.** Volatilité minimale : le premier secteur (Health Care) pèse 39,71 % pour un plafond de 40 %. Le poids dépasse 95 % du plafond, seuil de vigilance du rapport et non limite du mandat.
- **Alerte.** Sharpe maximal : le premier secteur (Health Care) pèse 39,79 % pour un plafond de 40 %. Le poids dépasse 95 % du plafond, seuil de vigilance du rapport et non limite du mandat.
- **Alerte.** Sharpe maximal : la première zone (Europe) pèse 49,89 % pour un plafond de 50 %. Le poids dépasse 95 % du plafond, seuil de vigilance du rapport et non limite du mandat.
- **Alerte.** Écart de suivi mesuré contre le fonds : Équipondéré 7,68 %, Volatilité minimale 8,23 %, Sharpe maximal 8,68 %, pour une cible ex ante de 8 % dans la politique d'investissement. Au-dessus de la cible : Volatilité minimale, Sharpe maximal. La cible n'est pas appliquée aux poids publiés : c'est une mesure après coup.
- **Alerte.** Drawdown maximal au-delà du repère de 30 % du profil du client : Sharpe maximal -30,32 %. Le profil accepte une perte temporaire au-delà de ce repère et précise qu'il ne déclenche pas, à lui seul, une vente.
- Rotation : 0 rééquilibrage au-dessus du plafond trimestriel de 12,5 % et 0 au-dessus du plafond annuel. La rotation la plus forte observée est de 12,5 %.
- **Alerte.** Qualité des données : score global 99,68 %, note A, statut WARNING. 6 catégories d'anomalies sur 54 contrôles. La plus étendue : cohérence des devises sur la table securities_master, 11 lignes sur 120, soit 9,17 %, gravité MEDIUM.
- Colonne Power BI de la réconciliation : 101 lignes OK sur une valeur lue dans Power BI Desktop, 0 en EXCEPTION, 0 en attente d'export.

## Points à instruire

- Faire revoir par le gérant, avant le prochain rééquilibrage, les livres proches d'un plafond : Volatilité minimale, Sharpe maximal. Une hausse relative du premier secteur ou de la première zone suffirait à franchir la limite entre deux rééquilibrages.
- Décider si la cible d'écart de suivi de 8 % doit entrer dans la construction des poids. Aujourd'hui elle est écrite dans la politique mais n'est pas appliquée.
- Traiter l'anomalie de gravité MEDIUM du contrôle qualité : cohérence des devises, 11 titres de la table securities_master sans série de change. Ces titres ne peuvent pas être convertis en CHF et restent hors des livres.
- Avant toute présentation comme performance réelle : obtenir des données de conservation (positions, transactions, frais, flux). La réconciliation prouve que les formules se recoupent, pas que les titres ont été détenus.
- Ajouter les dividendes au rendement des livres, ou comparer au rendement en prix du fonds, pour rendre la comparaison au fonds homogène.

Ces points sont des constats et des alertes liés aux limites écrites du mandat. Ce ne sont pas des recommandations d'investissement personnalisées.
