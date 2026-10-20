CREATE TABLE stage_inv_backup AS
SELECT inv_id, loc, qty, dt FROM stage_inv_clean WHERE dt IS NOT NULL;
