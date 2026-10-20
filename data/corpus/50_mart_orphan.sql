-- 孤儿表：只写 raw_orphan，无人读（census: write_only/orphan）
CREATE TABLE raw_orphan AS
SELECT 1 AS id, 'x' AS nm;
