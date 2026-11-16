-- Douze dernières observations du SARON publié par la Banque nationale suisse.
-- La clé de série est celle du cube zimoma. La valeur reste le taux publié, en pour cent.
-- Cette requête ne convertit pas le taux annuel en taux mensuel : c'est le pipeline qui le fait.

SELECT
    date,
    value,
    unit,
    series_key
FROM saron
WHERE series_key = 'EPB@SNB.zimoma{SARON}'
ORDER BY date DESC
LIMIT 12;
