# Processus manuel, processus automatisé

Lu avec le [guide](GUIDE_UTILISATEUR.md). Cette page décrit l'enchaînement que `python -m src.pipeline.refresh` remplace, et ce que chaque étape gagne. Elle ne contient pas de chiffre de résultat.

## Avant : une production mensuelle à la main

| Étape | Geste | Ce qui pouvait se passer |
|---|---|---|
| Télécharger | Ouvrir le site iShares, Yahoo Finance et la BNS, enregistrer les fichiers | Fichier du mois précédent gardé par erreur, colonne renommée par la source |
| Nettoyer | Supprimer les lignes vides, corriger un format de date, retrouver la devise d'un titre | Correction faite une fois, oubliée le mois suivant, et sans trace |
| Rapprocher | Comparer un total à celui du mois précédent, à l'œil | Un écart petit passe ; un écart grand est corrigé dans la cellule |
| Calculer | Formules Excel recopiées d'un classeur à l'autre | Plage décalée d'une ligne, annualisation sur le mauvais nombre de périodes |
| Rédiger | Recopier les chiffres dans un document, écrire le commentaire | Chiffre de l'ancien mois dans le nouveau rapport, commentaire qui ne correspond plus |
| Diffuser | Envoyer le fichier | Aucun moyen de prouver, après coup, d'où vient un chiffre |

## Après : une commande, et un arrêt à chaque contrôle

```text
Registre des sources
  → acquisition des jeux dus, selon la fréquence écrite
  → chargement en base
  → six contrôles qualité, résultat enregistré avec sa cause
  → conversion en CHF, univers éligible
  → livres, suivi, performance, risque, chocs
  → annexe Excel : recalcul indépendant, réconciliation Python / Excel / Power BI
  → rapport exécutif, rapport de CLIENT001, rapport du gérant, présentation, commentaires, cas d'investigation
  → relecture de chaque nombre dans son fichier
  → dictionnaire de données et requêtes SQL exécutées, dont les contrôles sur les tables des livres
```

`python -m src.pipeline.full_refresh` enchaîne le tout sur la machine de travail : les données, puis Power BI Desktop ouvert, actualisé, exporté et refermé sans enregistrer, puis l'annexe et les rapports. Une tâche mensuelle reconstruit les données seules (`scripts/monthly_refresh.cmd`).

La commande s'arrête quand :

- un jeu dû ne peut pas être acquis et qu'un jeu en dépend ;
- les poids ne somment pas à un, ou les contributions ne reconstituent pas le rendement ;
- un indicateur de la phase 7, 8 ou 9 ne rejoint pas la phase 5 ;
- une ligne de réconciliation reste ouverte sans cause ;
- un nombre d'un texte ne se retrouve dans aucun fichier ;
- une requête SQL publiée ne s'exécute pas, ou un contrôle SQL renvoie une ligne.

`--skip-office` laisse de côté l'annexe Excel et les rapports, qui demandent Excel sous Windows. Le reste de la chaîne tourne sans Office. La commande le dit dans le journal : l'annexe et les rapports décrivent alors le dernier passage complet. L'empreinte des entrées brutes est écrite à chaque passage dans `data/input_manifest.json`.

Elle ne s'arrête pas pour un avertissement qualité : l'écart est enregistré, visible sur la page Data Quality et dans les cas d'investigation, et le texte le signale.

## Ce que chaque gain veut dire ici

| Gain | Où il se voit |
|---|---|
| Constance | Le même fichier produit le même rapport. Les règles sont dans `src/config.py`, pas dans une cellule. |
| Répétabilité | Le calendrier du registre décide ce qui est réacquis. Le reste est relu depuis le disque. |
| Contrôle | Chaque étape a un contrôle qui lève une erreur. La tolérance est écrite avant la comparaison et n'est jamais ajustée après. |
| Traçabilité | `logs/technical.log` pour l'exécution, `controle_des_nombres.csv` pour chaque nombre d'un texte, le fichier des exclusions pour chaque séance écartée. |
| Transparence | Excel refait le calcul à partir des rendements, sans lire le résultat de Python. Un lecteur peut suivre chaque formule. |
| Maintenabilité | Une règle du mandat change dans un seul fichier. Les textes qui la citent se réécrivent. |

## Ce que l'automatisation ne remplace pas

- La relecture des livrables avant diffusion. Chaque texte porte la mention qui le rappelle.
- La décision sur un écart. Le pipeline l'écrit, il ne le tranche pas.
- La lecture des rapports de société pour le registre ODD. Elle reste manuelle, et sa source est nommée ligne par ligne.
- La mise en forme du rapport Power BI. La commande complète actualise le modèle et exporte les mesures, mais n'enregistre jamais le rapport.

## Le même raisonnement dans Excel

Les gestes du processus automatisé ont leur équivalent dans l'annexe Excel, parce que c'est ainsi qu'une équipe de reporting les pratique :

| Dans le pipeline | Dans l'annexe |
|---|---|
| Lecture des fichiers publiés | Requêtes Power Query, tables chargées |
| Jointures | `XLOOKUP`, `INDEX` / `MATCH` |
| Agrégations par livre et par mois | `SUMIFS`, `COUNTIFS`, tableaux croisés avec segments |
| Contrôle de somme et de reconstruction | Feuille Contrôles, résultat OK ou ERREUR |
| Réconciliation | Feuille Réconciliation, écart contre tolérance, statut, cause, clôture |

L'annexe n'est pas une copie de Python. Elle recalcule, et c'est ce qui donne un sens à la comparaison.
