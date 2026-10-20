CREATE TABLE stage_evt_join_cfg AS
SELECT e.evt_id, e.usr, c.cfg_val
FROM stage_evt_clean e
LEFT JOIN raw_cfg c ON c.cfg_key = e.ev;
