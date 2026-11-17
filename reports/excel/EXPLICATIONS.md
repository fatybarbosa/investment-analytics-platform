# Annexe Excel

## Formules

Le recalcul part des rendements mensuels. Il ne lit pas les indicateurs déjà écrits par Python.

Ces rendements mensuels sont ceux du pipeline : rendement total en CHF, avec le cours ajusté des dividendes converti au cours BNS de fin de mois, et des poids qui dérivent entre deux rééquilibrages trimestriels. Excel ne refait pas cette étape. Il ne peut donc pas détecter une erreur de base de rendement ou de dérive : il vérifie que les indicateurs sont bien calculés à partir de ces rendements.

Le rendement chaîné est le produit des `1 + r`, moins un. Le rendement annualisé est ce produit élevé à la puissance `12 / T`, moins un. `T` est le nombre de mois. L'annualisation n'utilise pas 252.

La volatilité annualisée est l'écart-type d'échantillon des rendements du portefeuille, diviseur `T - 1`, multiplié par la racine de 12. Ce n'est pas l'écart-type de l'excédent.

Le Sharpe est la moyenne de l'excédent sur le SARON, divisée par l'écart-type d'échantillon de cet excédent, multipliée par la racine de 12. Le SARON mensuel est `(1 + taux annuel en pourcentage / 100) ^ (1 / 12) - 1`.

Le Sortino met au numérateur la même moyenne d'excédent. Au dénominateur, chaque mois au-dessus du SARON contribue 0 et chaque mois en dessous contribue le carré de l'excédent. Le diviseur reste `T - 1`, puis on annualise par la racine de 12.

Le drawdown est la richesse divisée par son maximum courant, moins un. Le drawdown maximal est le minimum de cette série. La richesse part de `1 + r` au premier mois.

La VaR historique à 95 % est le rendement du rang `k = plafond(0,05 × T)`, après tri du pire vers le meilleur. À rendement égal, le mois le plus ancien vient d'abord. L'expected shortfall est la moyenne des rangs 1 à k. Ce ne sont pas des rendements annualisés et ce n'est pas une loi normale.

L'écart de suivi est l'écart-type d'échantillon de `rendement du livre − rendement du fonds en CHF`, multiplié par la racine de 12. Le ratio d'information est la moyenne de cet écart divisée par son écart-type, multipliée par la racine de 12.

Le choc de marché remplace le dernier rendement par le paramètre −20 %. Le choc de récession remplace les six derniers mois par −3 %. Le choc de volatilité conserve la moyenne et multiplie les écarts à la moyenne par 1,5. Le choc de taux ajoute 2 points au SARON annuel, reconvertit le mois, et ne change pas le rendement du portefeuille. Ces chocs sont illustratifs.

## Feuilles

Lisez-moi donne les sources, la date de génération, la tolérance et le périmètre. Suivi, Performance, Risque et Chocs portent les titres des pages HTML et des visuels Power BI correspondants. Les séries sont les mêmes. Les formules de ces graphiques sont sur Series. Parametres tient la tolérance, les plafonds et les paramètres de choc. Recalcul, la vue d'ensemble et les trois tableaux croisés lisent des tables chargées par Power Query. Actualiser tout recharge ces tables. SourcesCroisees ne relit pas les fichiers : elle référence les requêtes Rendements, Benchmark, Secteurs, Contributions et StressPublie. Recalcul porte les formules. Reconciliation compare Python et Excel. valeur_power_bi est la valeur attendue du pipeline. statut_power_bi reste en attente tant qu'une valeur lue dans Desktop n'est pas écrite dans export_power_bi. Vue_ensemble porte la fiche en INDEX/MATCH et la même fiche en XLOOKUP, plus un Top 10 en FILTER et SORTBY. Indicateurs, Correlation, Stress et Qualite présentent le détail. Croise_secteurs, Croise_contributions et Croise_stress sont trois tableaux croisés sur le cache SourcesCroisees, avec les segments strategy et periode. Controles vérifie que les poids somment à 1 et que les contributions sectorielles reconstruisent le rendement du mois. La même feuille compare le nombre de lignes et la somme des rendements entre les tables lues par les formules et les lignes de rendement de SourcesCroisees. Le résultat est OK ou ERREUR. Une ligne compte si son poids dépasse la tolérance, ce qui est le seuil du pipeline. L'équipondéré n'est pas soumis à la bande de 25 à 40 lignes. Un mois optimisé hors bande est affiché en ERREUR et ne fait pas échouer la commande : ce n'est pas un écart de formule.

## Power BI

La plupart des mesures DAX utilisent `SELECTEDVALUE` ou `MAX` sur la cellule publiée : elles ne refont pas le calcul. `Rendement chaîné calculé` et `Drawdown maximal calculé` recalculent en DAX, avec la définition du pipeline, uniquement pour la réconciliation. Elles ne sont pas posées sur une page et ne lisent ni `maximum_drawdown` ni `cumulative_wealth`. La page Performance calcule aussi le multiple contre le SARON, le multiple contre le fonds et le rendement glissant sur 12 mois, à partir des rendements mensuels. Le fonds y est une ligne : son rendement est le sien, son écart contre lui-même est nul. Les pages d'allocation, de suivi et de chocs ne proposent pas le fonds dans le filtre. Le graphique du temps des chocs est l'écart de richesse. Il n'y a pas de superposition des cinq chemins. Une valeur collée depuis un visuel doit rejoindre la colonne Python, à l'arrondi d'affichage près. Si l'écart vient seulement de cet arrondi, la cause est écrite et la ligne est close. La tolérance reste celle écrite avant la comparaison.

## Résultat de cette génération

Tous les indicateurs publiés par le pipeline coïncident avec le recalcul Excel à l'intérieur de la tolérance. Aucun écart n'a été inventé pour les faire coïncider.

Lignes laissées « non publié » : 1. Le ratio d'information du fonds n'est pas défini : le fonds est la référence et son écart de suivi est nul. La cause est écrite et la clôture est close.

Lignes Power BI en attente d'export : 0. Lignes Power BI passées OK par la formule : 101. Lignes Power BI en EXCEPTION : 0. Une valeur attendue ne peut pas rendre cette colonne OK : seule une valeur lue dans Power BI Desktop le peut.

## Export Power BI

`export_power_bi` contient 101 valeurs lues dans Power BI Desktop le 2026-11-17 08:53:56 UTC, sur le moteur localhost:57662 (Analysis Services 17.0.93.23, ADOMD.NET). Les données du modèle avaient été actualisées dans Desktop entre 2026-11-17T08:53:46 → 2026-11-17T08:53:48 UTC.

Méthode. Pendant qu'un rapport est ouvert, Desktop fait tourner un moteur Analysis Services local. `python -m src.reporting.power_bi_export` lit son port dans le dossier de travail de Desktop, s'y connecte avec ADOMD.NET et envoie une requête DAX `EVALUATE` par ligne : la mesure du modèle, filtrée sur le livre, le choc ou le dernier mois. La requête de chaque ligne est écrite dans `power_bi_export.csv`. Le rapport n'est ni modifié ni enregistré.

Ce que la valeur est. C'est la valeur que le moteur renvoie pour la mesure, avec tous ses chiffres. Un visuel affiche la même valeur arrondie par son format. Ce n'est pas une lecture d'écran.

Ce que l'export prouve. Pour le rendement chaîné et le drawdown maximal, la mesure recalcule l'indicateur en DAX à partir des rendements mensuels : un statut OK est alors un troisième calcul, après Python et Excel. Pour les autres lignes, la mesure est un `SELECTEDVALUE` ou un `MAX` de la colonne publiée : Power BI relit le chiffre du pipeline, et un statut OK prouve que le modèle a chargé le bon fichier, la bonne colonne et le bon filtre, pas un calcul indépendant.

Durée de validité. Le pipeline recopie ce fichier à chaque génération. Si les données changent après l'export, la formule compare l'ancien export aux nouvelles valeurs et la ligne passe en EXCEPTION : l'actualisation de Desktop et un nouvel export rétablissent la ligne. Tolerance reste la valeur écrite avant la comparaison.

Sans export automatique, la saisie reste manuelle : ouvrir le projet dans Desktop, Actualiser, puis copier la valeur d'une mesure dans `export_power_bi`, sur la ligne du même indicateur et du même livre. `valeur_power_bi` reste la valeur attendue du pipeline. Tolerance reste la valeur écrite avant la comparaison.

## Dix questions

1. Pourquoi le recalcul est-il indépendant ? Recalcul ne lit que les rendements mensuels, le SARON et les paramètres. Il ne lit pas Metriques, PerformancePubliee, RisquePublie ni StressPublie. La réconciliation compare ensuite les deux résultats. Si Excel lisait le chiffre de Python, l'écart serait nul par construction.
2. Comment la tolérance a-t-elle été fixée ? Elle est égale à l'agreement du pipeline, 1e-8, la même constante pour les contributions, le risque et les chocs. Elle est écrite dans Parametres avant la comparaison. Elle n'est pas ajustée pour faire coïncider une ligne.
3. Pourquoi l'écart-type est-il celui de l'échantillon ? Le diviseur est T − 1, `STDEV.S` dans Excel et `std(ddof=1)` dans Python. Les mois de la fenêtre servent à estimer une dispersion, ils ne sont pas traités comme la population entière. `STDEV.P` n'est pas utilisé.
4. Comment le TWR est-il calculé ? Le rendement chaîné est le produit des (1 + r) mensuels, moins un. Chaque r est déjà le rendement du livre de fin de mois à fin de mois, poids du mois compris. En l'absence de flux externe, ce produit est le rendement pondéré par le temps. Il n'y a pas de fichier de conservation, donc pas de flux à retirer, et ce n'est pas un rendement de Dietz.
5. Comment la VaR historique fonctionne-t-elle ? Les rendements mensuels sont triés du pire au meilleur, puis par mois croissant. k est le plafond de 5 % de T. La VaR est le rendement du rang k. L'expected shortfall est la moyenne des rangs 1 à k. Pas de loi normale, pas d'annualisation.
6. Que ne prouve pas la réconciliation ? Elle prouve que les formules Excel retrouvent les chiffres publiés par le pipeline, à la tolérance près. Elle ne prouve pas que les titres ont été détenus, que les cours sont ceux d'un conservateur, ni que des frais ont été prélevés. Il n'y a pas de données de conservation. Elle ne prouve pas non plus que les définitions sont les bonnes : Excel applique celles du pipeline, écrites par le même auteur, et la plupart des lignes Power BI relisent simplement la cellule publiée. Elle trouve une erreur de calcul, pas une erreur de méthode.
7. Comment un écart serait-il traité ? Le statut passe à EXCEPTION et la clôture reste ouverte tant que la cause n'est pas écrite. La commande du pipeline s'arrête. On documente la cause. On ne modifie pas la tolérance et on n'ajuste pas une formule pour forcer OK. Un écart qui vient d'une définition différente est un résultat, pas une erreur à masquer.
8. Pourquoi le ratio d'information du fonds n'est-il pas publié ? L'écart de suivi du fonds contre lui-même est nul. Diviser la moyenne de cet écart par un écart-type nul n'est pas défini. Le Sharpe, le Sortino, la VaR et l'expected shortfall du fonds sont publiés, avec les mêmes définitions que pour les livres.
9. Pourquoi la colonne Power BI n'est-elle jamais OK avant un export Desktop ? `valeur_power_bi` est la valeur attendue, lue dans expected_values.csv. Ce n'est pas une copie d'écran de Desktop. Le statut reste « en attente d'export Power BI » tant que `export_power_bi` est vide. Une valeur lue dans Desktop, écrite par `src.reporting.power_bi_export` ou collée à la main, fait basculer la formule vers OK ou EXCEPTION.
10. Pourquoi les trois tableaux croisés partagent-ils un cache ? Excel ne relie un segment à plusieurs tableaux que s'ils ont le même cache. SourcesCroisees référence les requêtes Rendements, Benchmark, Secteurs, Contributions et StressPublie. Elle ne relit pas les CSV. Recalcul lit les tables Rendements et Benchmark, chargées par ces mêmes requêtes. La vue d'ensemble lit Secteurs, Zones, Devises et Positions, chargées par leurs requêtes. Le contrôle de la feuille Contrôles compare le nombre de lignes et la somme des rendements. Il est OK seulement si les deux côtés coïncident, à la tolérance près. Les segments Livre et Période pilotent les trois tableaux. Le journal de qualité vient d'un classeur, pas d'un CSV, donc il n'a pas de requête Power Query.
