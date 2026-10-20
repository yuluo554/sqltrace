INSERT INTO mart_rn_pick (id, rn)
SELECT id, rn FROM mart_pay_rn WHERE rn <= 2;
