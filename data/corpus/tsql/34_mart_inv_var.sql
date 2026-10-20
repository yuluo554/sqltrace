-- CASE THEN 列 + ELSE 字面量：THEN 侧 value
CREATE TABLE mart_inv_var AS
SELECT inv_id,
       CASE WHEN qty > 1 THEN qty ELSE 0 END AS qty_var
FROM stage_inv_wh;
