-- 窗口只有 ORDER BY：ORDER BY 键 → control
CREATE TABLE mart_pay_rn AS
SELECT id, ROW_NUMBER() OVER (ORDER BY pay_dt) AS rn
FROM stage_pay;
