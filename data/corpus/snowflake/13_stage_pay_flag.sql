-- CASE 无 ELSE：THEN 为 value
CREATE TABLE stage_pay_flag AS
SELECT id, ord_id, pay_amt,
       CASE WHEN pay_amt > 0 THEN 'y' END AS flg,
       pay_dt
FROM stage_pay;
