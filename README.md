# SQLTrace — SQL 值/控制双通道血缘 + 写入者普查 + diff 闸门

**纯本地 Python CLI**：无数据库连接、无服务端、无网络请求、无图形界面。安装后命令名 `sqltrace`。

> 状态：**M6 发布**（M0 装订骨架 + M1 语料/标注/golden 输入侧/装载器闭环 + M2 AST 血缘边 + M3 降级策略与零静默门 + M4 写入者普查五节 + M5 diff/impact/golden + M6 发布三件套），里程碑状态见 `plan/00` §六。**当前发布版 `v0.1.1`**（修复零静默门漏 DML、Windows CRLF、`requires-python` 与依赖不自洽等，见 `plan/RELEASE-M6.1.md`）。

## 定位（诚实边界）

离线列级血缘**不是空白**——FlowScope（pondpilot/flowscope，105★）已占该位置。本工具只押三个未被覆盖的切口：

1. **值边 vs 控制边分型**：`SUM(x) OVER (PARTITION BY k) AS w` 产出 `w←x`（value）+ `w←k`（control），修正 sqlglot `lineage()` 把分区键与值参数并列且不标类型的实测错误。
2. **写入者普查**：每张表被谁写过、谁在读、孤儿表、多写冲突。
3. **git 维度 lineage diff 闸门**：`sqltrace diff --base HEAD~1` 在 CI 里给退出码阻断破坏性变更。

正确性纪律：`value` 边精确率 100%（人工标注语料范围内，宁可 `unknown` 不得假边）；每档降级带机器可读 reason code（零静默）；同输入两次运行 JSON 字节级一致。口径单点定义在 `data/README.md` §四。

运行期要求 **Python ≥3.9**（`sqlglot>=30.20` 自身要求 ≥3.9）；输出换行恒为 `\n`（跨平台字节级一致，Windows 亦不产 CRLF）。

**零静默是可执行的门，不是口号**：`sqltrace lineage` 对每条写语句断言"有边或有诊断"，任何静默丢弃都会让它以退出码 `4` 失败。写语句 = `INSERT` / `CREATE TABLE|VIEW ... AS` / `MERGE` / **`UPDATE` / `DELETE` / `TRUNCATE` / `COPY`**——后四类本期不做列级血缘，一律落 `unsupported_write_statement` 诊断（能力边界见 `data/README.md` §4.2）。

## 命令树（M1–M5 全部落地）

```bash
sqltrace lineage <dir> --json        # 列级血缘（M2/M3）
sqltrace census  <dir> --md          # 写入者普查报表（M4）
sqltrace diff    <dir> --base <ref>  # lineage diff 闸门（M5；退出码 0/1/2/3/4）
sqltrace impact  raw_cust.nm <dir>   # 反向影响，穿透中间表（M5）
sqltrace golden  data/golden         # 五条 golden 回归（M5；一条命令全绿）
```

## 安装与开发

```bash
py -m pip install -e .[dev]          # 本机 Windows；python 是商店占位符
py -X utf8 -m pytest tests           # 冒烟
py -X utf8 tools/check_sprint_layout.py   # 布局门（方法论装订）
```

运行期依赖仅 `sqlglot`（只当解析器，不调用其 `lineage()`）+ 标准库。License: MIT。

## 安装发布版

```bash
pip install https://github.com/yuluo554/sqltrace/releases/download/v0.1.1/sqltrace-0.1.1-py3-none-any.whl
```

需要 **Python ≥3.9**。校验和见 Release 附件的 `SHA256SUMS`（`sha256sum -c SHA256SUMS`）。CI 状态：三 job 全绿（布局门 / 全量测试 + 五条 golden（3.12） / 最低支持版本 3.9 真装真跑），run id 见 `plan/RELEASE-M6.1.md` §二。
