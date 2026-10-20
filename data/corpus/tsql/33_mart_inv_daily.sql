INSERT INTO mart_inv_daily (dt, tot_qty)
SELECT dt, SUM(qty) AS tot_qty
FROM stage_inv_clean
GROUP BY dt;
