-- JOIN：ON 为 control；SELECT 列为 value
CREATE TABLE mart_sales_daily_rd AS
SELECT m.dt, m.gmv_amt, c.nm
FROM mart_sales_daily m
JOIN stage_cust_enrich c ON c.id = s.cust_id;
