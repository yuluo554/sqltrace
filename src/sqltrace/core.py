# -*- coding: utf-8 -*-
"""M2 确定性列血缘内核。设计见 plan/03 §M2；口径 data/README.md §4.1。

- sqlglot AST + 自研 scope walker；**不调用** sqlglot `lineage()`/`qualify()`（D5/K5）。
- 判定顺序（§4.1）：AST 定不了 → unknown + reason code；再分 value / control。
- 窗口强制口径：`SUM(x) OVER (PARTITION BY k ORDER BY t)` → (w,value,x) + (w,control,k) + (w,control,t)。
- CTE / 子查询按输出列逐层回溯到基表（标注口径：source 落到最底层表.列）。
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from . import fallback
from .constants import MAX_AST_NODES, RECURSION_LIMIT
from .model import Corpus, Diagnostic, Edge

_DIALECT_MAP = {
    "postgres": "postgres",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "tsql": "tsql",
    "duckdb": "duckdb",
}


# ---------------------------------------------------------------- 小工具

def _clean_sql(node) -> str:
    """表达式文本（去掉 sqlglot 补的 NULLS FIRST/LAST，保持原 SQL 观感）。"""
    return (
        node.sql()
        .replace(" NULLS FIRST", "")
        .replace(" NULLS LAST", "")
        .strip()
    )


def _is_star(e) -> bool:
    if isinstance(e, exp.Star):
        return True
    return isinstance(e, exp.Column) and isinstance(e.this, exp.Star)


class _Source:
    """一个来源（列级），kind ∈ value/control/unknown。"""

    __slots__ = ("kind", "table", "column", "expr", "aggregation", "window", "join_path", "reason")

    def __init__(self, kind, table, column, expr, aggregation=None, window=None,
                 join_path=(), reason=None):
        self.kind = kind
        self.table = table
        self.column = column
        self.expr = expr
        self.aggregation = aggregation
        self.window = window
        self.join_path = join_path
        self.reason = reason


class _Resolver:
    """一条语句内的作用域解析器：关系别名 + CTE 链 + 输出列回溯。"""

    def __init__(self, corpus: Corpus, statement):
        self.corpus = corpus
        self.statement = statement
        self.diags: list[Diagnostic] = []
        self.edges: list[Edge] = []
        self._outputs_cache: dict = {}
        self._truncated: set = set()  # 触发 recursion_limit 的 select 节点
        self._in_progress: set = set()  # 正在展开的 select（自引用检测）
        self.output_count = 0  # 本语句解析出的输出列数（no_source_columns 诊断用）

    # ---- 诊断 ----
    def _diag(self, code: str, message: str, approximate: bool = False) -> None:
        self.diags.append(Diagnostic(
            file=self.statement.file,
            statement_index=self.statement.index,
            reason_code=code,
            message=message,
            approximate=approximate,
        ))

    # ---- 边 ----
    def add_edge(self, target_table: str, target_column: str, sources) -> int:
        """把一组来源落到 (target_table, target_column)；返回落的边数（MERGE 分支用）。"""
        n = 0
        for s in sources:
            if s.table is None and s.kind != "unknown":
                s.kind = "unknown"
                s.reason = s.reason or "unknown_type"
            self.edges.append(Edge(
                target_table=target_table,
                target_column=target_column,
                kind=s.kind,
                source_table=s.table,
                source_column=s.column,
                expr=s.expr,
                join_path=s.join_path,
                aggregation=s.aggregation,
                window=s.window,
                statement_id=self.statement.statement_id,
                reason_code=s.reason,
                approximate=s.kind == "unknown",
            ))
            n += 1
        return n

    # ---- 关系收集 ----
    def _relations(self, select, scope: dict) -> dict:
        """alias -> ('table', name) | ('select', node)。保持 FROM → JOIN 顺序。"""
        rels: dict = {}

        def add(node, force_alias=None):
            if isinstance(node, exp.Table):
                name = node.name
                alias = force_alias or node.alias or name
                rels[alias] = ("table", name)
                if alias != name and name not in rels:
                    rels[name] = ("table", name)  # 允许用裸表名限定
            elif isinstance(node, exp.Subquery):
                alias = force_alias or node.alias
                if alias:
                    rels[alias] = ("select", node.this)
            elif isinstance(node, exp.Lateral):
                add(node.this, force_alias or node.alias)

        frm = select.args.get("from_")
        if frm is None:
            frm = select.args.get("from")
        if frm is not None:
            add(frm.this)
            for extra in frm.expressions:
                add(extra)
        for j in select.args.get("joins") or []:
            add(j.this)
        # CTE 名当表引用（FROM agg / JOIN cte）
        for alias, (kind, node) in list(rels.items()):
            if kind == "table" and node in scope:
                rels[alias] = ("select", scope[node])
        return rels

    def _cte_scope(self, select, parent: dict) -> dict:
        scope = dict(parent)
        with_ = select.args.get("with_")
        if with_ is None:
            with_ = select.args.get("with")
        if with_ is not None:
            for cte in with_.expressions:
                if isinstance(cte, exp.CTE) and cte.alias:
                    scope[cte.alias] = cte.this
        return scope

    # ---- SELECT 输出 ----
    def resolve_select(self, select, scope: dict, depth: int = 0):
        """返回 [{'name': str|None, 'sources': [_Source]}]（顺序 = 输出列顺序）。"""
        key = id(select)
        if key in self._outputs_cache:
            if key in self._in_progress:
                # 自引用 CTE / 子查询：展开不收敛，按 §4.2 recursion_limit 降级（不静默）
                self._truncate(key, f"self-referencing CTE/subquery at `{_clean_sql(select)[:60]}`")
            return self._outputs_cache[key]
        if depth > RECURSION_LIMIT:
            self._truncate(key, f"CTE/subquery expansion depth > {RECURSION_LIMIT}")
            return []
        outputs: list = []
        self._outputs_cache[key] = outputs  # 防环（自引用 CTE）
        self._in_progress.add(key)

        if isinstance(select, (exp.Union, exp.Intersect, exp.Except)):
            self._resolve_setop(select, scope, depth, outputs)
            self._in_progress.discard(key)
            return outputs

        if not isinstance(select, exp.Select):
            self._in_progress.discard(key)
            return outputs

        local_scope = self._cte_scope(select, scope)
        rels = self._relations(select, local_scope)

        for proj in select.expressions:
            outputs.extend(self._resolve_projection(proj, rels, local_scope, depth, select))

        # ---- SELECT 级 control（WHERE/JOIN/GROUP BY/HAVING/QUALIFY）----
        controls = self._select_controls(select, rels, local_scope, depth)
        if controls:
            for out in outputs:
                out["sources"].extend(controls)
        self._in_progress.discard(key)
        return outputs

    def _truncate(self, key, message: str) -> None:
        """深度/自引用截断只留一条诊断（同一节点重复访问不重复计数）。"""
        if key in self._truncated:
            return
        self._truncated.add(key)
        self._diag("recursion_limit", message, True)

    def _resolve_setop(self, node, scope: dict, depth: int, outputs: list, branch_index: int = 0) -> None:
        """UNION/INTERSECT/EXCEPT：逐分支解析，按位置对齐；别名不一致记 positional_union。"""
        left = node.this
        right = node.expression
        left_outs = self._resolve_branch(left, scope, depth)
        right_outs = self._resolve_branch(right, scope, depth)

        if not outputs:
            for i, lo in enumerate(left_outs):
                outputs.append({"name": lo["name"], "sources": list(lo["sources"])})
        # 右侧按位置并入
        if len(left_outs) != len(right_outs):
            self._diag(
                "positional_union",
                f"UNION branches have {len(left_outs)} vs {len(right_outs)} output columns; positional merge",
                True,
            )
        for i, ro in enumerate(right_outs):
            if i >= len(outputs):
                outputs.append({"name": ro["name"], "sources": list(ro["sources"])})
                continue
            if ro["name"] and outputs[i]["name"] and ro["name"] != outputs[i]["name"]:
                self._diag(
                    "positional_union",
                    f"UNION alias mismatch at column {i}: {outputs[i]['name']} vs {ro['name']}; positional merge",
                    True,
                )
            outputs[i]["sources"].extend(ro["sources"])

    def _resolve_branch(self, node, scope: dict, depth: int):
        if isinstance(node, (exp.Union, exp.Intersect, exp.Except)):
            outs: list = []
            self._resolve_setop(node, scope, depth, outs)
            return outs
        if isinstance(node, exp.Subquery):
            return self.resolve_select(node.this, scope, depth + 1)
        if isinstance(node, exp.Select):
            return self.resolve_select(node, scope, depth + 1)
        return []

    def _resolve_projection(self, proj, rels: dict, scope: dict, depth: int, select):
        """单个 SELECT 列表项 → [{'name','sources'}]（star 可能展开成多列）。"""
        if _is_star(proj):
            return self._expand_star(proj, rels, scope, depth)

        if isinstance(proj, exp.Alias):
            name = proj.alias
            body = proj.this
        elif isinstance(proj, exp.Column):
            name = proj.name
            body = proj
        else:
            name = proj.alias_or_name or None
            body = proj

        if name in (None, ""):
            # 无别名的复杂表达式：不编造列名（schema 推导纪律）
            return []

        expr_text = _clean_sql(proj if not isinstance(proj, exp.Alias) else proj.this)
        raw = self._classify(body, "value", None, None, expr_text)

        sources: list = []
        for kind, col, agg, win, text in raw:
            sources.extend(self._resolve_column(
                col, kind, agg, win, text, rels, scope, depth))

        # COUNT(*) / COUNT(1)：无列参数 → 由 GROUP BY 键承担 control（行选择口径）
        if not raw and isinstance(body, exp.Count) and isinstance(body.this, exp.Star):
            for gkind, gcol, gagg, gwin, gtext in self._group_columns(select):
                for s in self._resolve_column(gcol, "control", "COUNT", gwin,
                                              expr_text, rels, scope, depth):
                    sources.append(s)

        return [{"name": name, "sources": sources}]

    def _expand_star(self, proj, rels: dict, scope: dict, depth: int):
        table = proj.table if isinstance(proj, exp.Column) else ""
        candidates = [rels[table]] if table and table in rels else list(rels.values())
        outs: list = []
        for kind, node in candidates:
            if kind == "table":
                schema = self.corpus.schemas.get(node)
                if schema:
                    # 正常路径（plan/01 §二模块③）：schema 已知 → 展开，并留一条 info 诊断
                    self._diag(
                        "wildcard_expanded",
                        f"SELECT * expanded to {len(schema)} column(s) of `{node}`",
                    )
                    for col in schema:
                        outs.append({
                            "name": col,
                            "sources": [_Source("value", node, col, f"{node}.{col}")],
                        })
                else:
                    outs.append({
                        "name": None,
                        "sources": [_Source(
                            "unknown", None, None, "*", reason="unknown_wildcard")],
                    })
            else:  # 子查询/CTE
                inner = self.resolve_select(node, scope, depth + 1)
                for io in inner:
                    outs.append({"name": io["name"], "sources": list(io["sources"])})
        return outs

    # ---- 表达式分类（§4.1 判定顺序）----

    def _classify(self, e, kind: str, agg, win, text: str):
        """返回 [(kind, Column, aggregation, window, expr_text)]。"""
        out: list = []
        if isinstance(e, exp.Window):
            fname = e.this.sql_name() if hasattr(e.this, "sql_name") else None
            if fname:
                win = fname
            wtext = _clean_sql(e)
            # 值参数（SUM(x) 的 x）
            for arg in e.this.iter_expressions():
                out.extend(self._classify(arg, "value", fname, win, wtext))
            # PARTITION BY / ORDER BY → control（强制口径，禁止归 value）
            for p in e.args.get("partition_by") or []:
                out.extend(self._classify(p, "control", None, win, f"PARTITION BY {_clean_sql(p)}"))
            order = e.args.get("order")
            if order is not None:
                for o in order.expressions:
                    suffix = " DESC" if o.args.get("desc") else ""
                    out.extend(self._classify(
                        o.this, "control", None, win,
                        f"ORDER BY {_clean_sql(o.this)}{suffix}",
                    ))
            return out
            fname = e.this.sql_name() if hasattr(e.this, "sql_name") else None
            if fname:
                win = fname
            wtext = _clean_sql(e)
            # 值参数（SUM(x) 的 x）
            for arg in e.this.iter_expressions():
                out.extend(self._classify(arg, "value", fname, win, wtext))
            # PARTITION BY / ORDER BY → control（强制口径，禁止归 value）
            for p in e.args.get("partition_by") or []:
                out.extend(self._classify(p, "control", None, win, f"PARTITION BY {_clean_sql(p)}"))
            order = e.args.get("order")
            if order is not None:
                for o in order.expressions:
                    suffix = " DESC" if o.args.get("desc") else ""
                    out.extend(self._classify(
                        o.this, "control", None, win,
                        f"ORDER BY {_clean_sql(o.this)}{suffix}",
                    ))
            return out

        if isinstance(e, exp.Case):
            ctext = _clean_sql(e)
            value_has_column = False
            branch_raw: list = []
            cond_raw: list = []
            for cond in e.args.get("ifs") or []:
                cond_raw.extend(self._classify(
                    cond.this, "control", None, win, f"CASE WHEN {_clean_sql(cond.this)}"))
                true = cond.args.get("true")
                if true is not None:
                    got = self._classify(true, "value", None, win, ctext)
                    if got:
                        value_has_column = True
                    branch_raw.extend(got)
            default = e.args.get("default")
            if default is not None:
                got = self._classify(default, "value", None, win, ctext)
                if got:
                    value_has_column = True
                branch_raw.extend(got)
            out.extend(branch_raw)
            if not value_has_column:
                # 分支全为常量：取值完全由谓词决定 → 谓词列同时记 value（标注口径）
                out.extend(("value", c, a, w, ctext) for (k, c, a, w, _t) in cond_raw)
            out.extend(cond_raw)
            return out

        if isinstance(e, exp.AggFunc):
            atext = _clean_sql(e)
            aname = e.sql_name() if hasattr(e, "sql_name") else None
            for arg in e.iter_expressions():
                if isinstance(arg, exp.Star):
                    continue
                out.extend(self._classify(arg, "value", aname, win, atext))
            return out

        if isinstance(e, exp.Column):
            out.append((kind, e, agg, win, text))
            return out

        for child in e.iter_expressions():
            out.extend(self._classify(child, kind, agg, win, text))
        return out

    def _resolve_column(self, col, kind: str, agg, win, text: str,
                        rels: dict, scope: dict, depth: int):
        """列引用 → 基表来源（穿透 CTE/子查询）。"""
        qualifier = col.table
        name = col.name
        if qualifier:
            rel = rels.get(qualifier)
            if rel is None and qualifier in scope:
                rel = ("select", scope[qualifier])
            if rel is None:
                self._diag("unknown_type",
                           f"unresolved qualifier `{qualifier}` in `{_clean_sql(col)}`", True)
                return [_Source("unknown", None, None, text, agg, win, reason="unknown_type")]
            return self._sources_from_rel(rel, name, kind, agg, win, text, rels, scope, depth)

        for rel in rels.values():
            srcs = self._sources_from_rel(rel, name, kind, agg, win, text, rels, scope, depth,
                                          probe=True)
            if srcs is not None:
                return srcs
        # 派生 schema 是近似（CTAS/函数列可能缺列）：只有单表时按该表兜底，不编造来源表
        tables = [rel for rel in rels.values() if rel[0] == "table"]
        if len(tables) == 1:
            return self._sources_from_rel(tables[0], name, kind, agg, win, text,
                                          rels, scope, depth, probe=False)
        self._diag("unknown_type", f"unresolved column `{_clean_sql(col)}`", True)
        return [_Source("unknown", None, None, text, agg, win, reason="unknown_type")]

    def _sources_from_rel(self, rel, name, kind, agg, win, text, rels, scope, depth, probe=False):
        rkind, node = rel
        if rkind == "table":
            schema = self.corpus.schemas.get(node)
            if schema is not None and name not in schema:
                return None if probe else [
                    _Source("unknown", None, None, text, agg, win, reason="unknown_type")]
            return [_Source(kind, node, name, text, agg, win)]
        inner = self.resolve_select(node, scope, depth + 1)
        for io in inner:
            if io["name"] == name:
                out = []
                for s in io["sources"]:
                    if s.kind == "unknown":
                        out.append(s)
                    elif s.kind == "control":
                        # 内层谓词/分组上下文保留原 expr（如 "GROUP BY dt"）；
                        # 内层 control 穿透外层时不得被升为 value（K1 判定顺序）
                        out.append(_Source("control", s.table, s.column, s.expr,
                                           s.aggregation, s.window, s.join_path))
                    else:
                        # 内层 value 穿透：沿用外层判定 kind（ORDER BY 键→control 等）
                        out.append(_Source(kind, s.table, s.column, text,
                                           s.aggregation, s.window, s.join_path))
                return out
        return None if probe else [
            _Source("unknown", None, None, text, agg, win, reason="unknown_type")]

    # ---- SELECT 级 control ----

    def _group_columns(self, select):
        grp = select.args.get("group") if isinstance(select, exp.Select) else None
        if grp is None:
            return []
        out = []
        for g in grp.expressions:
            out.extend(self._classify(g, "control", None, None, _clean_sql(g)))
        return out

    def _resolve_raw(self, raw, rels, scope, depth, expr_text, join_path=()):
        srcs: list = []
        for kind, col, agg, win, _text in raw:
            # expr 口径：谓词级调用方传入带前缀文本（WHERE/JOIN/GROUP BY/…）
            for s in self._resolve_column(col, kind, agg, win, expr_text, rels, scope, depth):
                if s.kind != "unknown":
                    s.join_path = join_path or s.join_path
                srcs.append(s)
        return srcs

    def _select_controls(self, select, rels, scope, depth) -> list:
        controls: list = []

        where = select.args.get("where")
        if where is not None:
            raw = self._classify(where.this, "control", None, None, _clean_sql(where.this))
            controls.extend(self._resolve_raw(raw, rels, scope, depth,
                                              f"WHERE {_clean_sql(where.this)}"))

        for j in select.args.get("joins") or []:
            on = j.args.get("on")
            using = j.args.get("using")
            if on is not None:
                raw = self._classify(on, "control", None, None, _clean_sql(on))
                jp = tuple(sorted({s.table for s in self._resolve_raw(raw, rels, scope, depth, "", ()) if s.table}))
                controls.extend(self._resolve_raw(raw, rels, scope, depth,
                                                  f"JOIN {_clean_sql(on)}", jp))
            elif using:
                for u in using:
                    uname = u.name if hasattr(u, "name") else str(u)
                    for rel in rels.values():
                        if rel[0] == "table":
                            controls.append(_Source("control", rel[1], uname,
                                                    f"JOIN USING ({uname})"))
                    break

        grp = select.args.get("group")
        if grp is not None:
            for g in grp.expressions:
                raw = self._classify(g, "control", None, None, _clean_sql(g))
                controls.extend(self._resolve_raw(raw, rels, scope, depth,
                                                  f"GROUP BY {_clean_sql(g)}"))

        having = select.args.get("having")
        if having is not None:
            htext = f"HAVING {_clean_sql(having.this)}"
            raw = self._classify(having.this, "control", None, None, _clean_sql(having.this))
            srcs = self._resolve_raw(raw, rels, scope, depth, htext)
            if not srcs:  # HAVING COUNT(*) 等纯行数谓词 → 行由 GROUP BY 键决定
                srcs = self._resolve_raw(self._group_columns(select), rels, scope, depth, htext)
            controls.extend(srcs)

        qualify = select.args.get("qualify")
        if qualify is not None:
            qtext = f"QUALIFY {_clean_sql(qualify.this)}"
            raw = self._classify(qualify.this, "control", None, None, _clean_sql(qualify.this))
            controls.extend(self._resolve_raw(raw, rels, scope, depth, qtext))

        return controls


# ---------------------------------------------------------------- 目标表识别

def _target_of(root, corpus: Corpus):
    """返回 (target_table, target_columns|None, select_node) 或 None（非写语句）。"""
    if isinstance(root, exp.Insert):
        this = root.this
        cols = None
        if isinstance(this, exp.Schema):
            cols = [c.name for c in this.expressions]
            table = this.this.name if isinstance(this.this, exp.Table) else None
        else:
            table = this.name if isinstance(this, exp.Table) else None
        select = root.expression
        return table, cols, select

    if isinstance(root, exp.Create):
        kind = (root.args.get("kind") or "").upper()
        this = root.this
        cols = None
        if isinstance(this, exp.Schema):
            cols = [c.name for c in this.expressions]
            table = this.this.name if isinstance(this.this, exp.Table) else None
        else:
            table = this.name if isinstance(this, exp.Table) else None
        select = root.expression
        if select is None:
            return None  # 纯 DDL
        if kind not in ("TABLE", "VIEW"):
            return None
        return table, cols, select
    return None


# ---------------------------------------------------------------- 主入口

def _root_cte_scope(root) -> dict:
    """`WITH c AS (...) INSERT INTO t ... SELECT ... FROM c`：CTE 挂在 DML 根节点上而非 SELECT 上。

    不把它带进初始 scope 会让 CTE 名被当成基表 → 假边（D7）。M3 修。
    """
    scope: dict = {}
    with_ = root.args.get("with_")
    if with_ is None:
        with_ = root.args.get("with")
    if with_ is not None:
        for cte in with_.expressions:
            if isinstance(cte, exp.CTE) and cte.alias:
                scope[cte.alias] = cte.this
    return scope


def _register_insert_schema(corpus: Corpus, root, table: str) -> None:
    """INSERT 目标无 schema 时按列清单/SELECT 输出名补全（类型 unknown，不编造）。

    M1 schema 推导只覆盖 CREATE TABLE/CTAS/VIEW；INSERT 目标表在此补齐，
    否则下游按表回溯列（如 `e.amt`）会因 schema 缺列误判 unknown_type。
    """
    if table in corpus.schemas:
        return
    select = root.expression
    if select is None or not isinstance(select, exp.Select):
        return
    names: list = []
    cols = root.this.expressions if isinstance(root.this, exp.Schema) else None
    if cols:
        names = [c.name for c in cols]
    else:
        for proj in select.expressions:
            if _is_star(proj):
                return  # star 展开不了：不编造
            n = proj.alias_or_name
            if not n:
                return
            names.append(n)
    if names:
        corpus.schemas[table] = {c: "unknown" for c in names}


def _flag_no_source(resolver, write_ids: list, stmt) -> None:
    """写语句零边时给出确定结论 `no_source_columns`（§4.2）：边集为空是**结果**，不是丢弃。

    只在该语句还没有任何语句级诊断时补——已有诊断的语句（PARSE_ERROR / arity_mismatch /
    skipped_merge_branch …）本身就是留痕，不重复记。
    """
    if resolver.edges:
        return
    if any(d.reason_code != "dialect_defaulted" for d in resolver.diags):
        return
    resolver._diag(
        "no_source_columns",
        f"write statement resolved {resolver.output_count} output column(s) but none has a "
        "source column in the AST (constant/literal only); empty edge set is the determined result",
    )


def build_edges(corpus: Corpus):
    """sqlglot AST + scope walker → (edges, diagnostics)。"""
    edges: list[Edge] = []
    diags: list[Diagnostic] = []
    write_ids: list[str] = []  # 应产出血缘的写语句（§4.2 规则 4 零静默门的输入）

    for stmt in corpus.statements:
        dialect = _DIALECT_MAP.get(stmt.dialect, "postgres")
        try:
            root = sqlglot.parse_one(stmt.sql, read=dialect)
        except ParseError as exc:
            diags.append(Diagnostic(stmt.file, stmt.index, "PARSE_ERROR",
                                    f"parse failed: {exc}", False))
            continue
        except Exception as exc:  # sqlglot 内部异常不静默
            diags.append(Diagnostic(stmt.file, stmt.index, "PARSE_ERROR",
                                    f"parser error: {type(exc).__name__}: {exc}", False))
            continue

        if root is None:
            continue

        if isinstance(root, (exp.Command,)) or type(root).__name__ == "Execute":
            diags.append(Diagnostic(stmt.file, stmt.index, "UNSUPPORTED_DYNAMIC_SQL",
                                    f"dynamic SQL statement stopped: {_clean_sql(root)[:80]}",
                                    True))
            continue

        node_count = sum(1 for _ in root.walk())
        if node_count > MAX_AST_NODES:
            diags.append(Diagnostic(stmt.file, stmt.index, "PARSE_ERROR",
                                    f"AST node count {node_count} exceeds {MAX_AST_NODES}; statement skipped",
                                    False))
            continue

        # ---- MERGE：核心里没有 _target_of 形态，走 M3 降级策略（逐分支）----
        if isinstance(root, exp.Merge):
            write_ids.append(stmt.statement_id)
            resolver = _Resolver(corpus, stmt)
            fallback.resolve_merge(resolver, root)
            resolver.output_count = len({e.target_column for e in resolver.edges})
            edges.extend(resolver.edges)
            diags.extend(resolver.diags)
            _flag_no_source(resolver, write_ids, stmt)
            continue

        target = _target_of(root, corpus)

        # ---- 存储过程 / 函数体：首期不做体内血缘（D11 / plan/01 §六），整条跳过但必须留痕 ----
        if target is None and isinstance(root, exp.Create) \
                and (root.args.get("kind") or "").upper() in ("PROCEDURE", "FUNCTION"):
            diags.append(Diagnostic(
                stmt.file, stmt.index, "unsupported_stored_procedure",
                f"{(root.args.get('kind') or '').upper()} body lineage not supported (D11); "
                "statement skipped",
                True,
            ))
            continue

        if target is None:
            continue  # 纯 SELECT / 纯 DDL：不是血缘语句
        table, explicit_cols, select = target
        if not table or select is None:
            continue
        write_ids.append(stmt.statement_id)

        if isinstance(root, exp.Insert):
            _register_insert_schema(corpus, root, table)

        resolver = _Resolver(corpus, stmt)
        outputs = resolver.resolve_select(select, _root_cte_scope(root), 0)
        resolver.output_count = len(outputs)

        # 目标列：显式清单 > schema 顺序 > SELECT 输出名
        if explicit_cols:
            target_cols = list(explicit_cols)
        else:
            schema = corpus.schemas.get(table)
            names = [o["name"] for o in outputs]
            if schema and any(n is None for n in names):
                target_cols = list(schema)
            else:
                target_cols = [n if n is not None else "*" for n in names]

        if len(target_cols) != len(outputs):
            # 列数不符：不猜位置，记 arity_mismatch（§4.2），边不产出
            resolver._diag("arity_mismatch",
                           f"target columns {len(target_cols)} != select outputs {len(outputs)}")
            diags.extend(resolver.diags)
            continue

        for tcol, out in zip(target_cols, outputs):
            resolver.add_edge(table, tcol, out["sources"])

        _flag_no_source(resolver, write_ids, stmt)
        edges.extend(resolver.edges)
        diags.extend(resolver.diags)

    # §4.2 规则 5：unknown 边必有同键诊断（补出来的诊断并入后统一排序）
    diags.extend(fallback.reconcile_unknown_edges(edges, diags))

    # 去重 + 排序（§4.6；同语句内重复来源只留一条）
    seen = set()
    uniq: list[Edge] = []
    for e in edges:
        key = (e.statement_id,) + e.sort_key() + (e.reason_code or "",)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    uniq.sort(key=lambda e: (e.sort_key(), e.statement_id))
    diags.sort(key=lambda d: d.sort_key())
    corpus.write_ids = list(write_ids)
    return uniq, diags
