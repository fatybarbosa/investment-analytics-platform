# Cas d'investigation sur les données

**Généré automatiquement, à relire avant diffusion.**

Produit par le pipeline le 2026-11-26 10:56 UTC. Chaque nombre est relu dans un fichier du pipeline. Les cas décrivent ce que le pipeline a fait d'un défaut : il l'écarte et l'écrit, il ne le corrige pas en silence.

## Titres sans série de change

- Symptôme. Le contrôle de cohérence des devises signale 11 titres du référentiel sur 120 sans série de change, gravité MEDIUM. Par devise : ILS 1, INR 6, SAR 1, TWD 3.
- Cause. Le cube de change de la Banque nationale suisse ne publie pas ces devises. Un cours en devise sans taux contre le franc ne peut pas être converti.
- Décision. Les titres restent hors des livres, dont 3 au statut Eligible qui seraient entrés sinon. Le pipeline n'invente pas de taux. La tolérance du contrôle n'a pas été modifiée pour faire passer la table.
- Trace. Le fichier des exclusions de cours garde chaque séance écartée avec sa raison, le fichier d'appartenance garde le titre avec la cause, et le contrôle reste en avertissement à chaque passage. Aucun taux croisé n'a été construit à partir d'une autre devise.

## Clôtures manquantes et cours hors fourchette

- Symptôme. Sur 651 748 séances de cours, 1 748 ont une clôture hors de la fourchette plus haut / plus bas ou négative, et 1 159 ont un champ obligatoire vide.
- Cause. Les séances viennent d'une source gratuite, avec des barres incomplètes ou incohérentes sur certaines places. Une clôture hors fourchette ne peut pas être vraie en même temps que son plus haut et son plus bas.
- Décision. Chaque séance fautive est retirée de la série en CHF et inscrite dans le fichier des exclusions avec sa raison : 1 748 séances hors fourchette et 1 159 sans clôture. Aucune valeur n'est interpolée. Le même fichier garde 50 959 séances sans série de change et 7 821 séances sans taux de fin de mois.
- Trace. Le contrôle reste en avertissement sur la table des cours. Le fichier des exclusions est relu par cette note à chaque génération.

## Dividendes et opérations sur titres

- Symptôme. Le cours ajusté du fournisseur ne reprend pas des dividendes déclarés. Titres éligibles concernés, avec le nombre de dividendes ignorés sur tout l'historique : 9901.HK 4, ENLT.TA 1, LAND.L 101, NRP.JO 38, PSON.L 67. Des dividendes dépassent aussi 10 % du cours précédent : SCA-B.ST 18.
- Cause. L'ajustement du fournisseur n'est pas le même d'une place à l'autre. Pour un titre scindé, le cours passé a été retraité et le dividende ne l'a pas été : les deux ne sont plus sur la même base.
- Versement absent des données, ajouté depuis la publication de la société. LAND.L : 60 pence par ancienne action, avec un regroupement de 16 actions en 15. Le montant est ramené à la base des cours et la source est écrite dans le registre.
- Décision. Le rendement total est reconstruit de la même façon pour tous les titres : le cours de clôture, avec chaque dividende déclaré réinvesti au cours du jour de détachement. Le cours ajusté reste dans le fichier et ne mesure plus aucun rendement. Sort des livres, avec le motif dividend_not_comparable : SCA-B.ST. Une opération sur titres que le cours ne reflète pas est signalée et n'est pas corrigée : FIBRAPL14.MX.
- Trace. Les versements déclarés sont dans data/01_raw/corporate_actions/capital_returns.csv. Chaque anomalie est une ligne de data/02_processed/market/corporate_action_check.csv, avec la séance et le cours de référence. Le contrôle des valeurs aberrantes compte les dividendes au-dessus de la limite.

## Unité du rendement publié du fonds

- Symptôme. La feuille de performance publiée par le fonds donne un rendement mensuel sans indiquer son unité : décimal ou points de pourcentage. Lire la mauvaise unité multiplierait l'écart de suivi par cent.
- Cause. La colonne n'a pas d'étiquette. Le module compare le rendement publié à la variation de la valeur liquidative sur au moins 6 mois sans distribution, à 5e-4 près, dans les deux unités.
- Décision. L'unité retenue est celle qui coïncide avec la valeur liquidative. Si aucune ne coïncide, le module s'arrête. La série acceptée compte 120 mois en USD, convertis en CHF avec le taux de fin de mois de la Banque nationale suisse.
- Trace. Le fichier de rendement du fonds garde, pour chaque mois, le rendement publié, le taux de change du mois et du mois précédent, et le rendement en CHF qui en résulte. L'annexe Excel le reconstruit à partir de ces colonnes.

## Historiques incomplets

- Symptôme. 33 titres du référentiel n'ont pas une clôture de fin de mois en CHF sur chaque mois de la fenêtre, dont 10 au statut Eligible.
- Cause. Introduction en bourse après le début de la fenêtre, séances écartées par le contrôle des cours, ou mois sans taux de change de fin de mois.
- Décision. Un titre sans historique complet n'entre dans aucun livre. Les trois livres partagent une seule liste, pour que leurs rendements soient comparables sur les mêmes mois. Aucun cours n'est reconstitué.
- Trace. Le fichier d'appartenance garde la décision et la cause par titre, avec le nombre de mois disponibles et le nombre requis.
