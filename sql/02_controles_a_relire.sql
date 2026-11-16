-- Contrôles du dernier passage qui ne sont ni PASS ni NOT_APPLICABLE.
-- NOT_APPLICABLE signifie que le contrôle ne s'applique pas à cette table.
-- WARNING et FAIL sont les lignes à relire. La cause est dans la colonne notes.

SELECT
    control.dataset_id,
    control.table_name,
    control.control_name,
    control.status,
    control.issues,
    control.notes
FROM quality_control_result AS control
INNER JOIN (
    SELECT run_id
    FROM quality_run
    ORDER BY execution_date DESC
    LIMIT 1
) AS last_run
    ON last_run.run_id = control.run_id
WHERE control.status NOT IN ('PASS', 'NOT_APPLICABLE')
ORDER BY control.dataset_id, control.control_name;
