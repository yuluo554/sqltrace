# HANDOFF-M3 — 降级策略交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M4.md 继续完成任务`（下一棒是 M4）。

## 一、当前进度 + 证据

- **M0 + M1 + M2 + M3 完成**（本提交）：M3 = 降级策略引擎 + reason code 封闭枚举 + 零静默机械门。
- 证据：
  - 常驻测试 **59 passed**（`PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q`；M3 新增 23 个）。
  - 精确率/召回未回退：value **100%（110/110）**、召回 **98.1%（152/155）**。
  - `sqltrace lineage data/corpus`：**232 条边**（value 110 / control 116 / unknown 6）+ **8 条诊断**，零静默门 **passed=true**、违规 0、未登记码 0。
  - 双跑 `--json` 字节级一致（100,399 字节，sha256 相同）。
  - **变异验证**：把 `_flag_no_source` 改成 no-op（模拟静默丢弃）→ CLI 退出码 `4`；还原 → `0`。门能红也能绿，不是空判据。
  - 布局门全绿（HANDOFF-M3 本份；WRAPUP-M3 已入库）。

## 二、当前事实·状态不变量（下一棒动手前必读）

1. M0 的 7 条 + M1 的 K1–K8 + M2 的 K9 **全部继续有效**；M3 新增 K10–K12（见 §四）。
2. **reason code 枚举现在是 13 个**（M2 时 9 个）：新增 `dialect_defaulted` / `no_source_columns` / `wildcard_expanded` / `schema_overridden` / `unsupported_stored_procedure`。`data/README.md` §4.2 与 `constants.py` **两处同步**（K2）；`test_constants_match_data_readme` 逐行比对 §4.2 表，改了文档不同步代码会红。
3. **§4.2 新增"挂载点"列**：`unknown_wildcard` / `unknown_type` 是**边+诊断**（`EDGE_AND_DIAG_CODES`），其余只落诊断。`diagnose_missing_edges` 反向断言这条口径；新增边缘码时必须同时登记挂载点常量。
4. **零静默门是硬门**（§4.2 规则 4）：`corpus.write_ids` 由 `build_edges` 填写（`INSERT` / `CREATE TABLE|VIEW ... AS` / `MERGE`），写语句"无边且无**语句级**诊断"即 FAIL → CLI 退出码 `4`。文件级码（`dialect_defaulted` / `schema_overridden`）**不算**语句留痕（`FILE_LEVEL_CODES`）。**M4/M5 复用同一份边集时必须复用这个门**。
5. **MERGE 由 fallback 直接产边**（`fallback.resolve_merge`）：`_target_of` 只认 `Insert`/`Create`，`build_edges` 里有 `isinstance(root, exp.Merge)` 显式路由。改 `_target_of` 时别破坏这条路由。
6. **`MERGE` 的目标侧自引用不入上游**：`ON t.id = s.id` 只产 `s` 侧 control 边，不产 `mart.X ← mart.X` self-loop。这是 D7 的具体落点，有测试锁死。
7. **`WITH ... INSERT/CREATE` 的 CTE 挂在 DML 根节点**（不在 SELECT 上）：`_root_cte_scope(root)` 负责把它带进初始 scope。M2 此处有缺陷（CTE 名当基表产假边），M3 已修并有专测。
8. **CLI JSON 的 `diagnostics[]` 现在是装载期 + 内核期合并**（此前只输出装载期；摘要行却两边都算，自相矛盾）。字段增 `approximate`；新增 `zero_silence` 块（`passed` / `silent_statements` / `unregistered_reason_codes`）。M5 冻结 golden 期望时以该形态为准。
9. **`--dialect` 现在真生效**（此前 CLI 收参数但 loader 忽略）；指定后不触发 `dialect_defaulted`。
10. `data/README.md` §4.2 之外，`plan/01` §二模块③ 策略表仍是题面级描述（含 `wildcard_expanded` 一行）；实现以 §4.2 为准，两者不冲突。

## 三、下一棒待办（M4 写入者普查）

1. **`census(edges, statements) -> CensusReport`**：`writers` / `readers` / `orphan`（有读无写）/ `multi_writer`（≥2 写入者写同一张表）/ `write_only`（只写不读）五节（plan/03 §M4、plan/01 模块④）。
2. **写入者口径**：写入者 = 有**写目标表**的语句（`build_edges` 已收集 `corpus.write_ids`，可直接复用；比重新解析 AST 更省且口径一致）。写入者条目需 `文件路径 + 语句序号 + 方言`（`Statement` 已有三字段）。
3. **读者口径**：`edges[].source_table` 即"读到的表"；注意 `unknown` 边 `source_table` 为 `None`，**不得**计入 readers（否则孤儿表判定失真）。
4. **排序**（§4.6）：表名升序；表内写入者按 `(file, statement_index)` 升序。输出 Markdown 可贴 PR + `--json`。
5. **零误报**：单写入者表不得出现在 `multi_writer`；`data/corpus/51_*` 与 `52_*` 同写 `stage_hot`（应命中多写），`50_*` 写 `raw_orphan`（无人读 → `write_only`）。
6. **golden g4 绿**（`data/golden/g4/corpus/`：植入多写 + 孤儿表）；期望冻结留 M5。
7. **零静默门复用**：`census` 也要跑 `zero_silence_violations`（同 M3 口径），失败退 `4`。
8. **`docs/census-sample.md` 必须是真实输出**（M4 DoD 明确要求，plan/00 §五）。

## 四、既定口径清单（K 编号，动了会打挂测试）

- **K1**：三类边判定顺序（AST 确定不了→unknown 先于 value/control）——§4.1。
- **K2**：reason code 封闭枚举 **13 个**——§4.2；新增必须改该节 + constants.py。
- **K3**：退出码 0/1/2/3/4——§4.4；argparse 用法错误保持 SystemExit(2)。M3 起 `4` 真实可达（零静默门/枚举守卫）。
- **K4**：排序键 (target_table, target_column, kind, source_table, source_column, expr) 码点升序——§4.6；`output.dumps_json` 单一出口。
- **K5**：不调用 sqlglot `lineage()`/`qualify()` 作判定路径（D5）；sqlglot 钉 `>=30.20,<31`。
- **K6**：零网络——src/ 不得 import requests/urllib/http.client/socket 等（常驻测试）。
- **K7**：语料与标注同提交；golden 期望冻结后只增不改（§三#6#7）。
- **K8**：表名裸名、`raw_/stage_/mart_` 假名；标注 target/source = `table.column`；路径相对语料根、分隔符 `/`。
- **K9（M2）**：窗口值参数穿透 CTE 后仍保留窗口口径；内层 control 穿透外层不得升为 value。
- **K10（M3 新增）**：**零静默门口径**——写语句（`write_ids`）必须"有边或有**语句级**诊断"；文件级码不计入；CLI 失败退 `4`。
- **K11（M3 新增）**：**边↔诊断对账**——unknown 边必有同 `(file, statement_index, reason_code)` 诊断；`EDGE_AND_DIAG_CODES` 的诊断必有对应边。
- **K12（M3 新增）**：**MERGE 口径**——`UPDATE SET`/`INSERT ... VALUES` 按左值列名与列清单位置映射产 value 边；`ON`/`WHEN` 条件产 control + `join_path`；目标侧自引用**不入上游**；DELETE 分支只留 `skipped_merge_branch`。

## 五、本机环境坑（实测日期 2026-10-20/21）

- M0/M1/M2 交接单 §五 全部继续有效（`py`/`-X utf8`/`PYTHONDONTWRITEBYTECODE=1`、pip 代理污染需 `NO_PROXY="*"`、临时脚本用完即删）。
- **测试一律走 3.12 通道**（sqlglot 30.23.0 + pytest 8.4.2）；3.8 只做语法兼容检查（`ast.parse` 全绿，未跑 sqlglot）。
- `sqlglot` 对 `EXEC('...')` 往 stderr 打 `Unsupported Execute syntax` —— 是警告不是异常；节点类型 `Execute`（`ParseWarning` 走 logging，不进我们的诊断）。测试输出里看到这行属正常。
- **`MERGE` 的 `when.args` 键名**：条件在 `condition`（不是 `cond`）；INSERT 分支的 `then.this` 是 `Tuple`（列清单），`then.expression` 是 `Tuple`（值）；无列清单时 `this` 为 `None`。
- **`CREATE PROCEDURE`** 三类形态：T-SQL → `Create(kind=PROCEDURE, this=StoredProcedure, expression=Block)`；Postgres → `expression=Heredoc`；Snowflake → `expression=Literal`。都**不带** `--dialect` 也能解析，但体内不展开（D11）。
- `pathlib.Path.write_text` 在 3.8 无 `newline` 参数；写文件统一 `open(..., newline="\n")`。

## 六、M3 DoD checklist

- [x] `grep -c unknown` 与未解析计数一致（JSON 三段对账，6 条 unknown 边逐条有同键诊断）
- [x] 每个降级构造都有对应 reason code（13 档表驱动覆盖，缺一即红）
- [x] 零静默（`write_ids` 42 条、违规 0；阳性对照必红；变异验证：关掉 `no_source_columns` → 退出码 4）
- [x] golden g2 绿（未知 schema `SELECT *` 零猜测，目标列占位 `*`）
- [x] golden g3 绿（`INSERT (c2, c1) SELECT a, b` 位置映射；按名对齐的反例被显式否定）
- [x] reason code 封闭枚举 + 文档/代码两处同步（逐行比对 §4.2 表）
- [x] `dialect_defaulted` 专用码接线（M2 遗留缺口关闭）；`--dialect` 覆盖生效
- [x] plan/00·05·README 状态回写一致（M3 ✅ 三副本同步；布局门绿）
- [ ] CI 步骤接线（无远端，M6 首推时在 workflow 里加布局门步骤；措辞"本地等价校验（未接远端，CI 待首推验证）"）

## 七、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q   # 全量测试（M3 起 59 个）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; main(['lineage','data/corpus'])"   # 血缘摘要 + 零静默门
py -3.12 -X utf8 -c "import sys,io,contextlib,json; sys.path.insert(0,'src'); from sqltrace.cli import main; b=io.StringIO(); c=contextlib.redirect_stdout(b); c.__enter__(); main(['lineage','data/corpus','--json']); c.__exit__(None,None,None); d=json.loads(b.getvalue()); print(len(d['edges']), d['zero_silence'])"   # JSON 边数 + 门
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; main(['lineage','data/golden/g2/corpus','--json'])"   # golden g2 手工核
git -c core.quotepath=false status --short       # 中文路径不转义
NO_PROXY="*" py -3.12 -m pip install -e .        # 可安装验证（官方源；用完卸载）
```
