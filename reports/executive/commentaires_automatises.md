# Commentaires automatisés

**Généré automatiquement, à relire avant diffusion.**

Produit par `python -m src.pipeline.refresh` le 2026-11-17 14:29 UTC. Portefeuilles hypothétiques construits rétrospectivement sur des données publiques : ils n'ont jamais été détenus. Les cours, les cours de change et le SARON sont des données réelles et publiques. Pas de données de conservation et pas de frais. Les livres sont mesurés en rendement total brut : dividendes réinvestis par le cours ajusté, avant frais et avant impôt à la source. Le fonds est mesuré par le rendement de sa valeur liquidative, net de ses frais : la comparaison avantage donc les livres.

Chaque nombre de ce texte est relu dans un fichier du pipeline par `src/reporting/number_check.py`. La liste des nombres et de leur source est dans `controle_des_nombres.csv`.

## Faits marquants

- La fenêtre couvre 120 mois, de 2016-11 à 2026-10. Les trois livres, hypothétiques et construits rétrospectivement sur des données publiques, partagent la même liste de 29 titres : ce sont les titres au statut Eligible du registre ODD qui ont un historique complet en CHF, sur 120 titres examinés.
- Rendement annualisé en CHF : Équipondéré 7,51 %, Volatilité minimale 6,24 %, Sharpe maximal 6,09 %, contre 6,08 % pour le fonds iShares, rendement de la valeur liquidative converti en CHF. Les trois livres dépassent le fonds sur la fenêtre, le livre Équipondéré le plus nettement. Les livres sont mesurés en rendement total brut : dividendes réinvestis par le cours ajusté, avant frais et avant impôt à la source. Le fonds est mesuré par le rendement de sa valeur liquidative, net de ses frais : la comparaison avantage donc les livres.
- Ratio de Sharpe contre le SARON : Équipondéré 0,66, Volatilité minimale 0,58, Sharpe maximal 0,55, fonds 0,52. Le livre Équipondéré a le Sharpe le plus élevé des trois livres.
- Richesse finale pour une unité investie au début de la fenêtre, sans choc : Équipondéré 2,06, Volatilité minimale 1,83, Sharpe maximal 1,81.
- Contrôle des calculs : sur 102 lignes de réconciliation, 101 sont OK entre Python et Excel, 0 en EXCEPTION et 1 non publiée. La tolérance est de 1e-8, fixée avant la comparaison.

## Risques identifiés

- Volatilité annualisée : Équipondéré 12,31 %, Volatilité minimale 11,80 %, Sharpe maximal 12,31 %, fonds 13,24 %.
- Perte mensuelle historique, lue sur les 5 % de mois les plus défavorables : Équipondéré VaR -5,35 % et expected shortfall -7,80 %; Volatilité minimale VaR -6,04 % et expected shortfall -7,51 %; Sharpe maximal VaR -5,56 % et expected shortfall -8,03 %; Fonds iShares (CHF) VaR -5,50 % et expected shortfall -7,42 %. Ce sont des rendements mensuels observés, sans loi normale et sans annualisation.
- Limite de l'échantillon : la VaR est lue sur 120 mois, et l'expected shortfall est la moyenne des 6 pires mois. Ce sont de petits échantillons : aucun intervalle de confiance n'est calculé, et un seul mois de plus ou de moins déplace ces chiffres.
- Pire mois de la fenêtre : Équipondéré -11,47 % en 2020-03, Volatilité minimale -10,72 % en 2020-03, Sharpe maximal -11,71 % en 2022-09.
- Drawdown maximal : Équipondéré -23,63 %, du sommet de 2021-08 au creux de 2023-10; Volatilité minimale -22,81 %, du sommet de 2021-08 au creux de 2023-10; Sharpe maximal -28,62 %, du sommet de 2021-08 au creux de 2023-10. À la fin de la fenêtre, le sommet n'est pas retrouvé pour : Équipondéré, Volatilité minimale, Sharpe maximal.
- Corrélation : la moyenne des paires de la liste est de 0,17 sur 29 titres. La paire la plus liée est COVIVIO SA et GECINA SA, à 0,77. Une corrélation moyenne basse ne protège pas dans un mois de baisse générale : les pires mois des trois livres sont proches.
- Concentration au mois de 2026-10 : Équipondéré 34,48 % sur les 10 premières lignes, 29,0 lignes effectives, premier secteur Health Care à 34,48 %; Volatilité minimale 49,72 % sur les 10 premières lignes, 22,9 lignes effectives, premier secteur Health Care à 39,80 %; Sharpe maximal 48,63 % sur les 10 premières lignes, 23,3 lignes effectives, premier secteur Health Care à 39,72 %.
- Tests de résistance, illustratifs : richesse finale la plus basse des quatre chocs, pour une unité investie. Équipondéré 1,57 avec le choc récession, contre 2,06 sans choc; Volatilité minimale 1,44 avec le choc récession, contre 1,83 sans choc; Sharpe maximal 1,40 avec le choc récession, contre 1,81 sans choc. Les chocs sont des paramètres écrits à l'avance, appliqués aux rendements déjà publiés. Ce ne sont pas des prévisions.
- Le choc de marché (-20 % sur le dernier mois) est plus sévère que le pire mois réellement observé (-11,71 %, livre Sharpe maximal). Le choc de taux ne change pas le rendement des actions : il ne modifie que le taux sans risque, donc le ratio de Sharpe. Ce n'est pas un test de sensibilité des titres aux taux. Aucun scénario daté n'est rejoué en dehors des pires mois observés ci-dessus.
- Éligibilité ODD : sur 120 titres examinés, 42 sont Eligible, 65 Indeterminate et 13 Not_Eligible. Les statuts sont saisis par un seul analyste à partir de rapports de sociétés qui ne sont pas versionnés : un tiers ne peut pas les rejouer depuis ce dépôt. La liste de titres est la composition actuelle du fonds de référence, et l'éligibilité ODD a été jugée à la date de saisie du registre puis appliquée à tout l'historique : les sociétés sorties du fonds n'y figurent pas, ce qui peut embellir le résultat.

## Alertes

- Aux dates de décision, aucun livre ne dépasse un plafond de construction. Mois-livres au-dessus d'une limite, comptés sur les 123 mois-livres de décision (début de trimestre) : émetteur 0, secteur (plafond de travail) 0, zone 0, devise 0, bande de lignes 0. Plafonds : émetteur 5 %, zone 50 %, devise 40 %, secteur 40 % (plafond de travail, voir ci-dessous), 25 à 40 lignes pour les livres optimisés.
- **Alerte.** Entre deux décisions, les poids dérivent avec le marché et un livre ne se corrige qu'au rééquilibrage suivant. Dépassements passifs, en mois-livres sur 237 : émetteur 161, secteur (plafond de travail) 30, zone 5, devise 0. Le plus gros poids d'un titre atteint 6,97 % pour un plafond de 5 %. Le mandat ne dit pas si un dépassement passif est toléré jusqu'au prochain rééquilibrage : la décision est à prendre.
- **Alerte.** Plafond de secteur écrit dans le mandat : 20 %. Il est dépassé dans 360 mois-livres sur 360. Sur cette liste, un livre entièrement investi ne peut pas respecter ce plafond : au plus 85 % du livre peut être placé sous le plafond d'émetteur de 5 % et ce plafond de secteur. Les livres sont donc construits avec un plafond de travail de 40 %, qui n'a pas été approuvé par le client. C'est un écart ouvert entre le mandat et la construction, pas une conformité.
- **Alerte.** Volatilité minimale : le premier secteur (Health Care) pèse 39,80 % pour un plafond de travail de 40 %. Le poids dépasse 95 % du plafond, seuil de vigilance du rapport et non limite du mandat.
- **Alerte.** Sharpe maximal : le premier secteur (Health Care) pèse 39,72 % pour un plafond de travail de 40 %. Le poids dépasse 95 % du plafond, seuil de vigilance du rapport et non limite du mandat.
- **Alerte.** Sharpe maximal : la première zone (Europe) pèse 50,00 % pour un plafond de 50 %. Le poids dépasse 95 % du plafond, seuil de vigilance du rapport et non limite du mandat.
- **Alerte.** Écart de suivi mesuré contre le fonds : Équipondéré 7,78 %, Volatilité minimale 8,34 %, Sharpe maximal 8,59 %, pour une cible ex ante de 8 % dans la politique d'investissement. Au-dessus de la cible : Volatilité minimale, Sharpe maximal. La cible n'est pas appliquée aux poids publiés : c'est une mesure après coup.
- **Alerte.** Rotation brute, mesurée contre le livre que le marché a laissé, dérive comprise : Équipondéré : plafond trimestriel dépassé 4 fois, plafond annuel dépassé 1 fois; Volatilité minimale : plafond trimestriel dépassé 0 fois, plafond annuel dépassé 0 fois; Sharpe maximal : plafond trimestriel dépassé 9 fois, plafond annuel dépassé 20 fois. Plafonds : 12,5 % par trimestre. La rotation la plus forte observée est de 18,6 %. À la date de transaction, les plafonds de poids priment sur le budget de rotation : quand les deux ne tiennent pas ensemble, la rotation dépasse.
- **Alerte.** Qualité des données : score global 99,68 %, note A, statut WARNING. 6 catégories d'anomalies sur 54 contrôles. La plus étendue : cohérence des devises sur la table securities_master, 11 lignes sur 120, soit 9,17 %, gravité MEDIUM.
- Le score de qualité est pondéré par les enregistrements : 650 954 lignes de cours sur 661 824 enregistrements contrôlés. Il masque donc les défauts qui touchent peu de lignes mais des titres entiers : le contrôle de cohérence des devises signale 11 titres sur 120 (9,17 %) sans série de change.
- Colonne Power BI de la réconciliation : 101 lignes OK sur une valeur lue dans Power BI Desktop, 0 en EXCEPTION, 0 en attente d'export. Sur ces lignes, 7 sont recalculées en DAX à partir des rendements et 94 relisent la cellule publiée : ces dernières prouvent le chargement du bon fichier, pas un second calcul.

## Points à instruire

- Faire revoir par le gérant, avant le prochain rééquilibrage, les livres proches d'un plafond : Volatilité minimale, Sharpe maximal. Une hausse relative du premier secteur ou de la première zone suffirait à franchir la limite entre deux rééquilibrages.
- Faire approuver ou refuser par le client le plafond de travail de secteur de 40 %, contre 20 % écrit dans le mandat. Tant qu'il ne l'est pas, le dépassement du plafond écrit reste ouvert.
- Décider du traitement des dépassements passifs : toléré jusqu'au rééquilibrage suivant, ou corrigé dès qu'il apparaît. Le mandat ne le dit pas.
- Décider si la cible d'écart de suivi de 8 % doit entrer dans la construction des poids. Aujourd'hui elle est écrite dans la politique mais n'est pas appliquée.
- Traiter l'anomalie de gravité MEDIUM du contrôle qualité : cohérence des devises, 11 titres de la table securities_master sans série de change. Ces titres ne peuvent pas être convertis en CHF et restent hors des livres.
- Avant toute présentation comme performance réelle : obtenir des données de conservation (positions, transactions, frais, flux). La réconciliation prouve que les formules se recoupent, pas que les titres ont été détenus, ni que les définitions sont les bonnes.
- Rendre la comparaison au fonds strictement homogène : le rendement total des livres est brut de frais et d'impôt à la source, celui du fonds est net de ses frais. Il manque une série de rendement du fonds avant frais.

Ces points sont des constats et des alertes liés aux limites écrites du mandat. Ce ne sont pas des recommandations d'investissement personnalisées.
