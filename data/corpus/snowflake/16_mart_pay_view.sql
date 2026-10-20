-- CREATE VIEW 无显式列清单：列名取 SELECT 别名
CREATE VIEW mart_pay_view AS
SELECT pay_dt, pay_amt FROM stage_pay;
