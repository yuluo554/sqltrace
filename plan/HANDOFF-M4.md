# HANDOFF-M4 — 写入者普查交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M5.md 继续完成任务`（下一棒是 M5，本份之后写 M5 交接单）。

## 一、当前进度 + 证据

- **M0 + M1 + M2 + M3 + M4 完成**（本提交）：M4 = 写入者普查五节 + Markdown 报表 + 门复用。
- 证据：
  - 常驻测试 **75 passed**（`PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q`；M4 新增 16 个）。
  - `sqltrace census data/corpus`：写者 **41** 张表 / 读者 **30** 张 / 多写 **1**（`stage_hot`）/ orphan **11** / write_only **22**；台账自检 `edges_missing_writer = []`；退出码 `0`。
  - `sqltrace census data/golden/g4/corpus`：`multi_writer = ["stage_hot"]`（`a.sql#1` + `b.sql#0`）、`write_only` 含 `raw_orphan`、`orphan = ["raw_g4"]` —— g4 绿。
  - 双跑确定性：`census --json` 两次运行 16,822 字节、`sha256` 相同；`--md` 两次逐字节一致；`docs/census-sample.md` 与实时输出**逐字节一致**（常驻测试断言）。
  - **变异验证 4 组**（门能红也能绿，不是空判据）：
    1. `multi_writer` 阈值 `>=2` → `>=1` → 4 个测试红（零误报断言失效即红）；
    2. 读者改从边集取（`edges[].source_table`）→ 4 红（纯 `SELECT` 读者丢失、`unknown` 边混入）；
    3. 写者改成"必须有边才算写者" → 3 红（全常量写语句丢失）；
    4. 去掉 CTE 名排除 → 2 红（`agg` 被当成表）。
  - 3.8 语法兼容：`ast.parse(feature_version=(3,8))` 对 `src/` + `tests/` 全绿。
  - 布局门全绿（HANDOFF-M4 本份 + WRAPUP-M4 已入库）。

## 二、当前事实·状态不变量（下一棒动手前必读）

1. M0 的 7 条 + M1 的 K1–K8 + M2 的 K9 + M3 的 K10–K12 **全部继续有效**；M4 新增 K13–K14（见 §四）。
2. **普查口径现在有单点**：`data/README.md` §4.8（五节定义 + 规则 1–8）。`plan/03 §M4` 是设计回写，实现以 §4.8 为准。**不要**在报表文案里另立第二套判定。
3. **写者/读者一律取语句台账，不从边集反推**（§4.8 规则 1–2）。台账在 `core.build_edges` 末尾写入 `corpus.write_targets` / `corpus.reads`；`Corpus` 已加这两个字段。**M5 的 `impact` 若要"下游消费者"也请复用 `corpus.reads`，不要从边集反推**（纯 `SELECT` 读者不在边集里）。
4. **`write_targets` 与 `write_ids` 同源**（同一处 append）：`INSERT` / `CREATE TABLE|VIEW ... AS` / `MERGE INTO t`。纯 DDL（无 `AS SELECT`）两者都不进。
5. **纯 `SELECT` 现在会写 `corpus.reads`**（`isinstance(root, exp.Query)` 分支）。此前 `target is None` 直接 `continue`，什么都不记。
6. **`_read_tables(root, target_table)`** 剔除 CTE 名（`root.find_all(exp.CTE)`）与自身写目标。CTE 名在 AST 里是 `exp.Table`，不排除会给 CTE 虚构一张表。
7. **`census(corpus, edges=None)` 的 `edges` 只用于台账自检**，不参与五节判定；`edges_missing_writer` 非空 = 内部不一致 → 退出码 `4`。
8. **CLI `census` 复用 `lineage` 的同一份门**（`zero_silence_violations` + `assert_reason_codes`），JSON 里同样有 `zero_silence` 块（多一个 `edges_missing_writer` 字段）。**M5 `diff` 必须复用**，不得另写一套。
9. **JSON 键序固定**：`writers` / `readers` 是按表名升序构造的 dict（构造期排序，不靠 `sort_keys`）。`multi_writer` 是 `[{table, writers[]}]` 列表（不是 dict）——g4 断言依赖这个形态。
10. **`docs/census-sample.md` 由 `render_markdown(census(load_corpus('data/corpus'), build_edges(...)))` 生成**，测试逐字节比对。改了 `render_markdown` 或语料 → 样例必须重生成，否则 `test_census_markdown_sample_is_real_output_and_deterministic` 红。
11. **真实语料的一个事实纠正**（见 §四 K14）：`plan/03`/`HANDOFF-M3` 曾称 `50_*` 写 `raw_orphan` 且"无人读 → write_only"，但 `51_*` 的 `SELECT id FROM raw_orphan` **确实读了它**。实测：`raw_orphan` 写者 1（`50_*`）、读者 1（`51_*`），既不 orphan 也不 write_only。真实语料的 `write_only` 植入项是 `stage_hot`；g4 golden 才是"多写 + 孤儿"的权威植入项。

## 三、下一棒待办（M5 diff 闸门与输出）

1. **`diff --base <git-ref|dir>`**：git 模式 `git show <ref>:<path>`（只读，不切工作区），双目录模式直读两目录；**两种模式喂同一个内核**（plan/03 §M5）。
2. **边级 diff**：`ADDED` / `REMOVED` / `CHANGED`（CHANGED = 同 `(target_table, target_column, kind)` 的来源集合变化）；排序 §4.6。
3. **退出码**（§4.4）：`0` 无变化 / `1` 有 `REMOVED` / `2` 仅 `ADDED`/`CHANGED` / `3` 使用错误 / `4` 内部断言失败。**注意**：`1`/`2` 是 diff 专属语义，不要污染 `lineage`/`census`（它们成功恒 `0`）。
4. **`impact <table>.<column>`**：上游来源 + 下游消费者，**穿透两层中间表**；下游消费者请复用 `corpus.reads`（K13），不要从边集反推。
5. **golden g5 绿**（`data/golden/g5/corpus/v1.sql`）；五条 golden 一条命令全绿（`sqltrace golden data/golden`）——期望侧冻结在本棒。
6. **`docs/diff-sample.json` 必须是真实输出**（`plan/00` §五承诺项，M5 DoD）。
7. **确定性**：同输入两次运行 JSON 字节级一致（`dumps_json` 单一出口）；`\n`、UTF-8 无 BOM、无绝对路径、无时间戳。
8. **门复用**：`diff` 与 `golden` 跑同一份边集时复用 `zero_silence_violations` + `assert_reason_codes`；`census` 的 `edges_missing_writer` 自检同理适用。

## 四、既定口径清单（K 编号，动了会打挂测试）

- **K1**：三类边判定顺序（AST 确定不了→unknown 先于 value/control）——§4.1。
- **K2**：reason code 封闭枚举 **13 个**——§4.2；新增必须改该节 + constants.py。
- **K3**：退出码 0/1/2/3/4——§4.4；argparse 用法错误保持 SystemExit(2)。M3 起 `4` 真实可达。
- **K4**：边排序键 `(target_table, target_column, kind, source_table, source_column, expr)` 码点升序——§4.6；`output.dumps_json` 单一出口。
- **K5**：不调用 sqlglot `lineage()`/`qualify()` 作判定路径（D5）；sqlglot 钉 `>=30.20,<31`。
- **K6**：零网络——src/ 不得 import requests/urllib/http.client/socket 等（常驻测试）。
- **K7**：语料与标注同提交；golden 期望冻结后只增不改（§三#6#7）。
- **K8**：表名裸名、`raw_/stage_/mart_` 假名；标注 target/source = `table.column`；路径相对语料根、分隔符 `/`。
- **K9（M2）**：窗口值参数穿透 CTE 后仍保留窗口口径；内层 control 穿透外层不得升为 value。
- **K10（M3）**：**零静默门口径**——写语句（`write_ids`）必须"有边或有**语句级**诊断"；文件级码不计入；CLI 失败退 `4`。
- **K11（M3）**：**边↔诊断对账**——unknown 边必有同 `(file, statement_index, reason_code)` 诊断；`EDGE_AND_DIAG_CODES` 的诊断必有对应边。
- **K12（M3）**：**MERGE 口径**——`UPDATE SET`/`INSERT ... VALUES` 按左值列名与列清单位置映射产 value 边；`ON`/`WHEN` 条件产 control + `join_path`；目标侧自引用**不入上游**；DELETE 分支只留 `skipped_merge_branch`。
- **K13（M4 新增）**：**普查数据来源**——写者取 `corpus.write_targets`、读者取 `corpus.reads`，**不得从边集反推**；读者剔除 CTE 名与自身写目标；纯 DDL 两边都不算；`multi_writer` 判据严格 `len(writers[t]) >= 2`；五节排序 §4.6。改这条会打挂 `tests/test_m4_census.py` 的零误报/CTE/自引用/全常量四族用例。
- **K14（M4 新增）**：**语料注释不是真值**——断言以实测为准。`raw_orphan` 写 1 读 1（`50_*` 写、`51_*` 读），既不 orphan 也不 write_only；`stage_hot` 是真实语料的 write_only 植入项；g4 golden 是"多写 + 孤儿"的权威植入项。`plan/03 §M4`/`HANDOFF-M3 §三#5` 的旧说法已在本棒纠正。

## 五、本机环境坑（实测日期 2026-10-21）

- M0–M3 交接单 §五 全部继续有效（`py`/`-X utf8`/`PYTHONDONTWRITEBYTECODE=1`、pip 代理污染需 `NO_PROXY="*"`、临时脚本用完即删）。
- **测试一律走 3.12 通道**（sqlglot 30.23.0 + pytest 8.4.2）；3.8 只做语法兼容检查（`ast.parse(feature_version=(3,8))` 全绿，未跑 sqlglot）。
- `sqlglot` 对 `EXEC('...')` 往 stderr 打 `Unsupported Execute syntax` —— 警告不是异常；`census` 输出里看到这行属正常（`data/corpus/tsql/36_stage_inv_dyn.sql`）。
- **`exp.Query` 是 `Select`/`Union`/`Insert` 等的共同基类**：`isinstance(root, exp.Query)` 用来识别"纯查询"时，务必放在 `_target_of` 之后（`Insert` 也是 `Query`），否则写语句会被当读者处理。M4 的实现顺序是 `_target_of` → `target is None` → `exp.Query` 分支。
- **`root.find_all(exp.CTE)` 会连嵌套 CTE 一起给**；`cte.alias` 可能为空串（无别名 CTE 不合法，但别假设非空）。
- Windows 上 `Path.write_text` 在 3.8 无 `newline` 参数；写样例文件统一 `open(..., newline="\n", encoding="utf-8")`。
- `git -c core.quotepath=false status --short` 看中文路径不转义。

## 六、M4 DoD checklist

- [x] 五节齐备（writers / readers / orphan / multi_writer / write_only）+ 每条含 `文件 + 语句序号 + 方言`
- [x] 合成语料植入项全命中：真实语料 `stage_hot` 多写（51+52）命中；g4 `stage_hot` 多写 + `raw_orphan` write_only + `raw_g4` orphan 全命中
- [x] 单写入者表零误报（`test_only_single_writer_tables_never_in_multi_writer`；变异把阈值降到 1 → 4 红）
- [x] 排序 §4.6（表名升序；表内 `(file, statement_index)` 升序）——专测 + JSON 键序断言
- [x] golden g4 绿（期望侧冻结留 M5，本棒只验输入侧判定）
- [x] 零静默门复用（同一函数，阳性对照退 `4`）；台账自检 `edges_missing_writer` 阳性对照退 `4`
- [x] `docs/census-sample.md` 是真实输出（常驻测试逐字节比对，双跑一致）
- [x] 双跑确定性（`--json` 16,822 字节 sha256 相同；`--md` 逐字节一致）
- [x] 口径单点 `data/README.md` §4.8 + `plan/03 §M4` 实现回写 + `plan/00` 承诺台账/招牌动词翻 ✅
- [x] plan/00·05·README 状态回写一致（M4 ✅ 三副本同步；布局门绿）
- [ ] CI 步骤接线（无远端，M6 首推时在 workflow 里加布局门步骤；措辞"本地等价校验（未接远端，CI 待首推验证）"）

## 七、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q   # 全量测试（M4 起 75 个）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; main(['census','data/corpus'])"          # 一行摘要
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; main(['census','data/golden/g4/corpus','--md'])"   # g4 报表手工核
py -3.12 -X utf8 -c "import sys,io,contextlib; sys.path.insert(0,'src'); from sqltrace.cli import main; b=io.StringIO(); c=contextlib.redirect_stdout(b); c.__enter__(); main(['census','data/corpus','--md']); c.__exit__(None,None,None); open('docs/census-sample.md','w',encoding='utf-8',newline='\n').write(b.getvalue())"   # 重生成样例（改报表后必做）
py -3.12 -X utf8 -c "import sys,json,io,contextlib; sys.path.insert(0,'src'); from sqltrace.cli import main; b=io.StringIO(); c=contextlib.redirect_stdout(b); c.__enter__(); main(['census','data/corpus','--json']); c.__exit__(None,None,None); d=json.loads(b.getvalue()); print(d['zero_silence'], len(d['census']['multi_writer']))"   # JSON 门 + 多写数
py -3.8 -X utf8 -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,8)) for p in pathlib.Path('src/sqltrace').glob('*.py')]; print('3.8 ok')"
git -c core.quotepath=false status --short       # 中文路径不转义
```
