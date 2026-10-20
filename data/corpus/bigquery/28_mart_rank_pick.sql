INSERT INTO mart_rank_pick (usr, dt, rk)
SELECT usr, dt, rk FROM mart_usr_daily_rank WHERE rk = 1;
