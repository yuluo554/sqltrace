-- 动态 SQL：M3 将以 UNSUPPORTED_DYNAMIC_SQL 降级（unknown 不预标）
EXEC('SELECT inv_id FROM raw_inv');
