# HANDOFF-M1 — 数据先行交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M2.md 继续完成任务`（下一棒是 M2）。

## 一、当前进度 + 证据

- **M0 + M1 完成**（本提交）：M1 = 语料 + 标注 + golden 输入侧 + 装载器最小闭环。
- 证据：
  - 语料 **53 个 `.sql`**（`find data/corpus -name '*.sql' | wc -l`），目录即方言：postgres/snowflake/bigquery/tsql/duckdb 各 10 个 + 根目录 3 个（多写/孤儿植入，方言默认 postgres 并记 `dialect_defaulted` 诊断 3 条）。
  - 标注 6 份 `data/labels/*.json`（5 方言 + unsorted），**逐边 156 条**（只标 value/control，§三#5）；`test_labels_cover_corpus_and_kinds` 断言标注文件全部存在于语料且 kind 合法。
  - golden **g1–g5 输入侧**：每条 `data/golden/gN/{README.md,corpus/*.sql}`（输入冻结，期望 M5 冻结）。
  - 装载器：`sqltrace lineage data/corpus --json` 输出文件清单/语句/ schema/诊断；`pip install -e .`（py-3.12 官方源）→ `sqltrace --version` = 0.1.0.dev0、lineage rc=0；装后已卸载，工作树无 egg-info 残留。
  - 常驻测试 **21 passed**（`py -X utf8 -m pytest tests -q`，含 M1 新增 12 个：gitignore/方言默认/CTAS+VIEW schema/拓扑/环/语句数上限/语料不变量族）。
  - 布局门全绿（LAYOUT.STATUS 3 副本 × 7 里程碑一致；HANDOFF-M1 本份）。
- 本棒**未做**变异验证（M0 已做过门的方法论级变异 8 组；M1 无判据改动，不复做）。

## 二、当前事实·状态不变量（下一棒动手前必读）

1. M0 交接单（`plan/HANDOFF-M0.md`）的 7 条不变量**全部继续有效**（口径真相源、版本两处、布局门耦合、门点名、pip 通道、pytest 通道、K1–K7）。
2. **标注与语料同提交纪律已生效**（§三#6）：改 `data/corpus` 必须同步改 `data/labels`，`tests/test_m1_loader.py` 会红——这是刻意的。
3. loader 的 `Statement.file` 是相对语料根目录的 `/` 分隔路径（§4.6）；表名**不带库前缀**（DDL 与边都用裸表名，如 `raw_cust`）；标注的 target/source 形如 `table.column`。M2 产边必须沿用此口径。
4. 方言默认诊断目前**借用 `PARSE_ERROR` 码承载** `dialect_defaulted` 消息（§4.2 枚举没有该码）；已登记 `plan/06` 缺口，M3 接线时决策（扩枚举需改 data/README §4.2 + constants.py，K2）。
5. loader 语句切分是**分号断句**（注释感知最小实现）；sqlglot 尚未接入（M2）。`_table_refs`/`_writes_target` 是正则近似，M2 的 AST 内核不要复用它们做判定，只可复用 `Corpus/Statement` 结构与拓扑序。
6. `data/golden/gN/corpus/` 是 golden 专用输入（g2 的 `raw_unknown`、g3 的列清单错位等故意构造），**不在** `data/corpus` 里，M5 实现 golden runner 时直接指向这些目录。
7. `.gitignore` 追加了 `data/golden/*/work/`（golden runner 临时目录约定，M5 可用）。

## 三、下一棒待办（M2 血缘内核）

1. sqlglot 30.23.0 接入：**只在 3.8 通道验证可装**（`NO_PROXY="*" py -3.8 -m pip install -i 官方源 sqlglot`；3.8 未装过 30.x，装不上就改用 3.12 跑测试并在 HANDOFF 登记）。
2. `core.build_edges(corpus) -> (edges, diags)`：自研 scope walker，CTE/子查询别名绑定、逐输出列回溯；按 §4.1 判定顺序（AST 定不了 → unknown 先于 value/control）。
3. 窗口强制口径：`SUM(x) OVER (PARTITION BY k ORDER BY t) AS w` → `(w,value,x)+(w,control,k)+(w,control,t)`；**禁止** `(w,value,k)`（K1/§4.1）。
4. 聚合/CASE/JOIN 构造分型（plan/03 §M2 关键构造清单）；元数据字段 expr/aggregation/window/join_path 落到 `Edge`。
5. 在标注语料上首跑精确率/召回自评（§4.3）：value 精确率 100% 门槛、召回 ≥85%、未召回必须落 unknown——先把 g1 窗口用例跑绿。
6. 零网络纪律复扫（K6，`test_no_network_imports` 常驻）。

## 四、既定口径清单（K 编号，动了会打挂测试）

- **K1**：三类边判定顺序（AST 确定不了→unknown，先于 value/control）——data/README §4.1。
- **K2**：reason code 封闭枚举 9 个——§4.2；新增必须改该节 + constants.py。
- **K3**：退出码 0/1/2/3/4——§4.4；argparse 用法错误保持 SystemExit(2)。
- **K4**：排序键 (target_table, target_column, kind, source_table, source_column, expr) 码点升序——§4.6；序列化 UTF-8 无 BOM、`\n`、`indent=2`、`ensure_ascii=False`（`output.dumps_json` 单一出口）。
- **K5**：不调用 sqlglot `lineage()`/`qualify()` 作判定路径（D5）；sqlglot 钉 `>=30.20,<31`。
- **K6**：零网络——src/ 不得 import requests/urllib/http.client/socket 等（常驻测试）。
- **K7**：语料与标注同提交；golden 期望冻结后只增不改（§三#6#7）。
- **K8（M1 新增）**：表名一律裸名（无库前缀）、`raw_/stage_/mart_` 前缀假名；标注 target/source = `table.column`；路径输出相对语料根、分隔符 `/`。

## 五、本机环境坑（实测日期 2026-10-20）

- M0 交接单 §五 全部继续有效（`py`/`-X utf8`/`PYTHONDONTWRITEBYTECODE=1`、pip 代理污染、双通道）。
- **Python 3.8 的 `Path.write_text` 没有 `newline` 参数**（3.10+ 才有）——写文件要 UTF-8 无 BOM + `\n` 时用 `open(..., newline="\n")`。
- pytest 只在 3.8 通道确认；sqlglot 30.23.0 只在 3.12 通道确认（M1 未引入 sqlglot，测试在 3.8 全绿）。

## 六、M1 DoD checklist

- [x] 语料文件数落区间（53 ∈ 40–60），5 方言齐
- [x] 每条 golden 有输入与一句话说明（g1–g5 `README.md` + `corpus/`）
- [x] 标注 JSON 覆盖全部 value/control 边（156 条；unknown 不预标）
- [x] `sqltrace` 可遍历语料并输出文件清单（`lineage --json` 装载闭环 + 可安装验证）
- [x] 语料不变量自检（无真实表名/人名/公司名；常驻测试锁死）
- [x] plan/00·05·README 状态回写一致（M0 ✅、M1 ✅ 三副本同步；布局门 LAYOUT.STATUS 绿）
- [ ] CI 步骤接线（无远端，M6 首推时在 workflow 里加布局门步骤；措辞"本地等价校验（未接远端，CI 待首推验证）"）

## 七、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -X utf8 -m pytest tests -q   # 全量测试（M1 起 21 个）
sqltrace lineage data/corpus                     # 装载摘要（文件/语句/schema/诊断计数）
sqltrace lineage data/corpus --json              # 装载 JSON（稳定排序）
find data/corpus -name '*.sql' | wc -l           # 语料计数（DoD 用）
git -c core.quotepath=false status --short       # 中文路径不转义
NO_PROXY="*" py -3.12 -m pip install -e .        # 可安装验证（官方源；用完卸载）
```
