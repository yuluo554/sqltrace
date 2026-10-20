# -*- coding: utf-8 -*-
"""M4 写入者普查 / 冲突检测。设计见 plan/03 §M4；口径单点在 data/README.md §4.8。

五节（plan/01 §二模块④）：
- `writers`    每张表 → 写入者（文件 + 语句序号 + 方言）
- `readers`    每张表 → 读取者（同形）
- `orphan`     **有读无写**（下游在用，本目录没人产出）
- `multi_writer` **同一张表被 ≥2 个语句写**（只看同表，不猜语义冲突）
- `write_only` **只写不读**（产出后无人使用）

口径（§4.8）：
- 写入者 = **有写目标表的语句**，取自 `build_edges` 填写的 `corpus.write_targets` 台账，
  **不从边集反推**——`INSERT INTO t VALUES (1)` 这类无来源列的写语句边集为空（`no_source_columns`
  是确定结果），从边反推会把写者漏掉，进而把 `write_only`/`orphan` 判反。
- 读者 = 语句里出现的表引用（`corpus.reads`），去掉 CTE 名与自身写目标；
  `unknown` 边 `source_table=None` 天然不计入，不靠边集过滤。
- 纯 DDL（无 SELECT 体的 `CREATE TABLE`）与纯 `SELECT` 不是写者；纯 `SELECT` 是读者。
- 排序（§4.6）：表名升序；表内条目按 `(file, statement_index)` 升序。不输出风险分/冲突概率。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Corpus


@dataclass(frozen=True)
class StatementRef:
    """普查条目：一条语句的身份（§4.8 要求 文件 + 语句序号 + 方言）。"""

    file: str
    index: int
    dialect: str

    def sort_key(self) -> tuple:
        return (self.file, self.index)

    def to_dict(self) -> dict:
        return {"file": self.file, "statement_index": self.index, "dialect": self.dialect}


@dataclass
class CensusReport:
    """五节普查结果。字典按表名升序构造（§4.6），JSON 键序因此固定。"""

    writers: dict = field(default_factory=dict)  # table -> [StatementRef]
    readers: dict = field(default_factory=dict)  # table -> [StatementRef]
    orphan: list = field(default_factory=list)  # 有读无写：table[]
    multi_writer: list = field(default_factory=list)  # [{table, writers[]}]
    write_only: list = field(default_factory=list)  # 只写不读：table[]
    edges_missing_writer: list = field(default_factory=list)  # 台账自检：有边但无写者（应为空）

    def to_dict(self) -> dict:
        return {
            "writers": {t: [r.to_dict() for r in refs] for t, refs in self.writers.items()},
            "readers": {t: [r.to_dict() for r in refs] for t, refs in self.readers.items()},
            "orphan": list(self.orphan),
            "multi_writer": [
                {"table": item["table"], "writers": [r.to_dict() for r in item["writers"]]}
                for item in self.multi_writer
            ],
            "write_only": list(self.write_only),
            "edges_missing_writer": list(self.edges_missing_writer),
        }


def _refs(by_table: dict, stmt, table: str) -> None:
    by_table.setdefault(table, []).append(
        StatementRef(file=stmt.file, index=stmt.index, dialect=stmt.dialect))


def census(corpus: Corpus, edges=None) -> CensusReport:
    """语料 + 语句台账 → 五节普查。

    `edges` 只用于台账自检（每条边的目标表必须登记过写者）；判定本身只读
    `corpus.write_targets` / `corpus.reads`，见模块文档。
    """
    writers: dict = {}
    readers: dict = {}

    # 按语句序列走（拓扑序），表内顺序随后再按 (file, index) 归一（§4.6）
    for stmt in corpus.statements:
        sid = stmt.statement_id
        table = corpus.write_targets.get(sid)
        if table:
            _refs(writers, stmt, table)
        for read_table in corpus.reads.get(sid, ()):
            _refs(readers, stmt, read_table)

    # §4.6 排序：表名升序；表内按 (file, statement_index) 升序
    report = CensusReport()
    report.writers = {
        t: sorted(refs, key=lambda r: r.sort_key())
        for t, refs in sorted(writers.items())
    }
    report.readers = {
        t: sorted(refs, key=lambda r: r.sort_key())
        for t, refs in sorted(readers.items())
    }

    report.orphan = sorted(t for t in report.readers if t not in report.writers)
    report.write_only = sorted(t for t in report.writers if t not in report.readers)
    report.multi_writer = [
        {"table": t, "writers": refs}
        for t, refs in report.writers.items()
        if len(refs) >= 2  # 单写入者零误报：严格 >=2
    ]

    if edges is not None:
        missing = sorted({e.target_table for e in edges if e.target_table not in report.writers})
        report.edges_missing_writer = missing
    return report


# ---------------------------------------------------------------- 输出

def render_markdown(report: CensusReport, version: str = "") -> str:
    """Markdown 报表（可直接贴 PR）。排序同 §4.6，不输出推断值。"""
    title = "# 写入者普查" + (f" · sqltrace {version}" if version else "")
    lines = [
        title,
        "",
        "> 事实报表，不含风险分/冲突概率。口径：`data/README.md` §4.8。",
        "",
        "## 摘要",
        "",
        "| 项 | 计数 |",
        "| --- | --- |",
        f"| 写入者语句 | {sum(len(v) for v in report.writers.values())} |",
        f"| 读者语句 | {sum(len(v) for v in report.readers.values())} |",
        f"| 有读无写（orphan） | {len(report.orphan)} |",
        f"| 多写冲突（multi_writer） | {len(report.multi_writer)} |",
        f"| 只写不读（write_only） | {len(report.write_only)} |",
        "",
        "## 写入者",
        "",
        "| 表 | 语句数 | 写入者 |",
        "| --- | --- | --- |",
    ]
    for table, refs in report.writers.items():
        who = "<br>".join(f"`{r.file}#{r.index}`（{r.dialect}）" for r in refs)
        lines.append(f"| `{table}` | {len(refs)} | {who} |")

    lines += ["", "## 读取者", "", "| 表 | 语句数 | 读取者 |", "| --- | --- | --- |"]
    for table, refs in report.readers.items():
        who = "<br>".join(f"`{r.file}#{r.index}`（{r.dialect}）" for r in refs)
        lines.append(f"| `{table}` | {len(refs)} | {who} |")

    lines += ["", "## 有读无写（orphan）", ""]
    if report.orphan:
        lines += ["| 表 | 读取者 |", "| --- | --- |"]
        for table in report.orphan:
            who = "<br>".join(f"`{r.file}#{r.index}`" for r in report.readers[table])
            lines.append(f"| `{table}` | {who} |")
    else:
        lines.append("（无）")

    lines += ["", "## 多写冲突（multi_writer）", ""]
    if report.multi_writer:
        lines += ["| 表 | 写入者数 | 写入者 |", "| --- | --- | --- |"]
        for item in report.multi_writer:
            who = "<br>".join(f"`{r.file}#{r.index}`" for r in item["writers"])
            lines.append(f"| `{item['table']}` | {len(item['writers'])} | {who} |")
    else:
        lines.append("（无）")

    lines += ["", "## 只写不读（write_only）", ""]
    if report.write_only:
        lines += ["| 表 | 写入者 |", "| --- | --- |"]
        for table in report.write_only:
            who = "<br>".join(f"`{r.file}#{r.index}`" for r in report.writers[table])
            lines.append(f"| `{table}` | {who} |")
    else:
        lines.append("（无）")
    return "\n".join(lines) + "\n"


def census_summary(report: CensusReport) -> str:
    """一行摘要（CLI 非 JSON 模式）。"""
    return (
        f"写者 {len(report.writers)} 张 / 读者 {len(report.readers)} 张 / "
        f"多写 {len(report.multi_writer)} / 孤儿 {len(report.orphan)} / "
        f"只写不读 {len(report.write_only)}"
    )
