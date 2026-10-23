# -*- coding: utf-8 -*-
"""CLI 唯一入口：sqltrace 命令树（plan/01 纪律 5：单一入口，库 API 不作验收路径）。

M1 装载 + M2 血缘内核：lineage --json 输出装载清单与血缘边；其余子命令占位（M3–M5 落地）。
退出码口径 data/README.md §4.4。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .census import census, census_summary, render_markdown
from .constants import DIALECTS, EXIT_INTERNAL, EXIT_OK, EXIT_USAGE
from .core import build_edges
from .diffgate import (
    BaseUsageError,
    gate_check,
    diff_edges,
    diff_exit_code,
    diff_payload,
    diff_summary,
    golden_to_dict,
    impact,
    load_base,
    render_diff_markdown,
    render_golden_text,
    render_impact_text,
    run_golden,
)
from .fallback import assert_reason_codes, zero_silence_violations
from .loader import load_corpus
from .output import dumps_json, ensure_deterministic_stdio, silence_library_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sqltrace",
        description="SQL 值/控制双通道血缘 + 写入者普查 + diff 闸门（纯本地，零网络）",
    )
    parser.add_argument("--version", action="version", version=f"sqltrace {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_lineage = sub.add_parser("lineage", help="列级血缘（M1 装载清单 / M2 起血缘边）")
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
    p_diff.add_argument("--dialect", choices=DIALECTS, default=None)
    p_diff.add_argument("--json", action="store_true")
    p_diff.add_argument("--md", action="store_true")

    p_impact = sub.add_parser("impact", help="反向影响查询（M5）")
    p_impact.add_argument("target", help="<table>.<column>，如 raw_cust.nm")
    p_impact.add_argument("root", type=Path, help="SQL 语料目录")
    p_impact.add_argument("--dialect", choices=DIALECTS, default=None)
    p_impact.add_argument("--json", action="store_true")

    p_golden = sub.add_parser("golden", help="五条 golden 回归（M5）")
    p_golden.add_argument("path", type=Path, nargs="?", default=Path("data/golden"))
    p_golden.add_argument("--dialect", choices=DIALECTS, default=None)
    p_golden.add_argument("--json", action="store_true")

    return parser


def _load_or_exit(args) -> object | None:
    root = Path(args.root)
    if not root.is_dir():
        print(f"sqltrace: 语料目录不存在: {root}", file=sys.stderr)
        return None
    return load_corpus(root, getattr(args, "schema", None), getattr(args, "dialect", None))


def _all_diags(corpus, edge_diags) -> list:
    """装载期 + 内核期诊断合并（§4.6 排序键），供输出与零静默门共用。"""
    return sorted(list(corpus.diagnostics) + list(edge_diags),
                  key=lambda d: d.sort_key())


def main(argv: list | None = None) -> int:
    ensure_deterministic_stdio()
    silence_library_logging()  # D5：库噪声与自家诊断分栏（stderr 只留 sqltrace: 前缀）
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE

    if args.command == "lineage":
        corpus = _load_or_exit(args)
        if corpus is None:
            return EXIT_USAGE
        edges, edge_diags = build_edges(corpus)
        diags = _all_diags(corpus, edge_diags)

        # §4.2 规则 4：零静默机械门（写语句必须"有边或有语句级诊断"）
        silent = zero_silence_violations(corpus.write_ids, edges, diags)
        # §4.2 封闭枚举：任何未登记的 reason code 即缺陷
        unknown_codes = assert_reason_codes(edges, diags)

        if args.json:
            payload = {
                "version": __version__,
                "files": corpus.files,
                "ignored": corpus.ignored,
                "statements": [
                    {"file": s.file, "index": s.index, "dialect": s.dialect}
                    for s in corpus.statements
                ],
                "schemas": {t: c for t, c in sorted(corpus.schemas.items())},
                "diagnostics": [
                    {
                        "file": d.file,
                        "statement_index": d.statement_index,
                        "reason_code": d.reason_code,
                        "message": d.message,
                        "approximate": d.approximate,
                    }
                    for d in diags
                ],
                "edges": [
                    {
                        "target": f"{e.target_table}.{e.target_column}",
                        "source": (f"{e.source_table}.{e.source_column}"
                                   if e.source_table else None),
                        "kind": e.kind,
                        "expr": e.expr,
                        "statement_id": e.statement_id,
                        "aggregation": e.aggregation,
                        "window": e.window,
                        "join_path": list(e.join_path),
                        "reason_code": e.reason_code,
                        "approximate": e.approximate,
                    }
                    for e in edges
                ],
                "zero_silence": {
                    "passed": not silent and not unknown_codes,
                    "silent_statements": silent,
                    "unregistered_reason_codes": unknown_codes,
                },
            }
            sys.stdout.write(dumps_json(payload))
            return _gate_exit(silent, unknown_codes)

        by_kind = {"value": 0, "control": 0, "unknown": 0}
        for e in edges:
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        print(
            f"sqltrace {__version__}: 装载 {len(corpus.files)} 个文件 / "
            f"{len(corpus.statements)} 条语句 / {len(corpus.schemas)} 张表 schema / "
            f"血缘边 {len(edges)} 条（value {by_kind['value']} / control {by_kind['control']} / "
            f"unknown {by_kind['unknown']}）/ {len(diags)} 条诊断。"
        )
        if silent:
            for sid in silent:
                print(f"sqltrace: 零静默门 FAIL：写语句无边也无诊断 {sid}", file=sys.stderr)
        if unknown_codes:
            print(f"sqltrace: reason code 未登记（§4.2）：{', '.join(unknown_codes)}",
                  file=sys.stderr)
        return _gate_exit(silent, unknown_codes)

    if args.command == "census":
        corpus = _load_or_exit(args)
        if corpus is None:
            return EXIT_USAGE
        edges, edge_diags = build_edges(corpus)
        diags = _all_diags(corpus, edge_diags)

        # M4：复用 M3 的同一份门（§4.2 规则 4 / §4.8 规则 7）——census 与 lineage 不得各判一套
        silent = zero_silence_violations(corpus.write_ids, edges, diags)
        unknown_codes = assert_reason_codes(edges, diags)
        report = census(corpus, edges)
        # §4.8 规则 8：边集目标必须登记过写者（台账↔边集一致性）
        orphan_edges = report.edges_missing_writer

        if args.json:
            payload = {
                "version": __version__,
                "census": report.to_dict(),
                "zero_silence": {
                    "passed": not silent and not unknown_codes and not orphan_edges,
                    "silent_statements": silent,
                    "unregistered_reason_codes": unknown_codes,
                    "edges_missing_writer": orphan_edges,
                },
            }
            sys.stdout.write(dumps_json(payload))
        elif args.md:
            print(render_markdown(report, __version__), end="")
        else:
            print(f"sqltrace {__version__}: 写入者普查 · {census_summary(report)}。")

        for sid in silent:
            print(f"sqltrace: 零静默门 FAIL：写语句无边也无诊断 {sid}", file=sys.stderr)
        if unknown_codes:
            print(f"sqltrace: reason code 未登记（§4.2）：{', '.join(unknown_codes)}",
                  file=sys.stderr)
        for table in orphan_edges:
            print(f"sqltrace: 台账不一致（§4.8）：表 {table} 有边但无写者", file=sys.stderr)
        return EXIT_INTERNAL if (silent or unknown_codes or orphan_edges) else EXIT_OK

    if args.command == "diff":
        root = Path(args.root)
        if not root.is_dir():
            print(f"sqltrace: 语料目录不存在: {root}", file=sys.stderr)
            return EXIT_USAGE
        try:
            base_corpus, base_kind = load_base(root, args.base, args.dialect)
        except BaseUsageError as exc:
            print(f"sqltrace: {exc}", file=sys.stderr)
            return EXIT_USAGE

        cur_corpus = load_corpus(root, None, args.dialect)
        base_edges, base_diags = build_edges(base_corpus)
        cur_edges, cur_diags = build_edges(cur_corpus)

        # 门复用（K10/K13）：基线 + 当前各跑同一份零静默门与枚举守卫，不得各判一套
        base_gate = gate_check(base_corpus, base_edges, base_diags)
        cur_gate = gate_check(cur_corpus, cur_edges, cur_diags)

        changes = diff_edges(base_edges, cur_edges)
        payload = diff_payload(__version__, base_corpus, base_kind, args.base,
                               cur_corpus, str(args.root), changes, base_gate, cur_gate)

        if args.json:
            sys.stdout.write(dumps_json(payload))
        elif args.md:
            print(render_diff_markdown(payload, __version__), end="")
        else:
            print(f"sqltrace {__version__}: 血缘 diff · {diff_summary(payload)}。")

        gate_ok = base_gate[0] and cur_gate[0]
        for label, gate in (("基线", base_gate), ("当前", cur_gate)):
            if not gate[0]:
                print(f"sqltrace: {label}语料门 FAIL：{gate[1]}", file=sys.stderr)
        if not gate_ok:  # §4.4：内部一致性门失败 = 缺陷 → 4，不掩盖成 diff 语义码
            return EXIT_INTERNAL
        return diff_exit_code(changes)

    if args.command == "impact":
        root = Path(args.root)
        if not root.is_dir():
            print(f"sqltrace: 语料目录不存在: {root}", file=sys.stderr)
            return EXIT_USAGE
        corpus = load_corpus(root, None, args.dialect)
        edges, edge_diags = build_edges(corpus)
        diags = _all_diags(corpus, edge_diags)

        silent = zero_silence_violations(corpus.write_ids, edges, diags)
        unknown_codes = assert_reason_codes(edges, diags)
        try:
            report = impact(corpus, edges, args.target)
        except BaseUsageError as exc:
            print(f"sqltrace: {exc}", file=sys.stderr)
            return EXIT_USAGE

        if args.json:
            payload = {
                "version": __version__,
                "impact": report,
                "zero_silence": {
                    "passed": not silent and not unknown_codes,
                    "silent_statements": silent,
                    "unregistered_reason_codes": unknown_codes,
                },
            }
            sys.stdout.write(dumps_json(payload))
        else:
            print(render_impact_text(report, __version__), end="")
        return _gate_exit(silent, unknown_codes)

    if args.command == "golden":
        path = Path(args.path)
        if not path.is_dir():
            print(f"sqltrace: golden 目录不存在: {path}", file=sys.stderr)
            return EXIT_USAGE
        results, code = run_golden(path, args.dialect)
        if not results:
            print(f"sqltrace: `{path}` 下没有含 expected.json 的 golden", file=sys.stderr)
            return code
        if args.json:
            body = {"version": __version__}
            body.update(golden_to_dict(results))
            body["exit_code"] = code
            sys.stdout.write(dumps_json(body))
        else:
            print(render_golden_text(results, __version__), end="")
        for r in results:
            for name, detail in r.failures():
                print(f"sqltrace: golden `{r.name}` {name} FAIL：{detail}", file=sys.stderr)
        return code

    print(f"sqltrace {__version__}: 子命令 `{args.command}` 骨架就绪，实现于 M5。")
    return EXIT_OK


def _gate_exit(silent, unknown_codes) -> int:
    """内部一致性门失败 = 缺陷 → 退出码 4（§4.4），不随成功路径返回 0。"""
    return EXIT_INTERNAL if (silent or unknown_codes) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
