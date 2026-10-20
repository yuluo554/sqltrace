# WRAPUP-M4 — 写入者普查收尾留档

> M4 非发布里程碑；发布留档在 `plan/RELEASE-M6.md`（tag 前入库）。本份为收尾记录，供布局门 LAYOUT.RELEASE 判据与后续追溯。

## 一、DoD 对账

| DoD 项 | 实现 | 核验 |
| --- | --- | --- |
| 五节齐备（writers/readers/orphan/multi_writer/write_only） | `census.census(corpus, edges)` → `CensusReport`；条目 = `文件 + 语句序号 + 方言`（§4.8 三字段） | `test_writers_and_readers_from_statement_ledgers`、`test_census_cli_real_corpus_exit0_and_shape` |
| 合成语料植入项全命中 | 真实语料：`51_*`+`52_*` 同写 `stage_hot` → `multi_writer` 命中；`stage_hot` 无读者 → `write_only`。g4：`stage_hot` 多写、`raw_orphan` 只写、`raw_g4` 只读 | `test_real_corpus_planted_items_hit`、`test_golden_g4_multi_writer_and_orphan` |
| 单写入者零误报 | `multi_writer` 判据严格 `len(writers[t]) >= 2` | `test_only_single_writer_tables_never_in_multi_writer`；变异降到 `>=1` → 4 红 |
| 排序 §4.6 | 表名升序；表内 `(file, statement_index)` 升序；dict 构造期排序 | `test_census_sorting_table_asc_writers_by_file_index` |
| golden g4 绿 | `data/golden/g4/corpus` 三件植入项全命中（期望侧冻结留 M5） | `test_golden_g4_multi_writer_and_orphan` |
| 零静默门复用 | `census` 调**同一个** `zero_silence_violations` + `assert_reason_codes`；失败退 `4` | `test_census_cli_zero_silence_gate_is_reused`（阳性对照） |
| `docs/census-sample.md` 真实输出 | 由 `census data/corpus --md` 直接落盘，9,192 字节 | `test_census_markdown_sample_is_real_output_and_deterministic`（与实时输出逐字节比对） |
| 双跑确定性 | `--json` 16,822 字节、两次 `sha256` 相同；`--md` 逐字节一致 | 收尾实跑（M5 接常驻双跑门） |
| 台账自检 | 每条边的 `target_table` 必须登记过写者 | `test_census_cli_ledger_mismatch_gate`（阳性对照退 `4`） |

## 二、实现落点

- `src/sqltrace/census.py`（M4 主体，从占位骨架变为五节普查）：
  - `census(corpus, edges=None)` — 写者取 `corpus.write_targets`、读者取 `corpus.reads`；`orphan = readers − writers`、`write_only = writers − readers`、`multi_writer = len(writers[t]) >= 2`；`edges` 只用于 `edges_missing_writer` 自检。
  - `render_markdown(report, version)` — 摘要 + 五节表格；条目带 `文件#序号（方言）`；无风险分/冲突概率。
  - `census_summary(report)` — CLI 一行摘要。
  - `StatementRef` / `CensusReport` — 冻结/可序列化结构，`to_dict()` 键序固定。
- `src/sqltrace/core.py`：
  - 新增 `_read_tables(root, target_table)`：AST `Table` 节点 → 读表集合，**剔除 CTE 名与自身写目标**。
  - `build_edges` 末尾写 `corpus.write_targets` / `corpus.reads`（与 `write_ids` 同源）；`MERGE` 分支与常规写分支各记一次；`target is None` 的纯查询分支补记读者（此前直接 `continue`，纯 `SELECT` 完全不进台账）。
- `src/sqltrace/model.py`：`Corpus` 增 `write_targets`（`statement_id -> 表`）与 `reads`（`statement_id -> 表元组`）。
- `src/sqltrace/cli.py`：`census` 子命令落地（`--json` / `--md` / 默认摘要）；复用 M3 的零静默门与枚举守卫；`zero_silence` 块增 `edges_missing_writer`；任一门失败退 `4`。
- `data/README.md`：新增 **§4.8 写入者普查口径**（五节定义 + 规则 1–8）——普查口径的单点真相源。
- `plan/03 §M4`：按实现回写（接口签名、台账来源、自检、门复用、样例生成方式）。
- `tests/test_m4_census.py`：新增 **16 个**常驻测试（五节判定 4、纯 SELECT/unknown 边 2、CTE/自引用 2、MERGE 1、多写零误报 2、排序 1、真实语料 1、g4 1、CLI 门 2）。
- `docs/census-sample.md`：真实输出（新建 `docs/`）。

## 三、变异验证（门不是空判据）

| 变异 | 预期 | 实测 |
| --- | --- | --- |
| `multi_writer` 阈值 `>=2` → `>=1` | 零误报断言红 | 4 failed（含 g4 与样例） |
| 读者改为从 `edges[].source_table` 取 | 纯 SELECT 读者丢失、`unknown` 边混入 | 4 failed |
| 写者改为"必须有边" | 全常量写语句丢失 | 3 failed |
| 去掉 CTE 名排除 | `agg` 被当成表 | 2 failed |

四组均"改坏即红、还原即绿"（还原后 75 passed）。

## 四、状态副本回写与事实纠正

- `plan/00` §六里程碑表（M4 ✅）、`plan/05` §一状态表（M4 ✅）、`README.md` 状态行（"M4 写入者普查完成"）三处一致；`plan/00` 顶部"当前状态"同步。
- `plan/00` §一文档索引：`src/sqltrace/` 改"普查已落地"；golden 行补 g4；报告样例行拆开（census ✅ M4 / diff ⬜ M5）。
- `plan/00` §三承诺台账：写入者普查行翻 ✅ M4；§四招牌动词表两行（写入者普查/多写冲突）确认命令与断言基准对应。
- `plan/06` §三风险表新增两行：①普查从边集反推 → 判反（缓解 = 台账 + 两族专测 + 变异）；②语料注释与实测不符。
- **事实纠正（K14）**：`plan/03 §M4` 与 `HANDOFF-M3 §三#5` 曾称 `50_*` 写 `raw_orphan` 且"无人读 → write_only"。实测 `51_*` 的 `SELECT id FROM raw_orphan` 读了它 —— `raw_orphan` 写 1 读 1，两边都不落；真实语料的 `write_only` 植入项是 `stage_hot`；g4 golden 才是"多写 + 孤儿"的权威植入项。断言已按实测写死（`test_real_corpus_planted_items_hit` 的 docstring 记了这条）。

## 五、遗留（不阻塞 M5）

- `data/corpus/50_mart_orphan.sql` 的注释"无人读"与语料事实不符（`51_*` 读它）。语料与标注同提交纪律（K7）：**未改语料**（改了会打挂 `data/labels/unsorted.json` 与既有 golden 口径），只在文档与测试里记事实。M5/M6 若想修注释，需同时确认标注无变化（注释不进标注）。
- `census` 的读者口径是**表级**（语句读过哪些表），不含"读了哪些列"；列级读者属于 `impact`（M5）。
- 写者口径是**语句级**：同一语句重复写同一表（如多分支 `INSERT`）只记 1 个写入者条目（`StatementRef` 以语句为身份）。若 M5 需要"每分支一个写者"，属口径扩展，须先改 §4.8。
- 零静默门当前挂在 `lineage` 与 `census` 上；M5 `diff` / `golden` 复跑同一份边集时**必须复用**（已写进 M5 待办）。
