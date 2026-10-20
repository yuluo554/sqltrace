INSERT INTO mart_amt_x_sum (dt, tot_x)
SELECT dt, SUM(amt_x) AS tot_x
FROM stage_evt_x
GROUP BY dt;
