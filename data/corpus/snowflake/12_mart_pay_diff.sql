-- 两表 join 后相减：表达式两边均 value
CREATE TABLE mart_pay_diff AS
SELECT p.pay_dt, p.pay_amt - r.ref_amt AS diff_amt
FROM stage_pay p
JOIN stage_ref r ON r.ord_id = p.ord_id;
