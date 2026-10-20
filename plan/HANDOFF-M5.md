# HANDOFF-M5 — diff 闸门与输出交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M6.md 继续完成任务`（下一棒是 M6 发布，本份之后写 M6 交接单）。

## 一、当前进度 + 证据

- **M0 + M1 + M2 + M3 + M4 + M5 完成**（本提交）：M5 = diff 闸门（git/双目录两模式）+ impact 穿透 + 五条 golden 期望侧冻结 + `docs/diff-sample.json`。
- 证据：
  - 常驻测试 **107 passed**（`PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q`；M5 新增 32 个）。
  - `sqltrace golden data/golden`：**5/5 通过**，退出码 `0`。
  - `sqltrace diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus`：`REMOVED 1 / ADDED 2 / CHANGED 1`，退出码 `1`。
  - `sqltrace diff data/corpus --base HEAD`：`0/0/0`，退出码 `0`；git 模式取到 53 文件 / 59 语句（与目录模式一致）。
  - `sqltrace impact raw_cust.nm data/corpus`：`max_depth = 2`、`final_consumers = [mart_sales_daily_rd.nm, mart_union_all.nm]`、`intermediate_tables = [stage_cust_enrich, stage_union_src_a, stage_union_src_b]`。
  - 双跑确定性：`diff --json` 1,521 字节、`golden --json` 2,340 字节，两次运行逐字节相同；`docs/diff-sample.json` 与实时输出**逐字节一致**（常驻测试断言）。
  - **变异验证 5 组**（门能红也能绿，不是空判据）：
    1. `CHANGED` 判据改语句集合 → 7 红；
    2. 退出码优先级反转 → 5 红；
    3. `impact` 闭包截到 1 层 → 3 红；
    4. 目录模式 sha 改回原始字节 → 2 红；
    5. 去掉 golden 期望 JSON 顶层键白名单 → 1 红。
  - 3.8 语法兼容：`ast.parse(feature_version=(3,8))` 对 `src/` + `tests/` 全绿（未跑 sqlglot）。
  - 布局门全绿（HANDOFF-M5 本份 + WRAPUP-M5 已入库）。

## 二、当前事实·状态不变量（下一棒动手前必读）

1. M0 的 7 条 + M1 的 K1–K8 + M2 的 K9 + M3 的 K10–K12 + M4 的 K13–K14 **全部继续有效**；M5 新增 K15–K17（见 §四）。
2. **diff/impact/golden 口径现在有单点**：`data/README.md` §4.9（规则 1–9）+ §4.4（退出码）。`plan/03 §M5` 是设计回写，实现以 §4.9 为准。**不要**在报表文案里另立第二套判定。
3. **退出码 `1`/`2` 是 diff 专属**。`lineage`/`census`/`impact` 成功恒 `0`；`golden` 期望不符或门红一律 `4`；所有命令使用错误 `3`；内部一致性失败 `4`。**别把 `1`/`2` 泄漏到别的子命令**（会打破 CI 的"非零即失败"直觉）。
4. **diff 的分组键是 `(target_table, target_column, kind)`**。`kind` 变了 = 旧键 REMOVED + 新键 ADDED，**不是** CHANGED。CHANGED 只表示"同键的来源集合变了"。
5. **两模式必须同内核**：目录模式 `load_corpus`、git 模式 `load_corpus_from_texts`，二者共用 `loader._assemble_corpus`。**任何新口径（如 schema 覆盖、方言判定）都必须加在那个函数里**，否则两模式会分叉。
6. **sha 一律取解码文本的 sha**（`_sha256_text`）。目录模式 `read_text` 走通用换行（CRLF→LF）；哈希原始字节会让 CRLF 文件在两模式下 sha 不同。
7. **`rev-parse --show-prefix` 带尾斜杠**，拼 pathspec 前必须 `rstrip("/")`；`git ls-tree` 用 `-z` 取原始路径（防非 ASCII 转义）。
8. **git 模式是只读的**：只用 `ls-tree` / `show` / `rev-parse`，**不得** checkout/stash/写工作区（`test_git_mode_does_not_touch_worktree` 锁死）。
9. **impact 的 `reading_statements` 取 `corpus.reads`**（K13，不从边集反推）；`downstream_consumers` 取边图正向闭包。两者不重复计数。
10. **`unknown` 边无来源表 → 不入 impact 图**，diff 里来源记字面 `null`（不编造表名）。自环（自更新）不入闭包。
11. **golden 期望 JSON 由口径人工推导**（`plan/04 §二`），只含 `target`/`source`/`kind`（+ census/diff/impact 的集合与计数）。顶层键只认 `lineage`/`census`/`impact`/`diff` 且至少一个——拼错必红。**不得**把实现风味字段（`expr`/`statement_id`）写进期望值，那就是循环论证。
12. **JSON 输出必须 `sys.stdout.write(dumps_json(...))`**，不能用 `print`（会多一个换行，破坏 §4.6 单 `\n`）。`docs/*.json` 与实时输出逐字节比对是常驻测试。
13. **`docs/diff-sample.json` 由 `diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus --json` 生成**，测试逐字节比对。改了 `diff_payload` 或 g5 语料 → 样例必须重生成，否则 `test_diff_sample_doc_is_real_output_and_deterministic` 红。
14. **g5 的 `corpus_v2/` 是 M5 新增的"当前"版本**（`corpus/` 仍是 M1 冻结的 v1）。`expected.json` 同时断言 diff 三态与 impact 穿透两层——**两者共用同一份语料**，改任一侧要同时复核另一侧。

## 三、下一棒待办（M6 发布）

1. **脱敏扫描**：`git ls-files` 全量过一遍——无真实表名/公司名/人名/邮箱/内网路径；`data/labels/*.json` 与语料注释也要看（注释不进标注但会进仓库）。
2. **干净环境验证**：真下载（`pip download` 或从 sdist 装）+ 解包 + 新 venv + **逐条敲 README 的每条命令**（`lineage`/`census`/`diff`/`impact`/`golden` 五条都要真跑，不能只看 `--help`）。
3. **`plan/RELEASE-M6.md` 两栏**（**tag 之前**入库）：§一 tag 前事实（构建命令、产物清单、SHA256、覆盖对账表三态行 ≥3）/ §二 tag 后追加（真实 tag 名、Release URL、上传产物哈希）。**tag 树内不自指写哈希**。
4. **构建产物**：`release/*.whl` + `release/SHA256SUMS`（`python -m build`，本机 3.12 通道）。
5. **annotated tag** → **`gh release create`** 附产物 → tag 后只允许**非交付面**提交（POST_TAG_SCOPE + DELIVERABLE_UNCHANGED 两判据）。
6. **CI 步骤接线**：首推时在 workflow 里加布局门 + 全量 pytest + 五条 golden；措辞固定"本地等价校验（未接远端，CI 待首推验证）"，回填真实 run id 后才可写"CI 绿"。
7. **五条 golden 必须在 CI 里跑**（`sqltrace golden data/golden`）；`diff` 的 git 模式在 CI 的浅克隆下可能取不到 `HEAD~1`——**要么 fetch-depth: 0，要么把 g5 的 diff 断言走目录模式**（当前 g5 就是目录模式，CI 不需要 git 历史）。

## 四、既定口径清单（K 编号，动了会打挂测试）

- **K1**：三类边判定顺序（AST 确定不了→unknown 先于 value/control）——§4.1。
- **K2**：reason code 封闭枚举 **14 个**——§4.2；新增必须改该节 + constants.py。
- **K3**：退出码 0/1/2/3/4——§4.4；argparse 用法错误保持 SystemExit(2)。
- **K4**：边排序键 `(target_table, target_column, kind, source_table, source_column, expr)` 码点升序——§4.6；`output.dumps_json` 单一出口。
- **K5**：不调用 sqlglot `lineage()`/`qualify()` 作判定路径（D5）；sqlglot 钉 `>=30.20,<31`。
- **K6**：零网络——src/ 不得 import requests/urllib/http.client/socket 等（常驻测试）。
- **K7**：语料与标注同提交；golden 期望冻结后只增不改（§三#6#7）。
- **K8**：表名裸名、`raw_/stage_/mart_` 假名；标注 target/source = `table.column`；路径相对语料根、分隔符 `/`。
- **K9（M2）**：窗口值参数穿透 CTE 后仍保留窗口口径；内层 control 穿透外层不得升为 value。
- **K10（M3）**：**零静默门口径**——写语句（`write_ids`）必须"有边或有**语句级**诊断"；文件级码不计入；CLI 失败退 `4`。
- **K11（M3）**：**边↔诊断对账**——unknown 边必有同 `(file, statement_index, reason_code)` 诊断；`EDGE_AND_DIAG_CODES` 的诊断必有对应边。
- **K12（M3）**：**MERGE 口径**——`UPDATE SET`/`INSERT ... VALUES` 按左值列名与列清单位置映射产 value 边；`ON`/`WHEN` 条件产 control + `join_path`；目标侧自引用**不入上游**；DELETE 分支只留 `skipped_merge_branch`。
- **K13（M4）**：**普查数据来源**——写者取 `corpus.write_targets`、读者取 `corpus.reads`，**不得从边集反推**；读者剔除 CTE 名与自身写目标；纯 DDL 两边都不算；`multi_writer` 判据严格 `len(writers[t]) >= 2`；五节排序 §4.6。
- **K14（M4）**：**语料注释不是真值**——断言以实测为准。`raw_orphan` 写 1 读 1（`50_*` 写、`51_*` 读），既不 orphan 也不 write_only；`stage_hot` 是真实语料的 write_only 植入项；g4 golden 是"多写 + 孤儿"的权威植入项。
- **K15（M5 新增）**：**diff 分组键与三态**——键 `(target_table, target_column, kind)`；同键来源集合变化 = `CHANGED`；`kind` 变化 = 旧键 `REMOVED` + 新键 `ADDED`；来源记 `table.column`，unknown 边记 `null`；三节按 `(表, 列, kind)` 升序，来源列表 `null` 在前。改这条会打挂 `test_diff_*` 五族用例 + g5。
- **K16（M5 新增）**：**两模式同内核 + 只读 git**——目录模式与 git 模式共用 `loader._assemble_corpus`；git 只用 `ls-tree -z` / `show <ref>:<path>` / `rev-parse`，不切工作区；`--show-prefix` 必须 `rstrip("/")`；文件 sha 一律取**解码文本**的 sha（`_sha256_text`）。改这条会打挂 `test_git_and_dir_*` / `test_load_corpus_from_texts_*` / `test_sha_normalized_*` / `test_git_mode_does_not_touch_worktree`。
- **K17（M5 新增）**：**impact 与 golden 口径**——`impact` 的上游=反向闭包、下游=正向闭包（上限 §4.7）、`final_consumers`=无更下游、`intermediate_tables`=既非目标也非汇点的表、`reading_statements` 取 `corpus.reads`（K13）；目标表不在血缘图退 `3`。`golden` 期望 JSON 顶层键白名单 + 非空、每份语料跑同一份 `gate_check`、不符或门红退 `4`、无 `expected.json` 退 `3`。JSON 一律 `sys.stdout.write(dumps_json(...))`（单换行）。

## 五、本机环境坑（实测日期 2026-10-21）

- M0–M4 交接单 §五 全部继续有效（`py`/`-X utf8`/`PYTHONDONTWRITEBYTECODE=1`、pip 代理污染需 `NO_PROXY="*"`、临时脚本用完即删）。
- **测试一律走 3.12 通道**（sqlglot 30.23.0 + pytest 8.4.2）；3.8 只做语法兼容检查。
- `sqlglot` 对 `EXEC('...')` 往 stderr 打 `Unsupported Execute syntax` —— 警告不是异常；`impact`/`census` 输出里看到这行属正常。
- **`git rev-parse --show-prefix` 带尾斜杠**（`data/corpus/`）——拼 pathspec 前必须剥掉，否则 `git show` 退 128。
- **`git ls-tree -r -z --name-only <ref> -- .`** 是取"该目录下全部文件"的稳妥写法（相对当前 `-C` 目录）；用 `-z` 防非 ASCII 路径被转义。
- **`print(dumps_json(...))` 会多一个换行**（`dumps_json` 已带 `\n`）——一律 `sys.stdout.write`。
- **Bash heredoc 写 Python 时 `\n` 会被吃掉/转义错**：本棒两次踩坑。写临时脚本一律用 Write 工具落盘，不用 heredoc。
- **`python` 是商店占位符**：跑脚本必须 `py -3.12`（heredoc 里写 `python - <<EOF` 会静默不执行）。
- Windows 上 `Path.write_text` 在 3.8 无 `newline` 参数；写样例文件统一 `open(..., newline="\n", encoding="utf-8")`。
- `git -c core.quotepath=false status --short` 看中文路径不转义。

## 六、M5 DoD checklist

- [x] `diff --base <git-ref|dir>` 两模式，喂同一内核（`test_git_and_dir_base_produce_identical_edges`）
- [x] 边级 diff 三态（ADDED/REMOVED/CHANGED），`kind` 变化 = REMOVED+ADDED
- [x] 退出码 §4.4（`0`/`1`/`2`/`3`/`4`；`1`/`2` 仅 diff 语义）
- [x] `impact` 穿透两层（g5：`intermediate_tables == [mid1, mid2]`；真实语料 `raw_cust.nm` 穿 2 层）
- [x] `impact` 的 `reading_statements` 复用 `corpus.reads`（K13，不从边集反推）
- [x] golden g5 绿（三态齐 + impact 穿透）
- [x] 五条 golden 一条命令全绿（`sqltrace golden data/golden` → 5/5，退出码 `0`）
- [x] `docs/diff-sample.json` 是真实输出（常驻测试逐字节比对）
- [x] 双跑确定性（`diff --json` 1,521 字节 / `golden --json` 2,340 字节，两次运行相同）
- [x] 门复用（diff 基线与当前各一次、golden 每份语料一次；两组阳性对照）
- [x] 口径单点 `data/README.md` §4.9 + `plan/03 §M5` 实现回写 + `plan/04` 期望侧形态
- [x] plan/00·05·README·06 状态回写一致（M5 ✅ 三副本同步；布局门绿）
- [ ] CI 步骤接线（无远端，M6 首推时在 workflow 里加布局门 + pytest + `golden` 步骤；措辞"本地等价校验（未接远端，CI 待首推验证）"）

## 七、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q   # 全量测试（M5 起 107 个）

# 五条 golden（M5 招牌命令；全绿退 0，任一红退 4）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; sys.exit(main(['golden','data/golden']))"

# diff：目录模式（g5 基线→当前）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; sys.exit(main(['diff','data/golden/g5/corpus_v2','--base','data/golden/g5/corpus','--md']))"

# diff：git 模式（只读，不切工作区）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; sys.exit(main(['diff','data/corpus','--base','HEAD','--json']))"

# impact：穿透层数 + 最终消费者
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; main(['impact','raw_cust.nm','data/corpus'])" 2>/dev/null

# 重生成样例（改 diff 输出后必做）
py -3.12 -X utf8 -c "import sys,io,contextlib; sys.path.insert(0,'src'); from sqltrace.cli import main; b=io.StringIO(); c=contextlib.redirect_stdout(b); c.__enter__(); main(['diff','data/golden/g5/corpus_v2','--base','data/golden/g5/corpus','--json']); c.__exit__(None,None,None); open('docs/diff-sample.json','w',encoding='utf-8',newline='\n').write(b.getvalue())"

py -3.8 -X utf8 -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,8)) for d in ('src/sqltrace','tests') for p in pathlib.Path(d).glob('*.py')]; print('3.8 ok')"
git -c core.quotepath=false status --short       # 中文路径不转义
```
