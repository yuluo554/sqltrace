-- 窗口分型：w 的来源分 value(amt) 与 control(cust_id)
INSERT INTO stage_orders_clean (id, cust_id, amt, w, dt)
SELECT o.id, o.cust_id, o.amt,
       SUM(o.amt) OVER (PARTITION BY o.cust_id ORDER BY o.dt) AS w,
       o.dt
FROM raw_ord o;
