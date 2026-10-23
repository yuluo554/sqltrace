# -*- coding: utf-8 -*-
"""数值口径常量 —— 唯一定义在 data/README.md §四；本文件只是代码侧引用点，不得另立口径。"""

# §4.5 方言列表（封闭集合）
DIALECTS = ("postgres", "snowflake", "bigquery", "tsql", "duckdb")
DEFAULT_DIALECT = "postgres"

# §4.2 reason code 枚举（封闭集合，新增需改 data/README.md §4.2）
REASON_CODES = (
    "unknown_wildcard",
    "unknown_type",
    "positional_union",
    "arity_mismatch",
    "skipped_merge_branch",
    "UNSUPPORTED_DYNAMIC_SQL",
    "PARSE_ERROR",
    "recursion_limit",
    "cycle_detected",
    "dialect_defaulted",
    "no_source_columns",
    "wildcard_expanded",
    "schema_overridden",
    "unsupported_stored_procedure",
    "unsupported_write_statement",
)

# §4.2 挂载点：既落边（kind=unknown）又落诊断的码
EDGE_AND_DIAG_CODES = ("unknown_wildcard", "unknown_type")

# §4.2 文件级诊断码：不属于某条语句的血缘留痕（零静默门不认它）
FILE_LEVEL_CODES = ("dialect_defaulted", "schema_overridden")

# §4.2 正常路径码（非降级）：出现它不表示能力缺失
INFO_CODES = ("wildcard_expanded", "schema_overridden")

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
