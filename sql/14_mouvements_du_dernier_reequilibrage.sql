-- Les plus grands mouvements de poids du dernier rééquilibrage de chaque livre.
-- Le poids avant est celui que le marché a laissé, dérive comprise. Le poids après
-- est le poids décidé. Ce sont les mouvements d'un livre hypothétique : aucun ordre
-- n'a été passé, ce ne sont pas des transactions.

WITH last_trade AS (
    SELECT strategy, MAX(month) AS month
    FROM book_weight_changes
    GROUP BY strategy
)
SELECT
    changes.strategy,
    changes.month,
    changes.name,
    ROUND(changes.weight_before, 4) AS poids_avant,
    ROUND(changes.weight_after, 4) AS poids_apres,
    ROUND(changes.weight_change, 4) AS variation
FROM book_weight_changes AS changes
INNER JOIN last_trade
    ON last_trade.strategy = changes.strategy
    AND last_trade.month = changes.month
ORDER BY changes.strategy, ABS(changes.weight_change) DESC;
