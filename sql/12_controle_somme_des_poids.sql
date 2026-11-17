-- Contrôle : les poids de chaque livre et de chaque mois font un.
-- La requête ne renvoie une ligne que si ce n'est pas le cas.
-- Un résultat vide est un contrôle réussi.

SELECT
    strategy,
    month,
    ROUND(SUM(weight), 12) AS somme_des_poids
FROM book_weights
GROUP BY strategy, month
HAVING ABS(SUM(weight) - 1.0) > 1e-8
ORDER BY strategy, month;
