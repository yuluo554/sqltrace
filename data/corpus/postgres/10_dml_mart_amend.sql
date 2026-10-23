-- 真实 DML 形态（D11）：UPDATE / DELETE 是数据写语句，必须被零静默门看见。
-- 本期不产列级边，只留 unsupported_write_statement 诊断（DEC-1 乙案边界）；
-- 两条都只碰自身表（不产生新的读者记录），故 §4.8 普查五节计数不因此变化。
UPDATE mart_sales_daily SET amt = amt + 1 WHERE dt = DATE '2026-01-01';
DELETE FROM stage_orders_clean WHERE dt < DATE '2026-01-01';
