-- Séances de cours qu'un contrôle écarte, par symbole : clôture absente,
-- ou clôture hors de la fourchette plus haut / plus bas, ou négative.
-- Les totaux rejoignent les anomalies QC-001 et QC-003 de la table des cours.
-- Le traitement retire ces séances de la série en CHF. Il n'interpole pas.

SELECT
    symbol,
    COUNT(*) AS seances,
    SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) AS sans_cloture,
    SUM(
        CASE
            WHEN close IS NOT NULL AND (close > high OR close < low OR close <= 0) THEN 1
            ELSE 0
        END
    ) AS hors_fourchette
FROM market_prices
GROUP BY symbol
HAVING sans_cloture > 0 OR hors_fourchette > 0
ORDER BY hors_fourchette DESC, sans_cloture DESC, symbol
LIMIT 25;
