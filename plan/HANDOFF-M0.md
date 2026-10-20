# HANDOFF-M0 — 装订与骨架交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 用法：`/goal 读取 <项目绝对路径>\plan\HANDOFF-M1.md 继续完成任务`（下一棒是 M1）。

## 一、当前进度 + 证据

- **M0 完成**（commit `2547903`）：装订三件 + plan/02–06 + 可运行骨架。
- 证据：布局门 8 项 PASS 全绿（扫到文档 10 / 状态副本 3 / 点名工具 1）；**8 组变异验证全红**（M1 删 AGENTS.md / M2 副本状态翻转 / M3 删 plan/02 / M4 删装订行 / M5 删布局门脚本 / M6 删 data/README / M7 删 README / M8 删 plan/05，还原后字节一致且复跑绿）。
- 冒烟测试 **9 passed**（`py -X utf8 -m pytest tests -q`）。
- `pip install -e .`（py -3.12 官方源）→ `sqltrace --version` = 0.1.0.dev0、`lineage` 子命令 rc=0 可跑；装后已卸载（工作树无 egg-info 残留，`git status` 干净）。

## 二、当前事实·状态不变量（下一棒动手前必读）

1. **口径唯一真相源 = `data/README.md` §四**；代码侧引用点 = `src/sqltrace/constants.py`（REASON_CODES 9 个、DIALECTS 5 个、上限 16/2000/200000、退出码 0–4）。**改口径先改 data/README §四再同步 constants.py**，两处不得漂移——`test_constants_match_data_readme` 只查成员数，语义漂移靠纪律。
2. **版本两处定义**：`src/sqltrace/__init__.py` 的 `__version__` 与 `pyproject.toml` 的 `version`，**必须一起改**（当前 0.1.0.dev0；定版 M6 时两处同步）。
3. **布局门判据与文档强耦合**：装订行正则锚定 `check_sprint_layout`（下划线形态）与日期同行；`plan/00/05/README` 三处里程碑状态行必须用 `| M0 |` 表格行形态（门只认表格行、锚定单元格开头）。**M6 缺口列写关闭说明时不要点文件名**（防 RELEASE-M6 撞里程碑号判据——门已剥单元格开头锚定，但仍按此写最稳）。
4. **门脚本被 AGENTS.md/plan/00/README 点名**（LAYOUT.DOC_TOOLS 判据）——改门文件名前先改三处文档。
5. **依赖安装通道事实**：清华镜像 sqlglot 最高 26.33，装不到 30.x；**必须用官方源**（本机 pip 有代理污染，`NO_PROXY="*"` 前缀可解）。sqlglot 30.23.0 在 3.12 通道可装；**3.8 通道未装过**（30.x 是否支持 3.8 未验证）。
6. **pytest 只在 3.8 通道确认过可用**；3.12 通道 pytest 未装（本棒测试全在 3.8 跑）。

## 三、下一棒待办（M1 数据先行）

1. `data/corpus/**/*.sql`：40–60 个文件、5 方言（postgres/snowflake/bigquery/tsql/duckdb），按 `plan/04` 真值纪律（raw/stage/mart 假名、占位字面量）。
2. `data/labels/*.json` 逐边人工标注（只标 value/control；规则见 data/README §三#5）。
3. 五条 golden 的**输入侧**（g1 窗口分型 / g2 未知 schema SELECT * / g3 INSERT 列清单 / g4 多写+孤儿 / g5 diff）。
4. loader 落地：.gitignore 解析、DDL/CTAS schema 推导、拓扑排序、`cycle_detected`；装载器遍历语料输出文件清单的最小闭环（M1 DoD）。
5. 语料不变量自检（无真实表名/人名/公司名）。

## 四、既定口径清单（K 编号，动了会打挂测试）

- **K1**：三类边与判定顺序（AST 确定不了→unknown，先于 value/control）——data/README §4.1。
- **K2**：reason code 封闭枚举 9 个——§4.2；新增必须改该节 + constants.py。
- **K3**：退出码 0/1/2/3/4——§4.4；argparse 用法错误保持 SystemExit(2)。
- **K4**：排序键 (target_table, target_column, kind, source_table, source_column, expr) 码点升序——§4.6；序列化 UTF-8 无 BOM、`\n`、`indent=2`、`ensure_ascii=False`。
- **K5**：不调用 sqlglot `lineage()`/`qualify()` 作判定路径（D5）；sqlglot 钉 `>=30.20,<31`。
- **K6**：零网络——任何 src/ 文件不得 import requests/urllib/http.client/socket 等（`test_no_network_imports` 常驻）。
- **K7**：语料与标注同提交；golden 期望冻结后只增不改（data/README §三#6#7）。

## 五、本机环境坑（实测日期 2026-10-20）

- `python` 是商店占位符，一律 `py`；控制台中文一律 `py -X utf8`；全程 `PYTHONDONTWRITEBYTECODE=1` 防 pyc 损坏。
- pip 代理污染：官方源需 `NO_PROXY="*" no_proxy="*"` 前缀；清华镜像缺 sqlglot 30.x。
- `py -0p` = 3.8.8-64 与 3.12-64；pytest 仅 3.8 通道确认；sqlglot 30.23.0 仅 3.12 通道确认。
- Git Bash 下临时脚本写在仓库目录（`/tmp` 的 py 脚本可跑但落 D:/program/Git，会污染 git status 视野）；临时文件用完即删。

## 六、M0 DoD checklist

- [x] 装订三件齐（AGENTS.md / tools/check_sprint_layout.py / plan/00 顶部行）
- [x] 布局门全绿 + 8 组变异全红 + 还原复绿
- [x] plan/02–06 齐且含必需小节
- [x] 骨架 `pip install -e .` 后 `sqltrace --help` / `--version` 可跑
- [x] 冒烟测试绿（9 passed）
- [x] plan/00·05·06 状态回写一致（M0 保持 ⬜→本次三方一致写 ⬜；**下一棒收尾时三处一起翻 ✅**）
- [ ] CI 步骤接线（无远端，M6 首推时在 workflow 里加布局门步骤）

## 七、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -X utf8 -m pytest tests -q   # 冒烟
NO_PROXY="*" py -3.12 -m pip install -e .        # 可安装验证（官方源）
sqltrace --version && sqltrace lineage data --json
git -c core.quotepath=false status --short       # 中文路径不转义
```
