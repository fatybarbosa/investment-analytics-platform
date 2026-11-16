-- Jeux que le registre autorise à charger.
-- load_enabled et active viennent du registre des sources, pas d'un filtre ajouté dans la requête.

SELECT
    dataset_id,
    source_id,
    dataset_name,
    table_name,
    load_enabled,
    quality_enabled,
    active,
    last_acquisition_status,
    records_loaded
FROM dataset_registry
ORDER BY dataset_id;
