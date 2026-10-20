CREATE TABLE mart_inv_daily_reader AS
SELECT dt, tot_qty FROM mart_inv_daily WHERE tot_qty > 0;
