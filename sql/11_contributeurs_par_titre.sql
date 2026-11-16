-- Plus fort contributeur et plus fort détracteur de chaque livre.
-- La contribution cumulée est celle publiée : poids du mois multiplié par le
-- rendement du titre en CHF, additionné sur la fenêtre, sans capitalisation.
-- Le mois retenu est le dernier mois du fichier.

WITH last_month AS (
    SELECT MAX(month) AS month
    FROM published_contributions
),
ranked AS (
    SELECT
        contribution.strategy,
        contribution.name,
        contribution.cumulative_contribution,
        ROW_NUMBER() OVER (
            PARTITION BY contribution.strategy
            ORDER BY contribution.cumulative_contribution DESC, contribution.name
        ) AS rank_high,
        ROW_NUMBER() OVER (
            PARTITION BY contribution.strategy
            ORDER BY contribution.cumulative_contribution ASC, contribution.name
        ) AS rank_low
    FROM published_contributions AS contribution
    INNER JOIN last_month
        ON last_month.month = contribution.month
)
SELECT
    strategy,
    name,
    cumulative_contribution,
    CASE
        WHEN rank_high = 1 THEN 'contributeur'
        ELSE 'detracteur'
    END AS role
FROM ranked
WHERE rank_high = 1 OR rank_low = 1
ORDER BY strategy, role;
