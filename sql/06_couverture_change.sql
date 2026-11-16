-- Couverture de change du référentiel : pour chaque devise de cotation,
-- le nombre de titres et la présence d'une série de la Banque nationale suisse.
-- Un titre dont la devise est « absente » ne peut pas être converti en CHF
-- et reste hors des livres. Le franc est la devise de référence : il n'a
-- pas de série contre lui-même.

SELECT
    master.listing_currency,
    COUNT(*) AS titres,
    CASE WHEN series.header_item_2 IS NULL THEN 'absente' ELSE 'publiée' END AS serie_bns
FROM securities_master AS master
LEFT JOIN (
    SELECT DISTINCT header_item_2
    FROM fx_rates
) AS series
    ON series.header_item_2 LIKE '% ' || master.listing_currency || ' %'
GROUP BY master.listing_currency, serie_bns
ORDER BY serie_bns, titres DESC, master.listing_currency;
