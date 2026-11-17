-- Contrôle : la rotation brute publiée de chaque rééquilibrage est la somme des
-- valeurs absolues de ses mouvements de poids. Un rééquilibrage sans mouvement
-- a une rotation nulle. La requête ne renvoie une ligne que s'il y a un écart.

SELECT
    turnover.strategy,
    turnover.month,
    ROUND(turnover.gross_turnover, 10) AS rotation_publiee,
    ROUND(COALESCE(SUM(ABS(changes.weight_change)), 0.0), 10) AS somme_des_mouvements
FROM book_turnover AS turnover
LEFT JOIN book_weight_changes AS changes
    ON changes.strategy = turnover.strategy
    AND changes.month = turnover.month
GROUP BY turnover.strategy, turnover.month, turnover.gross_turnover
HAVING ABS(turnover.gross_turnover - COALESCE(SUM(ABS(changes.weight_change)), 0.0)) > 1e-8
ORDER BY turnover.strategy, turnover.month;
