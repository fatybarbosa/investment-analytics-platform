# Cas d'investigation sur les données

**Généré automatiquement, à relire avant diffusion.**

Produit par le pipeline le 2026-11-17 08:56 UTC. Chaque nombre est relu dans un fichier du pipeline. Les cas décrivent ce que le pipeline a fait d'un défaut : il l'écarte et l'écrit, il ne le corrige pas en silence.

## Titres sans série de change

- Symptôme. Le contrôle de cohérence des devises signale 11 titres du référentiel sur 120 sans série de change, gravité MEDIUM. Par devise : ILS 1, INR 6, SAR 1, TWD 3.
- Cause. Le cube de change de la Banque nationale suisse ne publie pas ces devises. Un cours en devise sans taux contre le franc ne peut pas être converti.
- Décision. Les titres restent hors des livres, dont 3 au statut Eligible qui seraient entrés sinon. Le pipeline n'invente pas de taux. La tolérance du contrôle n'a pas été modifiée pour faire passer la table.
- Trace. Le fichier des exclusions de cours garde chaque séance écartée avec sa raison, le fichier d'appartenance garde le titre avec la cause, et le contrôle reste en avertissement à chaque passage. Aucun taux croisé n'a été construit à partir d'une autre devise.

## Clôtures manquantes et cours hors fourchette

- Symptôme. Sur 650 954 séances de cours, 1 744 ont une clôture hors de la fourchette plus haut / plus bas ou négative, et 1 153 n'ont pas de clôture.
- Cause. Les séances viennent d'une source gratuite, avec des barres incomplètes ou incohérentes sur certaines places. Une clôture hors fourchette ne peut pas être vraie en même temps que son plus haut et son plus bas.
- Décision. Chaque séance fautive est retirée de la série en CHF et inscrite dans le fichier des exclusions avec sa raison : 1 744 séances hors fourchette et 1 153 sans clôture, les mêmes nombres que le contrôle. Aucune valeur n'est interpolée. Le même fichier garde 50 890 séances sans série de change et 6 652 séances sans taux de fin de mois.
- Cours ajusté. Le rendement des livres est un rendement total : il utilise le cours ajusté des dividendes, converti en CHF comme le cours de clôture. 964 séances ont un cours ajusté nul ou négatif et 0 n'en ont pas : elles sont écartées, sans valeur reconstituée. Toutes sont antérieures à la fenêtre de mesure et ne touchent aucun livre.
- Trace. Le contrôle reste en avertissement sur la table des cours. Le fichier des exclusions est relu par cette note à chaque génération.

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
