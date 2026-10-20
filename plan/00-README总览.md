# 00 · README 总览 — 10-20-sqltrace（SQL 值/控制双通道血缘）

> 方法论：`ai-tool-project-sprint`（装订 2026-10-20）｜布局门：`py -X utf8 tools/check_sprint_layout.py`｜续接对话第一件事 = 跑它

> 方法论：`ai-tool-topic-definer` 阶段 4（骨架四件套）｜**续接对话第一件事 = 读本文档 §二 决策记录与 §六 里程碑**

- **项目**：SQLTrace——SQL 值/控制双通道血缘 + 写入者普查 + diff 闸门（**纯本地 Python CLI**）
- **性质**：不参赛项目题 · 发布 GitHub **公开仓库** · 署名 `yuluo554`
- **版本**：v1（2026-10-20 定稿；竞品与开源检索基准日 **2026-10-20**）；M0 骨架同日落地
- **当前状态**：**M6 发布完成**（M0 骨架 + M1 语料/标注/golden 输入侧/装载器闭环 + M2 AST 血缘边 + M3 降级策略与零静默门 + M4 写入者普查五节 + M5 diff/impact/golden + M6 发布三件套）。状态列见 §六。
- **一句话定位**：离线列级血缘不空（FlowScope 105★ 已占），但没人把**值边与控制边分开**、没人做**写入者普查**、没人做**纯 SQL 目录的 git diff 闸门**——本工具只押这三件。
- **交付形态**：**唯一形态 = 纯本地 Python CLI**。无数据库连接、无元数据平台、无服务端、无网络请求、无图形界面。

## 一、文档索引

| 文档 | 内容 | 状态 |
| --- | --- | --- |
| `plan/00-README总览.md` | 本文档：索引、决策记录、弃选项、承诺-证据台账、招牌动词表、提交材料实物表、里程碑 | ✅ M0 |
| `plan/01-题目文档.md` | 十段式题目定稿（**定稿不改写**；勘误走版本史行 + 版本号） | ✅ M0 |
| `data/README.md` | 依据查证记录（三态）、数据源可获取性、合成数据纪律、**数值口径单点定义（§四）** | ✅ M0 |
| `plan/02-架构与技术选型.md` | 分层、目录结构、依赖与确定性约束 | ✅ M1 |
| `plan/03-模块详设.md` | M1–M5 实现级设计与失败路径 | ✅ M1（M3/M4/M5 节均已按实现回写） |
| `plan/04-数据计划.md` | 语料目录、标注规则、golden 冻结纪律 | ✅ M1 |
| `plan/05-里程碑与发布.md` | 逐里程碑 DoD 与状态回写 | ✅ M1 |
| `plan/06-交付对标与决策.md` | 评分对标、开放项 | ✅ M1 |
| `src/sqltrace/` | CLI 源码（装载 / 内核 / 降级 / 普查 / diff） | ✅ M1–M5 全落地 |
| `data/corpus/**/*.sql` + `data/labels/*.json` | 40–60 个 `.sql` 人工标注语料 | ✅ M1 |
| `data/golden/g1`–`g5` | 五条 golden 回归（输入 + 期望输出 + 说明） | ✅ 输入侧 M1 冻结；期望侧 M5 冻结；`sqltrace golden` 五条全绿 |
| `docs/census-sample.md`、`docs/diff-sample.json` | 真实运行输出样例 | ✅ `census-sample.md` M4；`diff-sample.json` M5 |
| `plan/RELEASE-M6.md` | 发布留档（**tag 前入库**；tag 后事实分栏追加） | ✅ M6 |
| `plan/HANDOFF-M<k>.md` | 第 k 个里程碑收尾交接单 | ✅ M1 起（M0 豁免） |

## 二、决策记录

> **D1–D3 是本题的定位生死线，任何里程碑都不得削弱。**

| 编号 | 日期 | 决策 | 理由 / 弃选 |
| --- | --- | --- | --- |
| **D1** | 2026-10-20 | **"离线纯本地列级血缘"不是空白：FlowScope（pondpilot/flowscope）105★ / 22 fork 已占，且比多数人以为的深**——14 方言、DDL schema、dbt/Jinja 预处理、`APPROXIMATE_LINEAGE` / `UNKNOWN_TABLE` 降级码、72 条 lint 规则、Impact X-Ray（上游祖先 / 下游后代）、CLI 预编译二进制、导出 mermaid/json/csv/xlsx/duckdb | 把"离线"当卖点会正面撞车，且在功能面上明显落后。**题面、README、定位宣言一律不得出现"离线血缘空白/首创"类措辞**；只允许写"三个切口未被覆盖"。 |
| **D2** | 2026-10-20 | **护城河很薄：FlowScope 加一个 diff 闸门是 PR 量级**。本题必须靠"值/控制分型的正确性 + 写入者普查的零误报 + 永不猜测的信誉"立住 | 竞品功能面更宽，本项目短期不可能在宽度上赢。唯一可持续的差异是**正确性纪律**：`value` 边精确率 100%（宁可 unknown）、每档降级带 reason code（零静默）、五条 golden 可复算。这三条是全部护城河，缺一条就退化成 FlowScope 的低配版。 |
| **D3** | 2026-10-20 | **最大风险：把 M2/M3 做成"能跑 demo"就收工**——那样与 FlowScope 无区别 | demo 级实现的典型症状：窗口分区键当值边（sqlglot 的原错）、`SELECT *` 猜列名、`INSERT` 列清单报错就跳过、解析失败静默丢语句。**验收基准的三条硬门禁**（精确率 100% / 零静默 / 五条 golden）就是防这个的；每个里程碑收尾必须跑，不是最后补。 |
| D4 | 2026-10-20 | 交付形态收敛为**唯一**：纯本地 Python CLI | 不设"库 API / 服务端 / Web UI / 桌面 GUI"备选。形态留后门会给空壳通行证（预检 ⑩/㉕）。库 API 不作为验收路径。 |
| D5 | 2026-10-20 | 内核 = **sqlglot AST + 自研 scope walker**；**不调用 sqlglot 的 `lineage()` 作为判定路径** | 实测 sqlglot `lineage()`：窗口分区键当值输入、`INSERT` 列清单报 `Cannot find column`、多语句报 `sql must be SELECT`、`MERGE` 不支持、无 schema `SELECT *` 不支持。在错误输出上打补丁不可能得到正确分型；只能把 sqlglot 当解析器用。 |
| D6 | 2026-10-20 | **三类边（value / control / unknown）+ reason code 枚举**写进 `data/README.md` §四，**单点定义** | 内核、降级、普查、diff、文档共用一套口径；任何模块不得自行解释"什么是控制边"或新增 reason code。 |
| D7 | 2026-10-20 | **精确率 100% 优先于召回**：宁可 `unknown`，不得假边 | 对应六条真实 issue 的共同形态——"图还能画出来，只是少了一列"。假边比缺边更坏：缺边可从 unknown 清单补救，假边会被当成事实进入下游决策。 |
| D8 | 2026-10-20 | **零网络**：运行期不发任何请求；不接元数据平台；不连数据库 | 语料是企业内网 SQL，联网即隐私风险；也是"可进 CI"的前提。`--diff <git ref>` 只做本地只读 git 调用。 |
| D9 | 2026-10-20 | 输出**稳定排序 + 固定换行（`\n`）+ UTF-8 无 BOM**；同输入两次运行 JSON 字节级一致 | 否则 diff 闸门在 CI 里会噪声报警；跨平台（Windows/Linux）必须一致。 |
| D10 | 2026-10-20 | 首期方言限定 **5 种**：PostgreSQL / Snowflake / BigQuery / T-SQL / DuckDB | 方言越多，AST 差异越大，M1–M3 的正确性越难保证；先把 5 种的精确率做到 100%。 |
| D11 | 2026-10-20 | **不做存储过程体内血缘（首期）** | sqlglot 实测：`CREATE PROCEDURE` 只给 Block 包装，T-SQL `GO` 直接 `ParseError`。一周内做不出可信结果，只能靠启发式 → 违背 D5/D7。 |
| D12 | 2026-10-20 | **`SELECT *` 在 schema 未知时不猜列名**，只产出 `unknown_wildcard` + `approximate=true` | FlowScope / sqllens 已做逆向推导（D1）；本题刻意不做，以"零猜测"为信誉资产。这是能力边界声明，不是缺陷。 |
| D13 | 2026-10-20 | M6 产物口径采用 **A) Release 附产物**（`release/*.whl` 或源码包 + `SHA256SUMS`，本地留副本） | 纯 CLI 工具，用户需要能直接 `pip install` 的产物；源码 zipball 不能替代可安装包。 |
| D14 | 2026-10-20 | 品牌隔离：不复用本系列任何其他 CLI 工具的命名、代码、素材与文档模板；本文档不提及它们 | 系列内工具受众不同，交叉引用会污染检索与定位。 |

### 弃选项（候选方向，均已否决）

| 弃选项 | 弃因 |
| --- | --- |
| **"纯 lineage diff 闸门"独立产品** | diff 只是本题 M5 一个模块，单独拎出来不构成产品；且 **parrant 82★ / whatbreaks / zhao-cli / dbt-plan 四家已用 SQLGlot 做同构事**，正面红海。diff 必须悬挂在"正确分型 + 普查"之上才有差异。 |
| **存储过程体血缘（首期）** | 确定性内核成本极高（sqlglot 实测对 `CREATE PROCEDURE` 只给 Block 包装，T-SQL `GO` 直接 `ParseError`），必然靠启发式 → 违背 D5/D7。 |
| **`SELECT *` 逆向推导** | FlowScope 已实现（无 schema 时从下游反推列），撞车且无法保证零猜测。 |
| **交互式血缘图 UI** | 撞 FlowScope 的 Impact X-Ray 与 SQL Crack（171★），且属可视化禁区；本题的输出价值在 CI 与 PR 评论，不在看板。 |
| **元数据平台对接（DataHub / OpenMetadata / Atlas / OpenLineage）** | 都是平台形态（datahub 12,866★、atlas 2,155★、OpenLineage 2,715★），接入成本远超一周，且把"纯本地"这个唯一硬约束让掉。 |
| **数据库连接 / `--sqlalchemy_url`** | 撞 sqllineage 的既有入口，且引入凭据与环境依赖，破坏"离线可复算"。 |
| **dbt 项目 / Jinja 解析** | FlowScope 已做 dbt/Jinja 预处理；本题以"纯 SQL"为分工边界（§六）。 |
| **风险评分 / 冲突概率** | 普查只输出事实（谁写了、谁读了、谁冲突），不打分；打分不可复算，违背确定性纪律。 |
| **LLM 辅助推断列名** | 直接违反 D7（宁可 unknown 不得假边）；且不可复算、不可进 CI。 |

## 三、承诺-证据台账（全项目唯一一份）

> 其他文档只可引用本表，不得复制第二份。状态列随里程碑同步翻转；`⬜` = 尚未兑现，**任何文档不得写成已完成**。

| 承诺项 | 素材来源 | 交付物内可达性 | 核验方式 | 状态 |
| --- | --- | --- | --- | --- |
| 值/控制双通道分型 | 本题设计；口径在 `data/README.md` §四 | `src/sqltrace/core/` 的边生成 | 人工标注语料上 `value` 边精确率 100%；窗口用例 `w<-x`(value) + `w<-k`(control) | ✅ M2 |
| sqlglot 分区键误判被修正 | sqlglot 30.23.0 实测：`SUM(x) OVER (PARTITION BY k)` → `w` 的下游是 `t.x` 与 `t.k`（同层、无 kind 标注） | 同上 | 专项用例（golden g1） | ✅ M2 |
| sqllineage #276 谓词血缘（四年未做）被覆盖 | issue #276（open 2022-07-20） | `control` 边 | 标注语料中 WHERE / ON / USING / HAVING / QUALIFY 均有 control 边 | ✅ M2 |
| 降级 reason code 枚举 + 零静默 | 本题设计；枚举在 `data/README.md` §4.2 | `src/sqltrace/fallback.py` | `grep -c unknown` 与诊断未解析计数一致；无"解析了但无输出无诊断"的语句 | ✅ M3 |
| `SELECT *` 未知 schema 不猜列名 | 本题设计（D12）；反例 OpenLineage #3809 | `unknown_wildcard` + `approximate=true` | golden g2：输出中不含任何猜测列名 | ✅ M3 |
| `INSERT` 列清单位置映射 | 本题设计；反例 sqlglot 实测 `Cannot find column 'c1'` | `arity_mismatch` 诊断 | golden g3 | ✅ M3 |
| `CREATE VIEW v(c1,c2)` 列名对齐 | 本题设计；反例 OpenMetadata #33077 | 显式列名对齐 | 专项用例（静默丢列的反例） | ✅ M3 |
| 写入者普查（writers / readers / orphan / multi-writer / write-only） | 本题设计；检索式 `sql table multiple writers conflict` → 0 | `census` 子命令 + Markdown 报表 | 合成语料植入项全命中且无误报；golden g4 | ✅ M4 |
| lineage diff 闸门（ADDED/REMOVED/CHANGED + 退出码） | 本题设计；检索式 `sql folder git diff lineage` → 0 | `diff --base` | 同输入两次 JSON 字节级一致；golden g5 | ✅ M5 |
| `impact` 穿透两层中间表 | 本题设计；HN 47946547 原话 | `impact <table>.<column>` | golden g5 中 `impact raw_src.nm` 给出最终消费者 `leaf.nm`；真实语料 `impact raw_cust.nm` 穿 2 层 | ✅ M5 |
| 原型四段链路已验证 | 单文件原型（多文件 → 边 → 影响查询 → 两版本 diff） | — | 本机运行记录 | ✅ 已登记（原型，非交付物） |
| 竞品实测（sqlglot / sqllineage / FlowScope） | 本机实测 + GitHub API 快照，基准日 2026-10-20 | 题面 §1.1 | 复现命令写进 `data/README.md` §二 | ✅ 已登记 |
| 六条真实 issue 与需求原话 | 各 issue 页与 HN 条目，基准日 2026-10-20 | 题面 §1.2 / §1.3 | 链接可直连 | ✅ 已登记 |
| 三个切口检索为 0 | `gh api` 检索式与 `total_count` | 题面 §1.4 | 检索式 + 计数 + 基准日成对出现 | ⬜ 软论据（检索未穷尽，非全量） |
| 零网络 / 无数据库连接 | 本题设计（D8） | 全 CLI | 静态扫描无网络调用；无 DB 驱动依赖 | ✅ M5 |
| 同输入两次运行字节级一致 | 本题设计（D9） | 全部 JSON 输出 | 两次运行 `sha256` 相同；跨平台一致 | ✅ M5（Windows 本机双跑；Linux 侧待 CI，见 `plan/05 §四`） |
| 五条 golden 回归 | 本题设计 | `data/golden/g1`–`g5` | `sqltrace golden` 一条命令全绿 | ✅ M5 |
| 发布三件套 | 本题设计（D13） | 仓库发布流程 | git tag + GitHub Release（**附产物** `release/*.whl` + `SHA256SUMS`）+ `plan/RELEASE-M6.md` | ✅ M6 |

## 四、招牌动词表（能力名词 → 交付态命令 → 断言基准）

> 标题与定位宣言里出现的每个能力名词都必须填满后两格；填不出的词已删除或降级为扩展项。

| 能力名词 | 哪条交付态命令产出它 | 哪条基准 / 测试断言它 |
| --- | --- | --- |
| 值边（value） | `sqltrace lineage <dir> --json` 的 `edges[kind=value]` | 标注语料 `value` 精确率 100%；golden g1 |
| 控制边（control） | `sqltrace lineage <dir> --json` 的 `edges[kind=control]` | 标注语料中 WHERE/ON/USING/HAVING/QUALIFY/窗口分区键均有 control 边；golden g1 |
| unknown 与 reason code | `sqltrace lineage <dir> --json` 的 `edges[kind=unknown]` + `diagnostics[]` | `grep -c unknown` 与未解析计数一致（零静默） |
| 写入者普查 | `sqltrace census <dir> --md` | golden g4：多写冲突 / 孤儿表全命中且无误报 |
| 多写冲突 | `sqltrace census <dir> --json` 的 `multi_writer[]` | golden g4 植入项全命中 |
| 血缘 diff | `sqltrace diff --base <ref> --json` | golden g5：ADDED/REMOVED/CHANGED 正确 + 退出码正确 |
| 爆炸半径穿透 | `sqltrace impact <table>.<column>` | golden g5：穿透两层中间表 |
| 确定性输出 | `sqltrace lineage <dir> --json` 两次运行 | `sha256` 相同；跨平台一致 |
| 零静默 | 全命令的诊断输出 | 诊断计数与 unknown 计数一致；无静默丢弃 |
| 五条 golden | `sqltrace golden data/golden` | 五条全绿的退出码 0 |

## 五、提交材料实物表（承诺项 → 应存在文件 → 里程碑 → 核对命令）

> `plan/01` §三 的每一项都必须在这里有落点；指不出文件路径的承诺现在就删。

| 承诺项 | 应存在的文件路径 | 由哪个里程碑产出 | 用哪条命令核对 |
| --- | --- | --- | --- |
| CLI 源码 | `src/sqltrace/`（入口 `src/sqltrace/cli.py`） | M2–M5 | `git ls-files src` |
| 人工标注语料 | `data/corpus/**/*.sql`（40–60 个）+ `data/labels/*.json` | M1 | `find data/corpus -name '*.sql' \| wc -l` |
| 五条 golden 回归 | `data/golden/g1`–`g5`（输入 + 期望 JSON + 说明） | M1 / M5 | `sqltrace golden data/golden` |
| 报告样例 | `docs/census-sample.md`、`docs/diff-sample.json` | M4 / M5 | 文件存在 + 内容为真实输出 |
| 文档套件 | `plan/00`、`plan/01`、`data/README.md` | M0 | `git ls-files plan data` |
| 发布留档 | `plan/RELEASE-M6.md` | M6（tag 前入库） | `git cat-file -e <tag>:plan/RELEASE-M6.md` |
| Release 产物 | `release/*.whl`、`release/SHA256SUMS` | M6 | `gh release view` + `sha256sum -c` |

## 六、里程碑

| 里程碑 | 内容 | DoD | 状态 |
| --- | --- | --- | --- |
| **M0 装订与骨架** | 方法论装订三件 + plan/02–06 + 可运行骨架（src/sqltrace 命令树占位 + pyproject + tests 冒烟） | 布局门绿且变异验证通过；`pip install -e .` 后 `sqltrace --help` 可跑；骨架冒烟测试绿 | ✅ |
| **M1 数据先行** | 40–60 个 `.sql` 人工标注语料（5 方言）+ 标注 JSON + 五条 golden 的**输入侧**定稿；语料不变量自检（无真实表名、无真实人名、无公司名） | 语料文件数落进区间；每条 golden 有输入与一句话说明；标注 JSON 覆盖全部 value 边；`sqltrace` 可遍历语料并输出文件清单（装载器最小闭环） | ✅ |
| **M2 血缘内核** | sqlglot AST + 自研 scope walker；三类边 + 元数据（expr / join_path / aggregation / window） | `value` 边精确率 100%；召回 ≥85%；窗口用例 `w<-x`(value) + `w<-k`(control)，**不得**出现 `w<-k` 的 value 边；golden g1 绿 | ✅ |
| **M3 降级策略** | 全部策略档 + reason code 枚举 + 诊断 | `grep -c unknown` 与未解析计数一致；每个降级构造都有对应 reason code；**零静默**；golden g2 / g3 绿 | ✅ |
| **M4 写入者普查** | writers / readers / orphan / multi_writer / write_only + Markdown 报表 | 合成语料植入项全命中、单写入者表零误报；golden g4 绿；`docs/census-sample.md` 为真实输出 | ✅ |
| **M5 diff 闸门与输出** | `diff --base`（git + 双目录）、`impact`、退出码、JSON 稳定排序 + Markdown 评论 | 同输入两次运行 JSON 字节级一致、跨平台一致；`impact` 穿透两层；golden g5 绿；五条 golden 一条命令全绿 | ✅ |
| **M6 发布** | 发布 GitHub **公开仓库** | **M6 DoD = 三件套：①git tag ②GitHub Release（附产物 `release/*.whl` + `SHA256SUMS`，本地留副本）③发布留档 `plan/RELEASE-M6.md`（tag 之前写好并进 tag 树）**；发布后实测值在留档里分栏追加 | ✅ |

> 里程碑表的 DoD 列**只能加不能减**；任何裁剪必须在决策记录新增一行说明理由。

## 七、数字承诺纪律

不写会随实现漂移的硬数字（测试数 / 用例数 / 代码行数 / 通过数）；竞品星数与 issue 编号是带基准日的快照，属于已核对证据，允许出现。所有数值口径（三类边定义、reason code 枚举、精确率/召回判定、退出码、方言列表、排序规则）**只在 `data/README.md` §四定义一次**，plan/01、代码注记、报表文案一律引用该节，不得手写第二口径。
