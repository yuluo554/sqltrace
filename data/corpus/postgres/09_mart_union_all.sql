-- 两侧列别名一致（id/nm 对齐）：位置合并仍产出确定边
CREATE TABLE mart_union_all AS
SELECT id, nm FROM stage_union_src_a
UNION ALL
SELECT id, nm FROM stage_union_src_b;
