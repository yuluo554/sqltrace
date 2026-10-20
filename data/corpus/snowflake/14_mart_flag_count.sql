INSERT INTO mart_flag_count (pay_dt, cnt)
SELECT pay_dt, COUNT(*) AS cnt
FROM stage_pay_flag
GROUP BY pay_dt;
