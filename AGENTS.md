# AGENTS.md

本仓库遵循 **`ai-tool-project-sprint`** 方法论（装订日期：2026-10-20）。

## 任何新对话的第一件事

```bash
py -X utf8 tools/check_sprint_layout.py    # 布局门；必须绿，红了先修布局再干活
```

- 续接对话：读 `plan/HANDOFF-M<k>.md`（那是第 k 棒的收尾交接单），**先跑上面这条门**。
- 接手对话（无 HANDOFF）：先读 `plan/00`、`plan/05`、`plan/06` 与各 HANDOFF，重建"当前状态 + 既定口径清单"再动手。
- **门不存在 = 本项目没装订** → 先补第零步，再做别的。

## 强制布局（布局门逐条断言，改动前先看这里）

| 项 | 位置 | 判据 |
| --- | --- | --- |
| 计划套件 | `plan/00–06` + `data/README.md` | 存在且各含必需小节（标题关键词） |
| 数据台账 | `data/README.md` | 台账在位（依据三态 + 合成纪律 + 数值口径 §四） |
| 交接单 | `plan/HANDOFF-M<k>.md` | 每个 ✅ 里程碑一份（**M0 豁免**：M0 的收尾记录就是计划套件 + 骨架本身；从 M1 起七节齐，含"当前事实·状态不变量"） |
| 里程碑状态副本 | `plan/00` 里程碑表 + `plan/05` 状态表 + `README.md` 状态行 (+ `plan/06` 缺口列) | **逐处一致**，逐副本采集任一不一致即红 |
| 发布留档 | `plan/RELEASE-M<last>.md`（两栏）或 `plan/WRAPUP-M<n>.md` | 标题齐、覆盖对账表三态行 ≥3 |
| 文档点名工具 | `tools/*.py` 等路径形态 | 文档里引用的每个 `tools/` 脚本必须在 `git ls-files` 指得到实物 |

## 环境事实与禁忌

- 本机（2026-10-20 实测）：`py -0p` = 3.8.8-64 与 3.12-64 两条通道；跑脚本一律 `py -X utf8`（`python` 是商店占位符）；目标解释器 3.8 兼容（代码不写 3.9+ 语法）。
- 依赖安装走清华源：`NO_PROXY="*" py -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>`（本机 pip 代理污染）；全程 `PYTHONDONTWRITEBYTECODE=1` 防 pyc 损坏。
- 禁止：把"未执行"写成已完成；无远端时 DoD 写"CI 绿"（只能写"本地等价校验（未接远端，CI 待首推验证）"）；tag 之后改交付面代码。
- 本项目领域红线（`plan/00` D1/D8）：不得写"离线血缘空白/首创"；运行期零网络、零数据库连接。
