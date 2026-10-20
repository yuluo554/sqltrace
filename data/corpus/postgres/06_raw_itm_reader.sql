-- 只读不改写（census: read_only 表）
SELECT sku, qty FROM raw_itm WHERE qty > 1;
