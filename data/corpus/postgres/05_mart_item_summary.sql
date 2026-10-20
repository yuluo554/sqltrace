INSERT INTO mart_item_summary (dt, sku, tot_qty)
SELECT o.dt, i.sku, SUM(i.qty) AS tot_qty
FROM raw_ord o
JOIN raw_itm i ON i.ord_id = o.id
GROUP BY o.dt, i.sku;
