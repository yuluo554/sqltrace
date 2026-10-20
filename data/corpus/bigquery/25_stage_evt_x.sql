-- 算术表达式：两侧列均 value
CREATE TABLE stage_evt_x AS
SELECT evt_id, amt * 2 AS amt_x
FROM stage_evt_clean;
