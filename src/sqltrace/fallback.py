# -*- coding: utf-8 -*-
"""M3 降级策略引擎：每档构造一个 handler，返回"展开边"或"诊断 + reason code"。

设计见 plan/03 §M3；枚举与挂载点单点定义在 data/README.md §4.2（本文件不另立口径）。

出口：
- `resolve_merge(...)`：`MERGE` 逐分支解析（UPDATE / INSERT 产边；DELETE 与不支持形态记
  `skipped_merge_branch`）。核心里 `_target_of` 认不出 Merge，由 build_edges 显式路由到本函数。
- `reconcile_unknown_edges(...)`：§4.2 规则 5 的边↔诊断对账。
- `zero_silence_violations(...)`：§4.2 规则 4 的机械门——写语句必须"有边或有语句级诊断"。
- `assert_reason_codes(...)`：reason code 必须落在 §4.2 封闭枚举内。

依赖方向：core → fallback → model/constants。本模块**不 import core**（resolver 由调用方注入），
避免循环依赖。
"""
from __future__ import annotations

from sqlglot import exp

from .constants import EDGE_AND_DIAG_CODES, FILE_LEVEL_CODES, REASON_CODES
from .model import Diagnostic

# 语句级谓词口径与 M2 一致：MERGE 的 ON / WHEN 条件扇出到该语句产出的全部边（control）。
_ON_PREFIX = "MERGE ON "
_WHEN_PREFIX = "MERGE WHEN "


# ---------------------------------------------------------------- 关系登记（与 core 共用口径）

def add_relation(rels: dict, node) -> None:
    """把 USING 节点登记为 alias -> ('table', name) | ('select', node)。

    与 core._relations 的 add() 同口径：表名本身也可作限定名（`raw_a.x` 与 `a.x` 都解）；
    子查询只按别名登记（无别名则无法被限定，不编造）。
    """
    if isinstance(node, exp.Table):
        name = node.name
        alias = node.alias or name
        rels[alias] = ("table", name)
        if alias != name and name not in rels:
            rels[name] = ("table", name)
    elif isinstance(node, exp.Subquery):
        if node.alias:
            rels[node.alias] = ("select", node.this)
    elif isinstance(node, exp.Lateral):
        add_relation(rels, node.this)


# ---------------------------------------------------------------- MERGE

def _iter_set_pairs(update) -> list:
    """`UPDATE SET a = x, b = y` → [EQ, EQ]（sqlglot 把赋值存成 EQ 节点）。"""
    return [e for e in update.expressions if isinstance(e, exp.EQ)]


def _target_column_of(left, target_alias: str, target_table: str) -> str | None:
    """赋值左值 → 目标列名。限定名必须是目标表/别名，否则 SQL 本身写歪了（不猜）。"""
    if not isinstance(left, exp.Column):
        return None
    if left.table and left.table not in (target_alias, target_table):
        return None
    return left.name


def _branch_label(when) -> str:
    label = "MATCHED" if when.args.get("matched") else "NOT MATCHED"
    source = when.args.get("source")
    if source is not None:
        label += " BY SOURCE" if source else " BY TARGET"
    return label


def resolve_merge(resolver, root) -> None:
    """解析一条 MERGE 语句；边与诊断都写进 resolver 的收集器。

    resolver 需提供：`_diag(code, msg, approximate)`、`_classify(...)`、
    `_resolve_column(...)`、`add_edge(table, column, sources) -> int`。
    """
    table = root.this.name if isinstance(root.this, exp.Table) else None
    if not table:
        resolver._diag("skipped_merge_branch",
                       "MERGE target is not a plain table; statement skipped", True)
        return
    target_alias = root.this.alias or table

    rels: dict = {target_alias: ("table", table)}
    if target_alias != table:
        rels[table] = ("table", table)
    using = root.args.get("using")
    if using is not None:
        add_relation(rels, using)
    other_tables = {t for (kind, t) in rels.values() if kind == "table" and t != table}
    join_path = tuple(sorted({table, *other_tables})) if other_tables else ()

    # ---- 语句级 control：ON + 各 WHEN 条件（扇出到本语句所有边，口径同 M2）----
    controls: list = []
    on = root.args.get("on")
    if on is not None:
        controls.extend(_merge_controls(resolver, on, rels, target_alias, table,
                                        _ON_PREFIX, join_path))
    whens = root.args.get("whens")
    when_list = whens.expressions if whens else []
    for when in when_list:
        cond = when.args.get("condition")
        if cond is not None:
            controls.extend(_merge_controls(resolver, cond, rels, target_alias, table,
                                            _WHEN_PREFIX, join_path))

    # ---- 分支 ----
    for when in when_list:
        then = when.args.get("then")
        branch = _branch_label(when)
        if isinstance(then, exp.Update):
            _resolve_update_branch(resolver, then, table, target_alias,
                                   rels, controls, branch)
        elif isinstance(then, exp.Insert):
            _resolve_insert_branch(resolver, then, table, target_alias,
                                   rels, controls, branch)
        else:
            # DELETE 分支 / 形态不认识：列级边不存在，但必须留痕（零静默）
            resolver._diag(
                "skipped_merge_branch",
                f"MERGE branch `{branch}` yields no column-level edge: "
                f"{then.sql() if then is not None else 'empty'}",
                True,
            )


def _merge_controls(resolver, cond, rels, target_alias, table, prefix, join_path) -> list:
    """ON / WHEN 条件里的来源列 → control 来源。目标侧自引用不算上游（不产自环）。"""
    text = f"{prefix}{cond.sql()}"
    out: list = []
    for kind, col, agg, win, _t in resolver._classify(cond, "control", None, None, cond.sql()):
        if col.table in (target_alias, table):
            continue
        for s in resolver._resolve_column(col, "control", agg, win, text, rels, {}, 0):
            s.join_path = s.join_path or join_path
            out.append(s)
    return out


def _resolve_update_branch(resolver, update, table, target_alias, rels, controls, branch) -> None:
    for eq in _iter_set_pairs(update):
        tcol = _target_column_of(eq.this, target_alias, table)
        if tcol is None:
            resolver._diag("skipped_merge_branch",
                           f"MERGE `{branch}` assignment target unsupported: {eq.this.sql()}",
                           True)
            continue
        text = f"MERGE SET {tcol} = {eq.expression.sql()}"
        srcs: list = []
        for kind, col, agg, win, _t in resolver._classify(
                eq.expression, "value", None, None, eq.expression.sql()):
            srcs.extend(resolver._resolve_column(col, kind, agg, win, text, rels, {}, 0))
        resolver.add_edge(table, tcol, _with_join_path(srcs, table) + controls)


def _resolve_insert_branch(resolver, insert, table, target_alias, rels, controls, branch) -> None:
    """`INSERT (c1, c2) VALUES (s.a, s.b)`：按列清单位置映射；列数不符记 arity_mismatch。"""
    cols_node = insert.this
    vals_node = insert.expression
    if not isinstance(cols_node, exp.Tuple) or not isinstance(vals_node, exp.Tuple):
        resolver._diag("skipped_merge_branch",
                       f"MERGE `{branch}` insert without explicit column list; "
                       "target columns unknown, branch skipped", True)
        return
    cols = [c.name for c in cols_node.expressions]
    vals = list(vals_node.expressions)
    if len(cols) != len(vals):
        resolver._diag("arity_mismatch",
                       f"MERGE `{branch}` insert columns {len(cols)} != values {len(vals)}",
                       False)
        return
    for tcol, val in zip(cols, vals):
        text = f"MERGE INSERT {tcol} = {val.sql()}"
        srcs: list = []
        for kind, col, agg, win, _t in resolver._classify(
                val, "value", None, None, val.sql()):
            srcs.extend(resolver._resolve_column(col, kind, agg, win, text, rels, {}, 0))
        resolver.add_edge(table, tcol, _with_join_path(srcs, table) + controls)


def _with_join_path(srcs, table) -> list:
    for s in srcs:
        if s.table and not s.join_path:
            s.join_path = tuple(sorted({table, s.table}))
    return srcs


# ---------------------------------------------------------------- §4.2 规则 5：边↔诊断对账

def _split_sid(statement_id: str):
    if "#" not in statement_id:
        return None, None
    file, idx = statement_id.rsplit("#", 1)
    try:
        return file, int(idx)
    except ValueError:
        return None, None


def reconcile_unknown_edges(edges, diags) -> list:
    """每条 unknown 边都必须有同 `(file, statement_index, reason_code)` 的诊断（§4.2 规则 5）。

    返回补出来的诊断（调用方并入后重排）；不改动已有诊断。
    """
    have = {(d.file, d.statement_index, d.reason_code) for d in diags}
    added: list = []
    for e in edges:
        if e.kind != "unknown":
            continue
        file, idx = _split_sid(e.statement_id)
        if file is None:
            continue
        code = e.reason_code or "unknown_type"
        if (file, idx, code) in have:
            continue
        have.add((file, idx, code))
        added.append(Diagnostic(
            file=file, statement_index=idx, reason_code=code,
            message=f"unknown edge {e.target_table}.{e.target_column} "
                    f"({e.expr or 'n/a'}) carries reason code",
            approximate=True,
        ))
    return added


def diagnose_missing_edges(edges, diags) -> list:
    """§4.2 规则 5 反向：`边 + 诊断` 码若出现诊断，则同语句必须有该码的 unknown 边。

    返回违规（空 = 通过）。用于捕捉"诊断说有 unknown 但边没了"的不一致。
    """
    unknown = {(f, i, e.reason_code) for e in edges if e.kind == "unknown"
               for f, i in [_split_sid(e.statement_id)] if f is not None}
    bad = []
    for d in diags:
        if d.reason_code in EDGE_AND_DIAG_CODES:
            if (d.file, d.statement_index, d.reason_code) not in unknown:
                bad.append(f"{d.file}#{d.statement_index}:{d.reason_code}")
    return sorted(bad)


# ---------------------------------------------------------------- §4.2 规则 4：零静默机械门

def zero_silence_violations(write_ids, edges, diags) -> list:
    """写语句既无边也无**语句级**诊断 = 静默丢弃（返回违规列表，空 = 通过）。

    文件级诊断（如 `dialect_defaulted`）不构成某个语句的留痕，故不计入。
    纯 DDL（无 SELECT 体的 `CREATE TABLE`）不是血缘语句，由调用方排除在 write_ids 之外。
    """
    with_edges = {e.statement_id for e in edges}
    with_diags = {f"{d.file}#{d.statement_index}" for d in diags
                  if d.reason_code not in FILE_LEVEL_CODES}
    return sorted(sid for sid in write_ids if sid not in with_edges and sid not in with_diags)


def assert_reason_codes(edges, diags) -> list:
    """所有 reason code 必须落在 §4.2 封闭枚举内；返回未登记值（不应出现）。"""
    bad = {e.reason_code for e in edges if e.reason_code and e.reason_code not in REASON_CODES}
    bad |= {d.reason_code for d in diags if d.reason_code not in REASON_CODES}
    return sorted(bad)
