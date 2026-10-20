-- 反引号表名为 BigQuery 真实语法；AS 别名 + 谓词 control
INSERT INTO stage_evt_clean (evt_id, usr, ev, amt, dt)
SELECT e.evt_id, e.usr, e.ev, e.amt, e.dt
FROM `raw_evt` e
WHERE e.ev IN ('a', 'b');
