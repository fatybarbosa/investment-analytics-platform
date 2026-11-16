-- Feuille de positions du fonds iShares rapprochée du registre ODD,
-- sur la clé ticker et place de cotation. Le poids est celui du fonds,
-- pas celui des trois livres. Une position sans statut n'a pas de ligne
-- dans le registre : c'est une ligne à instruire, pas un titre éligible.

SELECT
    COALESCE(odd.status, 'sans ligne au registre') AS statut_odd,
    COUNT(*) AS positions,
    ROUND(SUM(holdings.weight), 4) AS poids_du_fonds,
    ROUND(SUM(holdings.market_value), 0) AS valeur_de_marche
FROM benchmark_holdings AS holdings
LEFT JOIN odd_assessment AS odd
    ON odd.ticker = holdings.ticker
    AND odd.exchange = holdings.exchange
GROUP BY statut_odd
ORDER BY positions DESC;
