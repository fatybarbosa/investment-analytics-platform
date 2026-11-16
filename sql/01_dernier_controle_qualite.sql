-- Dernier passage du contrôle qualité enregistré dans la base locale.
-- La note et le statut sont ceux du passage, pas une note saisie ici.

SELECT
    run_id,
    execution_date,
    datasets_checked,
    records_checked,
    controls_executed,
    issues_detected,
    global_quality_grade,
    global_status
FROM quality_run
ORDER BY execution_date DESC
LIMIT 1;
