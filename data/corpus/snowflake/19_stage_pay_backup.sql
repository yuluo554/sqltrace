CREATE TABLE stage_pay_backup AS
SELECT id, ord_id, pay_amt, pay_dt FROM stage_pay WHERE pay_dt IS NOT NULL;
