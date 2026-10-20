-- 多写目标之一（52 同写 stage_hot）
INSERT INTO stage_hot (id)
SELECT id FROM raw_orphan;
