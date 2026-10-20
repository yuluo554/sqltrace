# WRAPUP-M3 — 降级策略收尾留档

> M3 非发布里程碑；发布留档在 `plan/RELEASE-M6.md`（tag 前入库）。本份为收尾记录，供布局门 LAYOUT.RELEASE 判据与后续追溯。

## 一、DoD 对账

| DoD 项 | 实现 | 核验 |
| --- | --- | --- |
| `grep -c unknown` 与未解析计数一致 | JSON 文本里 `"kind": "unknown"` 行数 == `edges[kind=unknown]` 条数（6）；逐条在 `diagnostics[]` 找到同 `(file, statement_index, reason_code)` 项；反向无"有诊断无 unknown 边" | `test_cli_grep_unknown_count_matches_unresolved_diagnostics`（三段对账，常驻） |
| 每个降级构造都有对应 reason code | 枚举 13 档，**每档一个可复现触发用例**（表驱动，缺一即红） | `test_every_reason_code_has_a_triggering_case` |
| 零静默 | 写语句必须"有边或有语句级诊断"；实证 `write_ids` 42 条、违规 0 条；阳性对照 `["x.sql#0"]` 必红 | `test_zero_silence_gate_on_corpus` + `test_zero_silence_gate_catches_violation` |
| golden g2 绿（未知 schema `SELECT *` 零猜测） | 只出 `unknown_wildcard`、`approximate=true`、`source=None`、目标列占位 `*`，无任何猜测列名 | `test_golden_g2_unknown_wildcard_never_guesses` |
| golden g3 绿（INSERT 列清单位置映射） | `INSERT (c2, c1) SELECT a, b` → `c2←a`、`c1←b`；反例（按名对齐）显式断言不成立 | `test_golden_g3_insert_column_list_positional_mapping` |
| reason code 封闭枚举 | `constants.REASON_CODES` 与 `data/README.md` §4.2 表**逐行比对**（不是数个数）；运行期守卫 `assert_reason_codes` 兜底退 `4` | `test_constants_match_data_readme` + `assert_reason_codes` |
| 精确率 / 召回未回退 | value 精确率 **100%（110/110）**、召回 **98.1%（152/155）**，与 M2 持平 | `test_value_precision_100` + `test_recall_at_least_85` |
| 双跑字节级一致 | `lineage data/corpus --json` 两次运行输出完全相同（100,399 字节，`sha256` 相同） | 收尾实跑（M5 接常驻双跑门） |

## 二、实现落点

- `src/sqltrace/fallback.py`（M3 主体，从占位骨架变为策略引擎）：
  - `resolve_merge()` — `MERGE` 逐分支解析：`UPDATE SET` → value（按 `t.col = s.col` 左值定位目标列）；`INSERT (c1,c2) VALUES (...)` → 列清单位置映射；`ON`/`WHEN` 条件 → control + `join_path`；目标侧自引用不入上游（无 self-loop 假边）；DELETE / 无列清单 INSERT / 形态不支持 → `skipped_merge_branch`；MERGE 内 INSERT 列数不符 → `arity_mismatch`。
  - `reconcile_unknown_edges()` / `diagnose_missing_edges()` — §4.2 规则 5 双向对账。
  - `zero_silence_violations()` — §4.2 规则 4 机械门（文件级诊断不计入语句留痕）。
  - `assert_reason_codes()` — 封闭枚举守卫。
- `src/sqltrace/core.py`：
  - `_Resolver.add_edge()` 收边（MERGE 与常规路径共用落边口径，去重/排序不变）。
  - `exp.Merge` 路由到 fallback（`_target_of` 只认 Insert/Create）。
  - **修 M2 遗留缺陷**：`WITH c AS (...) INSERT/CREATE ...` 的 CTE 挂在 DML 根节点上，M2 从空 scope 起步 → CTE 名被当基表产**假边**（违反 D7）。新增 `_root_cte_scope()`，三条语句形态（insert / create / 各方言）均验证穿透到 `raw_x`。
  - `recursion_limit` 真实触发两条路径：深度 >16（§4.7）、自引用 CTE（新增 `_in_progress` 集合 + `_truncate` 单次诊断）。
  - `no_source_columns`：写语句全常量、边集为空是**确定结果**而非丢弃。
  - 存储过程 / 函数体：`unsupported_stored_procedure` 留痕（D11 边界，此前静默）。
  - `corpus.write_ids` 收集供零静默门使用。
- `src/sqltrace/loader.py`：`dialect_defaulted` 从"借 `PARSE_ERROR` 承载"改为**专用码**（§4.2）；`--dialect` 覆盖真正生效（此前 CLI 参数被忽略）；外部 `--schema` 覆盖补 `schema_overridden` 留痕（`plan/02` §二 承诺项）。
- `src/sqltrace/cli.py`：JSON 增 `diagnostics[].approximate` 与 `zero_silence` 块；**修 M2 遗留缺陷**——JSON 此前只输出装载期诊断、把内核诊断丢了（摘要行却计入，自相矛盾），现在两处同源；零静默门/枚举守卫失败 → 退出码 `4`（§4.4）。
- `src/sqltrace/constants.py`：枚举 9 → 13，新增 `EDGE_AND_DIAG_CODES` / `FILE_LEVEL_CODES` / `INFO_CODES` 三个挂载点常量。
- `data/README.md` §4.2：枚举表增"挂载点"列 + 规则 4（零静默机械判据）/ 规则 5（边↔诊断对账）；§4.2 标题加"两处同步"提示（K2）。
- 测试：`tests/test_m3_fallback.py` 新增 **23 个**（MERGE 6、recursion 2、dialect 2、no_source/root-CTE 2、存储过程 1、零静默门 3、枚举/对账 3、golden g2/g3 2、CLI 3 —— 含表驱动覆盖）；全量 **59 passed**（3.12 通道）。

## 三、状态副本回写

- `plan/00` §六里程碑表（M3 ✅）、`plan/05` §一状态表（M3 ✅）、`README.md` 状态行（"M3 降级策略完成"）三处一致。
- `plan/00` §一文档索引：`plan/02`–`06` 从 ⬜ M1 改为 ✅ M1（M1 早已完成，索引过期）；`src/sqltrace/` 与 golden 行改 🟡 反映真实进度。
- `plan/00` §三承诺台账 4 行翻 ✅（reason code/零静默、`SELECT *` 零猜测、INSERT 列清单、VIEW 列名对齐）。
- `plan/06` 缺口表：`dialect_defaulted` 一行**关闭**（M3 已接线）；新增存储过程边界行；风险表加"零静默门是空判据"一行 + 缓解。

## 四、遗留（不阻塞 M4）

- 3 条未召回边仍源于 M1 CTAS 派生 schema 近似（函数列推导不出），已落 `unknown` + `unknown_type`，与 M2 结论一致。M4 普查不依赖这些边。
- `MERGE` 的 `UPDATE` 分支若赋值右值含子查询，目前按常规 `_classify` 递归（未在语料中构造）；若 M5 golden 需要，再补专测。
- loader 语句切分仍为分号近似（判定路径已由 AST 接管，仅影响单文件语句计数）。已在 M1/M2 登记，M3 未改动。
- 零静默门当前挂在 `lineage` 子命令上；M4 `census` / M5 `diff` 复跑同一份边集时应复用同一门（写进 M4 待办）。
