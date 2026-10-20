-- 聚合：参数 value；GROUP BY control
INSERT INTO mart_sales_daily (dt, gmv_amt)
SELECT s.dt, SUM(s.amt) AS gmv_amt
FROM stage_orders_clean s
GROUP BY s.dt;
