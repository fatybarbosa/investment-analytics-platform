-- Dépassements de plafond, par livre : aux dates de décision, entre deux décisions
-- (dépassements passifs, par dérive des poids), et contre le plafond de secteur écrit
-- dans le mandat. Aux dates de décision, les plafonds de construction doivent tenir.

SELECT
    strategy,
    SUM(CASE WHEN rebalance_month = 1 AND (issuer_over_cap + sector_over_cap + zone_over_cap + currency_over_cap) > 0 THEN 1 ELSE 0 END)
        AS mois_au_dessus_aux_decisions,
    SUM(CASE WHEN rebalance_month = 0 AND issuer_over_cap = 1 THEN 1 ELSE 0 END)
        AS mois_passifs_emetteur,
    SUM(sector_over_ips_cap) AS mois_au_dessus_du_plafond_de_secteur_ecrit,
    COUNT(*) AS mois,
    ROUND(MAX(largest_issuer_weight), 4) AS plus_gros_poids_d_un_titre
FROM book_limits
GROUP BY strategy
ORDER BY strategy;
