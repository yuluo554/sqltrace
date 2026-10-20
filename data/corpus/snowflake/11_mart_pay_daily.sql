-- QUALIFY 是 snowflake 方言真实语法：QUALIFY 谓词 → control
INSERT INTO mart_pay_daily (pay_dt, pay_amt)
SELECT pay_dt, pay_amt
FROM stage_pay
QUALIFY ROW_NUMBER() OVER (PARTITION BY pay_dt ORDER BY pay_amt) = 1;
