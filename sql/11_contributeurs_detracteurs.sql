-- Les cinq titres qui ont le plus contribué et les cinq qui ont le plus pesé,
-- par livre, sur la fenêtre. La contribution est le poids du mois multiplié par
-- le rendement total en CHF du mois, additionnée sans capitalisation.
-- Deux classements par fonction de fenêtre, un vers le haut et un vers le bas.

WITH last_month AS (
    SELECT MAX(month) AS month
    FROM book_contributions
),
ranked AS (
    SELECT
        contributions.strategy,
        contributions.name,
        contributions.sector,
        contributions.cumulative_contribution,
        ROW_NUMBER() OVER (
            PARTITION BY contributions.strategy
            ORDER BY contributions.cumulative_contribution DESC
        ) AS rang_haut,
        ROW_NUMBER() OVER (
            PARTITION BY contributions.strategy
            ORDER BY contributions.cumulative_contribution ASC
        ) AS rang_bas
    FROM book_contributions AS contributions
    INNER JOIN last_month
        ON last_month.month = contributions.month
)
SELECT
    strategy,
    CASE WHEN rang_haut <= 5 THEN 'contributeur' ELSE 'détracteur' END AS role,
    name,
    sector,
    ROUND(cumulative_contribution, 4) AS contribution_cumulee
FROM ranked
WHERE rang_haut <= 5 OR rang_bas <= 5
ORDER BY strategy, cumulative_contribution DESC;
