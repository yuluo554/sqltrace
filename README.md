# SQLTrace — SQL 值/控制双通道血缘 + 写入者普查 + diff 闸门

**纯本地 Python CLI**：无数据库连接、无服务端、无网络请求、无图形界面。安装后命令名 `sqltrace`。

> 状态：M1 数据先行完成（M0 装订骨架 + M1 语料/标注/golden 输入侧/装载器闭环）；M2–M6 未开工，里程碑状态见 `plan/00` §六。

## 定位（诚实边界）

离线列级血缘**不是空白**——FlowScope（pondpilot/flowscope，105★）已占该位置。本工具只押三个未被覆盖的切口：

1. **值边 vs 控制边分型**：`SUM(x) OVER (PARTITION BY k) AS w` 产出 `w←x`（value）+ `w←k`（control），修正 sqlglot `lineage()` 把分区键与值参数并列且不标类型的实测错误。
2. **写入者普查**：每张表被谁写过、谁在读、孤儿表、多写冲突。
3. **git 维度 lineage diff 闸门**：`sqltrace diff --base HEAD~1` 在 CI 里给退出码阻断破坏性变更。

正确性纪律：`value` 边精确率 100%（人工标注语料范围内，宁可 `unknown` 不得假边）；每档降级带机器可读 reason code（零静默）；同输入两次运行 JSON 字节级一致。口径单点定义在 `data/README.md` §四。

## 命令树（骨架就绪，M1–M5 落地）

```bash
sqltrace lineage <dir> --json        # 列级血缘（M2/M3）
sqltrace census  <dir> --md          # 写入者普查报表（M4）
sqltrace diff    <dir> --base <ref>  # lineage diff 闸门（M5）
sqltrace impact  raw.cust.nm <dir>   # 反向影响，穿透中间表（M5）
sqltrace golden  data/golden         # 五条 golden 回归（M5）
```

## 安装与开发

```bash
py -m pip install -e .[dev]          # 本机 Windows；python 是商店占位符
py -X utf8 -m pytest tests           # 冒烟
py -X utf8 tools/check_sprint_layout.py   # 布局门（方法论装订）
```

运行期依赖仅 `sqlglot`（只当解析器，不调用其 `lineage()`）+ 标准库。License: MIT。
