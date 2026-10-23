# WRAPUP-M2 — 血缘内核收尾留档

> M2 非发布里程碑；发布留档在 `plan/RELEASE-M6.md`（tag 前入库）。本份为收尾记录，供布局门 LAYOUT.RELEASE 判据与后续追溯。

## 一、DoD 对账

| DoD 项 | 实现 | 核验 |
| --- | --- | --- |
| `value` 边精确率 100% | 标注语料 155 条边实测：value 精确率 **100%（110/110，零错判）** | `tests/test_m2_core.py::test_value_precision_100`（常驻） |
| 召回 ≥85% | 实测 **98.1%（152/155）**；未命中 3 条落 `unknown` + `unknown_type`（CTAS 派生 schema 推导不出函数列，零猜测） | `test_recall_at_least_85` + `test_missed_labels_not_silent`（常驻） |
| control 边口径 | 语句级谓词（WHERE/JOIN/GROUP BY/HAVING/QUALIFY）扇出到该 SELECT 全部输出列（§4.1 未限定逐目标归属；标注单目标为下界，实现为上界，不触碰 value 精确率门禁） | 标注 155 条全部命中于产出（recall 分母口径） |
| 窗口强制口径 | `SUM(x) OVER (PARTITION BY k ORDER BY t)` → (w,value,x)+(w,control,k)+(w,control,t)；**无** (w,value,k) | `test_window_partition_order_are_control_not_value` |
| golden g1 窗口用例 | g1 的窗口分型即上条口径，M2 内核通过单元等价用例锁定（g1 期望冻结在 M5 跑 runner） | 同上 + `test_case_then_value_when_control` 族 |
| CLI 血缘边 | `sqltrace lineage data/corpus` → 232 条边（value 110 / control 116 / unknown 6）+ 3 条内核诊断；`--json` 稳定排序输出 | CLI 实跑（M2 收尾）。**v0.1.1 注**：D11 加了 2 条真实 DML 语料后边数仍 232，诊断由 3（内核侧）/8（含装载侧）变为 10（+2 `unsupported_write_statement`） |

## 二、实现落点

- `src/sqltrace/core.py`：`build_edges(corpus) -> (edges, diagnostics)`；自研 scope walker（CTE/子查询别名绑定 + 输出列回溯到基表）；**未调用** sqlglot `lineage()`/`qualify()`（K5）。
- 判定顺序严格 §4.1：AST 定不了 → unknown + reason code；再分 value/control。谓词（WHERE/JOIN ON/USING/GROUP BY/HAVING/QUALIFY）→ control；CASE THEN/ELSE → value（分支全常量时谓词列兼记 value，标注口径）。
- `COUNT(*)` 无列参数 → 由 GROUP BY 键承担 control；JOIN ON 记 `join_path`（连接链表名元组）。
- `src/sqltrace/cli.py`：lineage 子命令接 `build_edges`，JSON 输出边（target/source/kind/expr/statement_id/aggregation/window/join_path/reason_code/approximate）。
- 测试：`tests/test_m2_core.py` 15 个常驻（含 §4.3 精确率/召回门槛 2 个）；全量 **36 passed**（3.12 通道）。

## 三、状态副本回写

- `plan/00` §六里程碑表 + §五对标 3 行、`plan/05` §一、`README.md` 状态行：M0 ✅、M1 ✅、**M2 ✅**（三处一致，LAYOUT.STATUS 绿）。
- `plan/06` 缺口关闭一条：sqlglot 3.8 通道不可装（requires-python ≥3.9）→ 定案测试走 3.12 通道。

## 四、遗留（不阻塞 M3）

- 3 条未召回边（`mart_amt_x_sum.dt ← stage_evt_x.dt` 等）源于 M1 CTAS 派生 schema 近似（函数列推导不出），已按纪律落 `unknown` + `unknown_type`，不计静默；M3 降级策略可复用该路径。
- `dialect_defaulted` 专用码仍待 M3 接线（§4.2 扩枚举需同步 constants.py，K2）。
- loader 语句切分仍为分号近似（判定路径已由 AST 接管，切分仅供遍历，影响面：单文件语句计数）。
