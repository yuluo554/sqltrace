-- 聚合 + HAVING control
INSERT INTO mart_usr_daily (dt, usr, tot_amt)
SELECT dt, usr, SUM(amt) AS tot_amt
FROM stage_evt_clean
GROUP BY dt, usr
HAVING COUNT(*) >= 1;
