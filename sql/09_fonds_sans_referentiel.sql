-- Positions du fonds qui n'ont pas de ligne dans le référentiel des titres,
-- sur la clé ticker et place de cotation. Une position hors référentiel
-- n'a ni symbole de cours ni devise de cotation : elle ne peut pas être suivie.
-- Les lignes de trésorerie et de change du fonds sont attendues ici.

SELECT
    holdings.ticker,
    holdings.name,
    holdings.asset_class,
    holdings.exchange,
    holdings.currency,
    ROUND(holdings.weight, 4) AS poids_du_fonds
FROM benchmark_holdings AS holdings
LEFT JOIN securities_master AS master
    ON master.ticker = holdings.ticker
    AND master.exchange = holdings.exchange
WHERE master.ticker IS NULL
ORDER BY holdings.weight DESC;
