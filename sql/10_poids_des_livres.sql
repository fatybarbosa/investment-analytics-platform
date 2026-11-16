-- Poids des trois livres au dernier mois publié.
-- Ces tables sont chargées depuis les fichiers du pipeline, pas depuis une source externe.
-- Un livre est entièrement investi : la somme des poids du mois vaut 1.

SELECT
    strategy,
    month,
    COUNT(*) AS lignes,
    ROUND(SUM(weight), 8) AS somme_des_poids
FROM published_weights
WHERE month = (SELECT MAX(month) FROM published_weights)
GROUP BY strategy, month
ORDER BY strategy;
