-- 多写目标之二：同写 stage_hot
INSERT INTO stage_hot (id)
SELECT post_id FROM raw_sns;
