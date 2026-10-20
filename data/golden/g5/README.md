# g5

lineage diff：基线（`corpus/` v1）→ 当前（`corpus_v2/` v2）三态齐（REMOVED / ADDED / CHANGED）并穿透两层中间表

输入语料：`corpus/v1.sql`（M1 冻结）+ `corpus_v2/v2.sql`（M5 新增，"当前"版本）。期望：`expected.json`（M5 冻结，按 `data/README.md` §4.9 人工推导）。

v2 的改动（三态各有）：

- **REMOVED**：`leaf` 整表消失 → `leaf.nm` 的边移除（破坏性，退出码 `1`）。
- **CHANGED**：`mid1.nm` 换源 `raw_src.nm` → `raw_src2.nm`。
- **ADDED**：`mid1.cd`、`mid2.cd` 两条新边。

**穿透两层**：`impact raw_src.nm` 的下游是 `mid1.nm`（1 层）→ `mid2.nm`（2 层）→ `leaf.nm`（3 层），
中间表 `mid1`/`mid2` 两跳，最终消费者 `leaf.nm`（`intermediate_tables == [mid1, mid2]` 是机械判据）。

验收：`sqltrace golden data/golden`；或手工
`sqltrace diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus --md`。
