# -*- coding: utf-8 -*-
"""共享数据结构（M1–M5 共用）。字段口径见 data/README.md §四。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Edge:
    """一条列级血缘边。排序键 = (target_table, target_column, kind, source_table, source_column, expr)（§4.6）。"""

    target_table: str
    target_column: str
    kind: str  # value / control / unknown（§4.1）
    source_table: Optional[str]
    source_column: Optional[str]
    expr: str
    join_path: tuple = ()
    aggregation: Optional[str] = None
    window: Optional[str] = None
    statement_id: str = ""
    reason_code: Optional[str] = None  # 仅 unknown/降级时（§4.2）
    approximate: bool = False

    def sort_key(self) -> tuple:
        return (
            self.target_table,
            self.target_column,
            self.kind,
            self.source_table or "",
            self.source_column or "",
            self.expr,
        )


@dataclass
class Statement:
    """语料中的一条语句（拓扑排序后）。"""

    file: str  # 相对语料根目录，分隔符统一 /（§4.6）
    index: int  # 文件内语句序号，从 0 起
    sql: str
    dialect: str

    @property
    def statement_id(self) -> str:
        return f"{self.file}#{self.index}"


@dataclass
class Diagnostic:
    """诊断项。排序键 = (file, statement_index, reason_code, message)（§4.6）。"""

    file: str
    statement_index: int
    reason_code: str
    message: str
    approximate: bool = False

    def sort_key(self) -> tuple:
        return (self.file, self.statement_index, self.reason_code, self.message)


@dataclass
class Corpus:
    """M1 产出：文件清单 + 拓扑语句序列 + 推导 schema。"""

    files: list = field(default_factory=list)  # [{path, sha256, dialect}]
    ignored: list = field(default_factory=list)  # [{path, reason}]
    statements: list = field(default_factory=list)  # Statement[]（拓扑序）
    schemas: dict = field(default_factory=dict)  # table -> {column: type_or_unknown}
    diagnostics: list = field(default_factory=list)  # Diagnostic[]
