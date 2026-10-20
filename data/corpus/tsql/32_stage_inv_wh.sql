CREATE TABLE stage_inv_wh AS
SELECT i.inv_id, w.wh, i.qty
FROM stage_inv_clean i
JOIN raw_wh w ON w.loc = i.loc;
