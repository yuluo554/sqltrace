# -*- coding: utf-8 -*-
"""CLI 唯一入口：sqltrace 命令树（plan/01 纪律 5：单一入口，库 API 不作验收路径）。

M0 骨架：命令树与帮助可跑；各子命令为占位（M1–M5 落地）。
退出码口径 data/README.md §4.4。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .constants import DIALECTS, EXIT_OK, EXIT_USAGE
from .output import ensure_deterministic_stdio


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sqltrace",
        description="SQL 值/控制双通道血缘 + 写入者普查 + diff 闸门（纯本地，零网络）",
    )
    parser.add_argument("--version", action="version", version=f"sqltrace {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_lineage = sub.add_parser("lineage", help="列级血缘（M2）")
    p_lineage.add_argument("root", type=Path, help="SQL 语料目录")
    p_lineage.add_argument("--schema", type=Path, default=None, help="外部 DDL schema 覆盖")
    p_lineage.add_argument("--dialect", choices=DIALECTS, default=None)
    p_lineage.add_argument("--json", action="store_true", help="JSON 输出（稳定排序）")

    p_census = sub.add_parser("census", help="写入者普查（M4）")
    p_census.add_argument("root", type=Path)
    p_census.add_argument("--json", action="store_true")
    p_census.add_argument("--md", action="store_true", help="Markdown 报表")

    p_diff = sub.add_parser("diff", help="lineage diff 闸门（M5）")
    p_diff.add_argument("root", type=Path)
    p_diff.add_argument("--base", required=True, help="git ref 或第二个目录")
    p_diff.add_argument("--json", action="store_true")
    p_diff.add_argument("--md", action="store_true")

    p_impact = sub.add_parser("impact", help="反向影响查询（M5）")
    p_impact.add_argument("target", help="<table>.<column>，如 raw.cust.nm")
    p_impact.add_argument("root", type=Path)

    p_golden = sub.add_parser("golden", help="五条 golden 回归（M5）")
    p_golden.add_argument("path", type=Path, nargs="?", default=Path("data/golden"))

    return parser


def main(argv: list | None = None) -> int:
    ensure_deterministic_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE
    print(f"sqltrace {__version__}: 子命令 `{args.command}` 骨架就绪，实现于 M1–M5。")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
