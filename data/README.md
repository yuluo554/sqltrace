# data/README.md — 依据查证、数据源、合成纪律与数值口径

> 基准日：**2026-10-20**（GitHub API 返回 `2026-10-19T17:50Z`，即北京时间 2026-10-20 01:50）。
> 本文档是**口径的唯一真相源**：§四 的枚举与判据被 `plan/01`、代码、报表文案、golden 期望值共同引用。**任何模块不得另立第二套口径。**

## 一、依据查证记录（三态）

| # | 依据 | 编号 / 标识 | 状态 | 渠道 / 备注 |
| --- | --- | --- | --- | --- |
| 1 | sqlglot 规模与许可 | 9,696★ / 1,342 fork，MIT，2026-10-19 | ✅ 已核对 | GitHub API 快照（基准日） |
| 2 | sqlglot `lineage.py` 体积 | 27,773 字节 | ✅ 已核对 | 本地安装包内文件大小 |
| 3 | sqlglot `lineage()` 是库函数、无 CLI 子命令 | — | ✅ 本地实测 | `sqlglot 30.23.0` 本机运行 |
| 4 | sqlglot 窗口分区键与值参数同级 | `SUM(x) OVER (PARTITION BY k) AS w` → `w` 的下游为 `t.x` 与 `t.k`（同层，无 kind） | ✅ 本地实测 | 同上；复现见 §五 |
| 5 | sqlglot `INSERT ... (c1) SELECT` 失败 | `Cannot find column 'c1' in query.` | ✅ 本地实测 | 同上 |
| 6 | sqlglot 无 schema `SELECT *` / 多语句 / `MERGE` / 反向查询 4 项不支持 | `SELECT *` → `Cannot find column`；多语句 → `Cannot build lineage, sql must be SELECT`；`MERGE` 根节点可解析为 `Merge`，但 `lineage()` 报 `Cannot find column`；反向查询库无此 API | ✅ 本地实测 | 同上 |
| 7 | sqlglot 30.x 把 schema 改为必填位置参数 | 实测 `lineage(col, sql)` → `TypeError: missing 1 required positional argument: 'schema'` | ✅ 本地实测 | 见 §二 版本策略 |
| 8 | sqllineage 规模与许可 | 1,680★，MIT，2026-10-16 | ✅ 已核对 | GitHub API 快照 |
| 9 | sqllineage `SELECT *` 穿 CTE 丢列 | issue **#303**（2022-10-12 开至今） | ✅ 已核对 | https://github.com/reata/sqllineage/issues/303 |
| 10 | sqllineage 谓词血缘四年未做 | issue **#276**（open 2022-07-20） | ✅ 已核对 | https://github.com/reata/sqllineage/issues/276 |
| 11 | sqllineage CLI 只暴露 `--sqlalchemy_url` | 无 `--schema ddl.sql` | ✅ 本地实测 | `sqllineage 1.5.9` |
| 12 | FlowScope 规模、许可、能力面 | 105★ / 22 fork，Apache-2.0，2026-09-24；14 方言、DDL schema、dbt/Jinja、72 条 lint、Impact X-Ray、`APPROXIMATE_LINEAGE`/`UNKNOWN_TABLE` | ✅ 已核对 | https://github.com/pondpilot/flowscope |
| 13 | OpenLineage 遇 `SELECT * FROM (SELECT ...)` 跳过列级 | issue **#3809** | ✅ 已核对 | issue 页 |
| 14 | OpenMetadata `CREATE VIEW v(c1,c2)` 静默丢列级边 | issue **#33077** | ✅ 已核对 | issue 页 |
| 15 | SQLMesh `dbt_utils.star` 破坏列级血缘 | issue **#4873** | ✅ 已核对 | issue 页 |
| 16 | dbt 列级血缘规模化失效 | issue **#16483**："76 of 144 models" | ✅ 已核对 | issue 页 |
| 17 | DataHub 表级有边、列级缺失 | issue **#11670** | ✅ 已核对 | issue 页 |
| 18 | 需求侧原话 5 条 | HN 44433883 / 47946547 / 47948027 + whatbreaks README 两段 | ✅ 已核对原文 | 链接见 `plan/01` §1.2 |
| 19 | 开源检索式与计数 | 见 `plan/01` §1.4 表 | ✅ 已核对检索式与 `total_count` | `gh api` 检索，基准日 |
| 20 | 原型四段链路 | 多文件 → 列级边 → 反向影响 → 两版本 diff（v1 三边 → v2 换源 → REMOVED/ADDED） | ✅ 已本地跑通（**单文件原型，非交付物**） | 本机运行 |

### 如实标注：两条**未采信**的说法

| 说法 | 状态 | 处理 |
| --- | --- | --- |
| "文档里的血缘是手画的一直过期" | ⬜ **未找到高信噪比出处** | HN 命中招聘贴/无关线程；**Reddit 403**（基准日两次尝试均被拒）。**题面、README、报表文案一律不得引用该说法**，改用 §一 #18 的 5 条可直连原话。 |
| "离线列级血缘是空白" | ❌ **与实测矛盾** | FlowScope 105★ 已占（#12）。文档只能写"三个切口未被覆盖"，**禁止写"空白/首创/首位"**。 |

### 检索式为 0 的软论据口径

`sql lineage where clause`、`sql table multiple writers conflict`、`sql ownership conflict`、`sql folder git diff lineage`、`lineage regression test golden`、`sql column rename impact`、`upstream downstream column lineage cli`、`unmanaged sql lineage local`、`sql lineage without database`、`warehouse-agnostic sql lineage` 十个检索式的 `total_count` 均为 **0**。

**一律标 ⬜ 软论据**：检索未穷尽、GitHub 检索不覆盖私有仓与站外实现，0 结果**不能反证"世界上没有"**。文档中使用这些论据时必须同时写出检索式与基准日。

## 二、数据源可获取性记录

| 数据源 | 状态 | 获取方式 / 阻断原因 |
| --- | --- | --- |
| SQL 语料 | ✅ **自建，无外部依赖** | `data/corpus/` 下由本项目手写的 `.sql` 文件；**不下载任何公开数据集**，避免许可与隐私问题 |
| 方言语法知识 | ✅ 可获取 | 依据各引擎公开文档的语法形态手写；**不抓取、不内置文档副本** |
| sqlglot 运行时依赖 | ✅ 已获取并实测 | **`sqlglot 30.23.0`**（基准日本机实测版本）。**API 漂移风险**：30.x 把 schema 从可选改为必填位置参数；`lineage()` 行为亦可能随版本变化。策略：`pyproject.toml` 里**钉死版本区间并写下界**，内核不依赖 `lineage()`，只依赖公开 AST 节点类型；升级时必须重跑五条 golden |
| sqllineage | ⬜ 仅作对照，不作依赖 | 只用于 §一 #9–#11 的对照实测；**不进入 runtime 依赖** |
| 真实业务 SQL（任何公司） | ❌ 不可获取且**不得获取** | 隐私红线：不索取、不收集、不提交任何真实业务语料 |
| 公开数据集（TPC-DS / Jaffle Shop 等） | ⬜ 未采用 | 表名/列名会引入第三方许可与"看起来像真实业务"的风险；本题全部语料自建 |

**依赖清单（人读版）**：运行期仅 `sqlglot`（解析）+ Python 标准库。**无数据库驱动、无 HTTP 客户端、无遥测 SDK**。

## 三、合成数据纪律

1. **表名与列名全部自造**：使用 `raw` / `stage` / `mart` 前缀 + 语义化假名（`raw.cust`、`stage.orders_clean`、`mart.sales_daily`）。**不得**使用任何真实公司的表名、库名、schema 名。
2. **不得出现真实人名、手机号、邮箱、身份证号**：语料中即使出现字面量，也只用 `'x'`、`'foo'`、数字 `1`/`2` 这类占位值。
3. **不写真实业务指标口径**：不出现"GMV""转化率"等会被误当真实口径的字段含义说明；列名保持中性（`amt`、`qty`、`dt`）。
4. **方言真实性 vs 业务真实性分离**：**方言语法必须真实**（窗口函数、`QUALIFY`、`MERGE`、`INSERT` 列清单、`CREATE VIEW v(c1,c2)` 都按各引擎真实语法写），但**业务内容必须虚构**。
5. **人工标注即真值**：`data/labels/*.json` 是人工逐边标注的结果，**是精确率判定的唯一真值来源**。标注规则：只标 `value` 边与 `control` 边；`unknown` 不预标（由实现产出后人工复核其 reason code 是否合理）。
6. **标注 JSON 与语料同提交**：语料改动必须同时更新标注，否则 golden 会红——这是刻意的：**语料与真值不得漂移**。
7. **golden 冻结**：`data/golden/g1`–`g5` 的期望输出一旦入库，变更必须走"新增一份 + 说明差异"，**不得原地改写期望值去迁就实现**（否则 golden 退化成快照测试）。

## 四、数值口径（单点定义，全项目引用本节）

### 4.1 三类边定义

| kind | 定义 | 典型来源 | 反例（**不得**归入 value） |
| --- | --- | --- | --- |
| `value` | 直接决定目标列**取值**的来源 | SELECT 列表项、表达式、聚合函数参数、**窗口函数的值参数**（`SUM(x) OVER (...)` 的 `x`）、CASE 的 THEN / ELSE 分支 | `PARTITION BY k`、`ORDER BY k`、WHERE 谓词 |
| `control` | 只影响**取哪些行 / 如何分组 / 排序 / 走哪条分支**，不改变取值 | `WHERE`、`JOIN ... ON`、`USING`、`GROUP BY`、`HAVING`、`OVER (PARTITION BY …, ORDER BY …)`、CASE 的 WHEN 谓词、`QUALIFY` | SELECT 列表里的列 |
| `unknown` | 无法在 AST 层面确定、且不能安全推断的来源 | 未知 schema 的 `SELECT *`（`unknown_wildcard`）、动态 SQL（`UNSUPPORTED_DYNAMIC_SQL`） | 已知 schema 的 `SELECT *`（应展开为 value/control 边） |

**判定顺序（必须按此顺序，不得重排）**：① 能否在 AST 上确定？不能 → `unknown` + reason code，结束。② 该来源是否决定取值？是 → `value`。③ 否则 → `control`。

**窗口函数的强制口径**：`SUM(x) OVER (PARTITION BY k ORDER BY t) AS w` 必须产出
`(w, value, x)` + `(w, control, k)` + `(w, control, t)` 三条边；**禁止**产出 `(w, value, k)`。
（sqlglot `lineage()` 的实测输出把 `t.x` 与 `t.k` **并列成 `w` 的同层下游、不带 kind**，
读者无法分辨哪条是值、哪条是控制 —— 这正是本项目要修正的错误。）

### 4.2 reason code 枚举（封闭集合，新增需改本节 + `constants.py` 两处）

**挂载点**列是机械判据的一部分：`边 + 诊断` 表示该码既出现在 `edges[kind=unknown].reason_code` 上也出现在 `diagnostics[]` 上；`诊断` 表示只出现在 `diagnostics[]`（该码对应的构造不产出边）。

| code | 触发条件 | 是否 `approximate` | 挂载点 |
| --- | --- | --- | --- |
| `unknown_wildcard` | `SELECT *` 且 schema 未知 | 是 | 边 + 诊断 |
| `unknown_type` | 列无法在 AST 上回溯到基表（限定名不可解 / 派生 schema 缺列 / 类型推导失败） | 是 | 边 + 诊断 |
| `positional_union` | `UNION` 两侧列别名不一致，按位置合并 | 是 | 诊断 |
| `arity_mismatch` | `INSERT` / `MERGE ... INSERT` 列清单或 `CREATE VIEW v(...)` 显式列名与来源列数不符 | 否 | 诊断 |
| `skipped_merge_branch` | `MERGE` 中该分支无法产出列级边（`DELETE` 分支、分支体形态不支持、INSERT 分支缺目标列清单且 schema 未知） | 是 | 诊断 |
| `UNSUPPORTED_DYNAMIC_SQL` | 遇 `EXEC` / `EXECUTE IMMEDIATE` 等动态 SQL，停止解析该块 | 是 | 诊断 |
| `PARSE_ERROR` | 语句解析失败，或触发 §4.7 保护性上限中止 | 否 | 诊断 |
| `recursion_limit` | CTE / 子查询展开层数超过上限 | 是 | 诊断 |
| `cycle_detected` | 表依赖图存在环 | 否 | 诊断 |
| `dialect_defaulted` | 文件无法从目录判定方言，回落 `postgres`（`--dialect` 显式指定时不触发） | 是 | 诊断 |
| `no_source_columns` | 写语句的目标列在 AST 上**无来源列**（SELECT 列表全为常量/字面量）；边集为空是确定结果，非丢弃 | 否 | 诊断 |
| `wildcard_expanded` | `SELECT *` 且 schema 已知，**正常路径**展开为具体列（非降级，仅供参考；`plan/01` §二模块③ 表） | 否 | 诊断 |
| `schema_overridden` | 外部 `--schema` 文件覆盖了从语料推导出的同名表 schema（`plan/01` §二模块①） | 否 | 诊断 |
| `unsupported_stored_procedure` | 存储过程 / 函数体内含 DML：首期不做体内血缘（D11），整条语句跳过并留痕 | 是 | 诊断 |

**规则**：
1. `unknown` 边必须带 1 个 reason code，且 `approximate=true`；
2. 降级但仍有边时必须带 1 个 reason code；
3. **没有 reason code 的静默丢弃 = FAIL**；
4. **零静默（机械判据）**：每条**写语句**（`INSERT` / `CREATE TABLE|VIEW ... AS` / `MERGE`）必须落在下列之一——① 产出 ≥1 条边；② 产出 ≥1 条诊断。两者皆无 = FAIL（退出码 `4`，§4.4）。
5. **边↔诊断对账**：每条 `unknown` 边都必须在 `diagnostics[]` 里有同 `(file, statement_index, reason_code)` 的一项；反向，挂载点为`边 + 诊断`的码若出现诊断，则同语句必须至少有一条该码的 `unknown` 边。

### 4.3 精确率与召回的判定

- **标注范围**：`data/labels/*.json` 中人工标注的 `value` + `control` 边。
- **精确率（value）** = 实现产出的 `value` 边中与标注一致者 / 实现产出的 `value` 边总数。**门槛 100%**（任一条错判即 FAIL）。
- **召回** = 实现产出的边（value 或 control）中与标注一致者 / 标注边总数。**门槛 ≥ 85%**。
- **未命中但未错判的部分必须落在 `unknown` 且带 reason code**——不落 unknown 的缺失算"静默丢失"，同样 FAIL。
- 上述判定只在**标注语料范围内**成立，不得表述为"对任意 SQL 100% 正确"。

### 4.4 退出码（全 CLI 唯一语义）

| 码 | 含义 |
| --- | --- |
| `0` | 成功；diff 模式下表示**无变化** |
| `1` | diff 模式下存在 `REMOVED`（破坏性变更） |
| `2` | diff 模式下仅 `ADDED` / `CHANGED`（非破坏） |
| `3` | 使用错误（参数非法、目录不存在、base ref 不存在）或解析/配置错误 |
| `4` | 内部断言失败（理论上不应出现；出现即缺陷） |

`lineage` / `census` / `impact` 成功返回 `0`；有 `PARSE_ERROR` 但仍能完成时返回 `0` 并把错误写进 `diagnostics[]`（**不静默**），只有无法完成时才返回 `3`。

**`diff` / `golden` 专属语义（M5）**：`0` / `1` / `2` 只属于 `diff`；`golden` 期望侧不符或门红一律 `4`。**不得**把 `1`/`2` 用到 `lineage`/`census`/`impact`（它们成功恒 `0`）。

### 4.5 方言列表（封闭集合）

`postgres` / `snowflake` / `bigquery` / `tsql` / `duckdb`。方言由文件扩展或 `--dialect` 指定；无法判定时默认 `postgres` 并在诊断里记 `dialect_defaulted`（**不静默**）。

### 4.6 排序与序列化

- 边排序键：`(target_table, target_column, kind, source_table, source_column, expr)`，全部按 Unicode 码点升序。
- 诊断排序键：`(file, statement_index, reason_code, message)`。
- 普查排序键：表名升序；表内写入者按 `(file, statement_index)` 升序。
- 序列化：UTF-8 **无 BOM**，换行 `\n`，JSON `ensure_ascii=False`、`indent=2`、键顺序固定（不使用依赖插入顺序的动态键）。
- 路径输出一律**相对语料根目录**，分隔符统一 `/`（跨平台一致）；不得输出绝对路径。

### 4.7 保护性上限

- CTE / 子查询展开层数上限：`16`（超过即 `recursion_limit`，不再展开）。
- 单文件语句数上限：`2000`（超过即中止该文件并报 `PARSE_ERROR` 类诊断，不截断后继续）。
- 单条语句 AST 节点数上限：`200000`（保护性中止，报诊断）。

> 以上数值只在**本节**定义；代码中必须引用本节常量，不得就地写裸数字。

### 4.8 写入者普查口径（`census`）

五节的判据是机械的，**不是语义推断**；报表只输出事实，不输出风险分、冲突概率、严重级别。

| 节 | 定义 | 判据 |
| --- | --- | --- |
| `writers` | 每张表 → 写它的语句列表（`文件` + `语句序号` + `方言`） | 语句有**写目标表**：`INSERT INTO t`、`CREATE TABLE\|VIEW t AS`、`MERGE INTO t`。取自内核语句台账，**不从边集反推** |
| `readers` | 每张表 → 读它的语句列表（同形） | 语句 AST 里出现该表的引用（`FROM` / `JOIN` / 子查询 / CTE 外的表） |
| `orphan` | **有读无写**：`readers` 里有、`writers` 里没有的表 | 表名集合差 `readers − writers` |
| `multi_writer` | **同一张表被 ≥2 条语句写**（同表不同列也算） | `len(writers[t]) >= 2`；单写入者表绝不出现 |
| `write_only` | **只写不读**：`writers` 里有、`readers` 里没有的表 | 表名集合差 `writers − readers` |

**规则**：

1. **写者不靠边集反推**。`INSERT INTO t VALUES (1)` 全常量、无来源列，边集为空（`no_source_columns` 是**确定结果**，§4.2）；若用"边存在 ⇔ 有写者"判定，这类写者会消失，`write_only` / `orphan` 直接判反。
2. **读者不靠边集反推**。纯 `SELECT`（不写任何表）不产边，但它是读者；`unknown` 边 `source_table` 为 `None`，把边集当读者来源会让孤儿表判定失真。读者一律取语句 AST 的表引用。
3. **CTE 名不是表**。`WITH agg AS (...)` 里的 `agg` 出现在 AST 的 `Table` 节点上，但在报表里既不进 `readers` 也不进 `writers`（它不是语料里的实体表）。
4. **自身写目标不算读**。`INSERT INTO t ... SELECT ... FROM t` 的读集合剔除 `t`（自引用不制造 `t` 的读者，否则每张自更新表都会"有人读"，`write_only` 永不成立）。
5. **纯 DDL 不是写者**。无 `AS SELECT` 体的 `CREATE TABLE t (...)` 只声明 schema，不产生数据，不进 `writers`（否则每张基表都会被算成一个写入者）。
6. **排序**：表名升序；表内条目按 `(file, statement_index)` 升序（§4.6）。
7. **零静默门复用**：`census` 跑同一份边集，同样执行 §4.2 规则 4 的机械门；失败 → 退出码 `4`（§4.4）。
8. **台账自检**：每条血缘边的 `target_table` 必须登记过写者，否则 `edges_missing_writer[]` 非空即内部不一致（退出码 `4`）。这是写者台账与边集的一致性证明，不是业务规则。

### 4.9 diff / impact / golden 口径（M5）

三者的判据同样机械，**不做语义推断**（不输出"破坏性程度""风险等级"）。

**规则 1 — 边级 diff 的分组键**：`(target_table, target_column, kind)`。key 在基线存在、当前不存在 → `REMOVED`；反向 → `ADDED`；两侧都有但**来源集合**不同 → `CHANGED`。`kind` 变化视为旧 key 消失 + 新 key 出现（不是 `CHANGED`）——因为 kind 是分组键的一部分。

**规则 2 — 来源集合元素**：`source_table.source_column`；`unknown` 边（`source_table=None`）记字面 `null`，**不得**编造表名。

**规则 3 — diff 排序**：三节各自按 `(target_table, target_column, kind)` 升序（§4.6）；同一节点的来源列表按"`null` 在前，其余码点升序"（§4.6）。

**规则 4 — 基线两模式同内核**：`--base <dir>` 直读目录；`--base <git-ref>` 用只读 `git ls-tree` + `git show <ref>:<path>` 取内容（**不切工作区、不写文件**）。两模式喂**同一个装载内核**（`loader._assemble_corpus`），故同一点必须产出同一份边集与**同一个文件 sha256**（sha 一律取"解码文本"的 sha，见 §4.6 序列化口径）。`git` 不可用 / ref 不存在 / `root` 不在仓库内 → 退出码 `3`。

**规则 5 — impact 上游/下游**：以 `<table>.<column>` 为起点，在边集的有向图上做闭包——`upstream_sources` = 反向（谁产出了它）、`downstream_consumers` = 正向（它产出了谁）。`unknown` 边无来源表，**不入图**；自环（`INSERT INTO t ... FROM t`）不入闭包。

**规则 6 — impact 穿透与最终消费者**：闭包不受单层限制（上限 `§4.7` 展开层数；同时兼作环保护）。`final_consumers` = 下游闭包中**没有更下游**的节点；`intermediate_tables` = 下游列所在的表里**既非目标表也非汇点**的那些。"穿透 N 层中间表" 的机械判据 = `len(intermediate_tables) == N`。

**规则 7 — impact 表级读者**：`reading_statements` 取 `corpus.reads`（**K13 口径**，不从边集反推）——纯 `SELECT` 不产边但它是消费者。目标表不在血缘图（schema ∪ 写者台账 ∪ 读者台账）→ 退出码 `3`（防打错表名得空结果）。

**规则 8 — golden 期望侧冻结**：`data/golden/g<k>/expected.json` 是**按本节口径人工推导**的期望，**不得**由实现反向生成（防"实现即真值"循环，`plan/04 §二`）。顶层键只认 `lineage` / `census` / `impact` / `diff` 且至少一个——拼错或写空必须红，不得静默通过。`golden` 的每一份语料都跑 §4.2 规则 4 的零静默门与封闭枚举守卫（与 `lineage`/`census` 同一份，不各判一套）；期望不符或门红 → 退出码 `4`。找不到任何含 `expected.json` 的 golden → 退出码 `3`（防空跑全绿）。

**规则 9 — 确定性**：`diff` / `impact` / `golden` 的 JSON 同输入两次运行字节级一致（单一出口 `output.dumps_json`；§4.6）；输出**不得**含时间戳、绝对路径或 Windows 反斜杠（`--base`/`root` 给绝对路径时只报计数、`ref` 记 `null`）。

## 五、可复现记录附录

竞品实测的最小复现命令（基准日 2026-10-20，`sqlglot 30.23.0`）：

```bash
python -c "import sqlglot; print(sqlglot.__version__)"   # 基准日实测：30.23.0

# 复现"窗口分区键与值参数同级、无类型标注"（结论见 plan/01 §1.1）
# 注意：30.x 的 lineage() 的 schema 是必填位置/关键字参数
python - <<'PY'
import sqlglot
from sqlglot.lineage import lineage
from sqlglot.schema import MappingSchema
schema = MappingSchema({"t": {"x": "int", "k": "int"}})
n = lineage("w", sqlglot.parse_one("SELECT SUM(x) OVER (PARTITION BY k) AS w FROM t"),
            schema=schema, dialect="postgres")
def walk(node, depth=0):
    print(" " * depth + node.name)
    for child in node.downstream:
        walk(child, depth + 2)
walk(n)   # 实测输出：w / t.x / t.k —— 两个下游同层，没有 kind
PY
```

> 上面的脚本只**记录调用路径与实测形态**，不把竞品输出当断言——竞品的输出会随版本变化。
> **不要用竞品输出当本项目的期望值**：`g1` 的期望值是按 §4.1 口径人工推导的
> （`x` 为 value，`k` 为 control）。
