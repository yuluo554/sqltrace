# WRAPUP-M1 — 数据先行收尾留档

> M1 非发布里程碑；发布留档在 `plan/RELEASE-M6.md`（tag 前入库）。本份为收尾记录，供布局门 LAYOUT.RELEASE 判据与后续追溯。

## 一、DoD 对账

| DoD 项 | 实现 | 核验 |
| --- | --- | --- |
| 语料文件数落区间 | 53 个 `.sql`（40–60 区间内） | `find data/corpus -name '*.sql' \| wc -l`；`test_corpus_file_count_in_range` |
| 5 方言覆盖 | postgres/snowflake/bigquery/tsql/duckdb 各 10 + 根目录 3 | `test_corpus_covers_five_dialects` |
| 标注 JSON | 6 份、逐边 156 条（value/control） | `test_labels_cover_corpus_and_kinds` |
| golden 输入侧 | g1–g5 各有 `README.md` + `corpus/` | `data/golden/` 目录 |
| 装载器最小闭环 | `sqltrace lineage data/corpus --json` 文件清单/语句/schema/诊断 | CLI 实跑 + `pip install -e .` 后 rc=0 |
| 语料不变量自检 | 表名前缀/字面量占位/标注覆盖常驻测试 | `tests/test_m1_loader.py` 12 个 |

## 二、状态副本回写

- `plan/00` §六、`plan/05` §一、`README.md` 状态行：M0 ✅、M1 ✅（三处一致，布局门 LAYOUT.STATUS 绿）。
- `plan/06` 缺口新增两条：`dialect_defaulted` 专用码待 M3 决策；sqlglot 3.8 通道安装待 M2 开工前验证。

## 三、遗留（不阻塞 M2）

- loader 的 dialect_defaulted 诊断借用 PARSE_ERROR 码承载（plan/06 缺口列）。
- loader 语句切分为分号近似，M2 AST 内核接管判定路径。
