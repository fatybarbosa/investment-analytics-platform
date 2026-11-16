-- Répartition sectorielle de la feuille de positions du fonds iShares.
-- Ce sont les positions publiées par le fonds, pas les poids des trois livres.
-- Un secteur sert au plafond du mandat. Il ne prouve pas l'éligibilité d'une société.

SELECT
    sector,
    COUNT(*) AS lignes,
    SUM(weight) AS poids
FROM benchmark_holdings
GROUP BY sector
ORDER BY poids DESC;
