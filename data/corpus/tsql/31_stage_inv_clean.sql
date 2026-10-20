-- 方括号引用 + INSERT 列清单位置映射
INSERT INTO stage_inv_clean (inv_id, loc, qty, dt)
SELECT i.inv_id, i.loc, i.qty, i.dt
FROM [raw_inv] i;
