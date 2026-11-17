-- Poids de chaque secteur dans chaque livre, au dernier mois publié.
-- Le secteur vient de la feuille de positions du fonds, jointe sur le symbole.
-- La part du livre est calculée avec une fonction de fenêtre : elle doit faire un par livre.
-- Le poids est celui avec lequel le mois commence, dérive comprise.

WITH last_month AS (
    SELECT MAX(month) AS month
    FROM book_weights
)
SELECT
    weights.strategy,
    holdings.sector,
    COUNT(*) AS lignes,
    ROUND(SUM(weights.weight), 4) AS poids,
    ROUND(
        SUM(weights.weight) * 1.0 / SUM(SUM(weights.weight)) OVER (PARTITION BY weights.strategy),
        4
    ) AS part_du_livre
FROM book_weights AS weights
INNER JOIN last_month
    ON last_month.month = weights.month
INNER JOIN book_holdings AS holdings
    ON holdings.yahoo_symbol = weights.yahoo_symbol
    AND holdings.strategy = weights.strategy
WHERE weights.weight > 1e-8
GROUP BY weights.strategy, holdings.sector
ORDER BY weights.strategy, poids DESC;
