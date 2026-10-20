-- 窗口：PARTITION BY usr → control；amt → value
CREATE TABLE mart_usr_daily_rank AS
SELECT dt, usr, tot_amt,
       RANK() OVER (PARTITION BY usr ORDER BY tot_amt DESC) AS rk
FROM mart_usr_daily;
