# HANDOFF-M2 — 血缘内核交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M3.md 继续完成任务`（下一棒是 M3）。

## 一、当前进度 + 证据

- **M0 + M1 + M2 完成**（本提交）：M2 = sqlglot AST 血缘内核 + CLI 血缘边输出。
- 证据：
  - 标注语料自评：**value 精确率 100%（110/110）、召回 98.1%（152/155）**；未召回 3 条全部落 `unknown` + `unknown_type`（零静默，§4.3）。
  - `sqltrace lineage data/corpus`：232 条边（value 110 / control 116 / unknown 6）+ 3 条内核诊断；`--json` 含边明细且稳定排序。
  - 常驻测试 **36 passed**（`PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q`；M2 新增 15 个：窗口口径/CASE 分型/谓词 control/CTE 穿透/UNION 位置合并/wildcard/arity/动态 SQL/PARSE_ERROR/排序去重 + §4.3 门槛 2 个）。
  - 布局门全绿（HANDOFF-M2 本份；WRAPUP-M2 已入库）。
- 本棒未做变异验证（无判据改动；M0 的方法论级 8 组仍然有效）。

## 二、当前事实·状态不变量（下一棒动手前必读）

1. M0 交接单 7 条不变量 + M1 交接单 8 条（K1–K8）**全部继续有效**。
2. **测试通道定案（plan/06 已登记关闭）**：sqlglot 30.x requires-python ≥3.9，3.8 通道官方源实测装不上（清华镜像同）→ **测试一律走 3.12 通道**（`py -3.12`，sqlglot 30.23.0 + pytest 8.4.2 已装）。pyproject `requires-python = ">=3.8"` **维持不动**（库代码 3.8 兼容，D 通道纪律不改）。注意 3.12 通道已装 sqlglot/pytest 两个包（`pip install -e .` 验证后仍需卸载 egg-info）。
3. **sqlglot 30.x 的参数键名**：`Select` 的 FROM 是 `args["from_"]`（30.x 改名）、CTE 是 `args["with_"]`；`INSERT INTO t (a,b)` 的 `root.this` 是 `Schema`。core.py 已按 30.x 适配并留 `args.get("from")` 兜底——**升级 sqlglot 前先看这两处**。
4. **core.py 内部口径**（M3 接诊断时沿用）：
   - `_Resolver` 诊断用 `_diag(code, message, approximate)`；unknown 边必带 reason（`unknown_wildcard`/`unknown_type`）。
   - 派生 schema 近似（CTAS 函数列推导不出）→ 列回溯失败落 `unknown_type`（这是 3 条未召回边的根因，不是 bug）。
   - `COUNT(*)` 无列参数 → GROUP BY 键承担 control；JOIN ON 右表口径 + `join_path` 元组。
   - CASE 分支全常量 → 谓词列兼记 value（与标注口径一致，`test_case_constant_branch_predicate_also_value` 锁死）。
   - 边去重键 = `(statement_id,) + sort_key() + (reason_code,)`；排序 §4.6。
5. `_register_insert_schema`：INSERT 目标表无 schema 时按列清单/SELECT 输出名补全（类型 unknown）——这让下游 `e.amt` 类限定列可解析；改 loader schema 推导时别破坏它。
6. CLI `lineage --json` 的 `edges` 数组字段名已定（target/source/kind/expr/statement_id/aggregation/window/join_path/reason_code/approximate），M5 冻结 golden 期望时以该形态为准。
7. M1 交接单 #4 的 `dialect_defaulted` 缺口**仍在**（M3 决策）；#6 golden 输入侧说明**继续有效**（g1–g5 在 `data/golden/gN/corpus/`，期望 M5 冻结）。
8. **control 边扇出口径（M2 定案）**：语句级谓词挂到该 SELECT 全部输出列（实现上界；标注只挂单目标）。M5 冻结 golden 期望时按实现口径冻结；若要收窄须先改 data/README §4.1 再动代码（两处同步纪律）。

## 三、下一棒待办（M3 降级策略）

1. 逐 reason code 落地策略档（§4.2 九码全覆盖）：`positional_union`/`arity_mismatch`/`skipped_merge_branch`/`UNSUPPORTED_DYNAMIC_SQL`/`recursion_limit` 已有骨架路径，补 MERGE 分支跳过与 CTE 展开层数的真实触发用例。
2. `dialect_defaulted` 决策：扩 §4.2 枚举（改 data/README + constants.py 两处，K2）或维持 PARSE_ERROR 承载——**先改 data/README 再动代码**。
3. 零静默审计：`grep -c unknown` 与未解析计数一致性检查（M3 DoD）；每条降级边必有 reason code + approximate 标记。
4. golden g2（未知 schema `SELECT *` → 仅 `unknown_wildcard`）/ g3（INSERT 列清单映射 + arity）输入侧已备好，M3 先把它们当验收用例跑通（期望冻结留 M5）。
5. MERGE 语句：sqlglot 解析支持面先探（`exp.Merge`），不支持则 `skipped_merge_branch` 降级，不得静默。

## 四、既定口径清单（K 编号，动了会打挂测试）

- **K1**：三类边判定顺序（AST 确定不了→unknown 先于 value/control）——§4.1。
- **K2**：reason code 封闭枚举 9 个——§4.2；新增必须改该节 + constants.py。
- **K3**：退出码 0/1/2/3/4——§4.4；argparse 用法错误保持 SystemExit(2)。
- **K4**：排序键 (target_table, target_column, kind, source_table, source_column, expr) 码点升序——§4.6；`output.dumps_json` 单一出口。
- **K5**：不调用 sqlglot `lineage()`/`qualify()` 作判定路径（D5）；sqlglot 钉 `>=30.20,<31`。
- **K6**：零网络——src/ 不得 import requests/urllib/http.client/socket 等（常驻测试）。
- **K7**：语料与标注同提交；golden 期望冻结后只增不改（§三#6#7）。
- **K8**：表名裸名、`raw_/stage_/mart_` 假名；标注 target/source = `table.column`；路径相对语料根、分隔符 `/`。
- **K9（M2 新增）**：窗口值参数穿透 CTE 后仍保留窗口口径；内层 control 穿透外层**不得升为 value**（`_sources_from_rel` 分支语义，测试锁死）。

## 五、本机环境坑（实测日期 2026-10-20）

- M0/M1 交接单 §五 全部继续有效（`py`/`-X utf8`/`PYTHONDONTWRITEBYTECODE=1`、pip 代理污染需 `NO_PROXY="*"` 前缀、临时脚本用完即删）。
- **py 3.12 通道已装**：sqlglot 30.23.0、pytest 8.4.2（M2 新装）；3.8 通道仍只有 pytest。
- sqlglot 30.x 解析 `EXEC('...')` 打 "Unsupported Execute syntax" 到 stderr——是警告不是异常，节点类型 `Execute`（M2 已按 Command/Execute 双探测定性 `UNSUPPORTED_DYNAMIC_SQL`）。
- `Path.write_text` 在 3.8 无 `newline` 参数；3.12 有。写文件统一用 `open(..., newline="\n")` 保跨通道一致。

## 六、M2 DoD checklist

- [x] `value` 边精确率 100%（110/110，标注语料）
- [x] 召回 ≥85%（98.1%，152/155；未召回落 unknown + reason code）
- [x] 窗口用例 w<-x(value)+w<-k(control)，无 w<-k 的 value 边（常驻测试）
- [x] golden g1 口径单元等价用例绿（期望 runner 留 M5）
- [x] CLI lineage 输出血缘边（摘要 + JSON）
- [x] plan/00·05·README 状态回写一致（M2 ✅ 三副本同步；布局门绿）
- [ ] CI 步骤接线（无远端，M6 首推时在 workflow 里加布局门步骤；措辞"本地等价校验（未接远端，CI 待首推验证）"）

## 七、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q   # 全量测试（M2 起 36 个，3.12 通道）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; main(['lineage','data/corpus'])"   # 血缘摘要
py -3.12 -X utf8 -c "import sys,io,contextlib,json; sys.path.insert(0,'src'); from sqltrace.cli import main; buf=io.StringIO(); contextlib.redirect_stdout(buf).__enter__(); main(['lineage','data/corpus','--json']); d=json.loads(buf.getvalue()); print(len(d['edges']))"   # JSON 边数
git -c core.quotepath=false status --short       # 中文路径不转义
NO_PROXY="*" py -3.12 -m pip install -e .        # 可安装验证（官方源；用完卸载）
```
