-- Troisième calcul de la richesse cumulée : en SQL pur, par une requête récursive,
-- à partir des seuls rendements mensuels. Elle est comparée à la richesse publiée
-- par la phase 6. L'écart doit être nul à la tolérance du pipeline près.

WITH RECURSIVE ordered AS (
    SELECT
        strategy,
        month,
        portfolio_return,
        ROW_NUMBER() OVER (PARTITION BY strategy ORDER BY month) AS n
    FROM book_returns
),
chain AS (
    SELECT strategy, month, n, 1.0 + portfolio_return AS wealth
    FROM ordered
    WHERE n = 1
    UNION ALL
    SELECT ordered.strategy, ordered.month, ordered.n, chain.wealth * (1.0 + ordered.portfolio_return)
    FROM chain
    INNER JOIN ordered
        ON ordered.strategy = chain.strategy
        AND ordered.n = chain.n + 1
)
SELECT
    chain.strategy,
    chain.month,
    ROUND(chain.wealth, 12) AS richesse_sql,
    ROUND(path.cumulative_wealth, 12) AS richesse_publiee,
    ABS(chain.wealth - path.cumulative_wealth) AS ecart
FROM chain
INNER JOIN book_path AS path
    ON path.strategy = chain.strategy
    AND path.month = chain.month
WHERE chain.month = (SELECT MAX(month) FROM book_returns)
ORDER BY chain.strategy;
