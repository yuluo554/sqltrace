# -*- coding: utf-8 -*-
"""数值口径常量 —— 唯一定义在 data/README.md §四；本文件只是代码侧引用点，不得另立口径。"""

# §4.5 方言列表（封闭集合）
DIALECTS = ("postgres", "snowflake", "bigquery", "tsql", "duckdb")
DEFAULT_DIALECT = "postgres"

# §4.2 reason code 枚举（封闭集合，新增需改 data/README.md §四）
REASON_CODES = (
    "unknown_wildcard",
    "positional_union",
    "arity_mismatch",
    "skipped_merge_branch",
    "UNSUPPORTED_DYNAMIC_SQL",
    "PARSE_ERROR",
    "recursion_limit",
    "cycle_detected",
    "unknown_type",
)

# §4.1 三类边（kind 取值）
EDGE_KINDS = ("value", "control", "unknown")

# §4.7 保护性上限
RECURSION_LIMIT = 16
MAX_STATEMENTS_PER_FILE = 2000
MAX_AST_NODES = 200000

# §4.4 退出码
EXIT_OK = 0
EXIT_REMOVED = 1
EXIT_NONBREAKING = 2
EXIT_USAGE = 3
EXIT_INTERNAL = 4
