# -*- coding: utf-8 -*-
"""M2 常驻测试：血缘内核（data/README.md §4.1 分型口径、§4.3 精确率/召回门槛）。"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sqltrace.core import build_edges  # noqa: E402
from sqltrace.loader import load_corpus  # noqa: E402
from sqltrace.model import Corpus, Statement  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "corpus"
LABELS = REPO / "data" / "labels"


def _edges_from_sql(sql: str, dialect: str = "postgres", schemas: dict | None = None):
    corpus = Corpus()
    corpus.statements = [Statement(file="t.sql", index=0, sql=sql, dialect=dialect)]
    if schemas:
        corpus.schemas.update(schemas)
    edges, diags = build_edges(corpus)
    return edges, diags


# ---------- §4.1 强制口径 ----------

def test_window_partition_order_are_control_not_value():
    """SUM(x) OVER (PARTITION BY k ORDER BY t) → (w,value,x)+(w,control,k)+(w,control,t)；禁止 (w,value,k)。"""
    edges, _ = _edges_from_sql(
        "CREATE TABLE stage_w AS SELECT SUM(x) OVER (PARTITION BY k ORDER BY t) AS w FROM raw_w;",
        schemas={"raw_w": {"x": "unknown", "k": "unknown", "t": "unknown"}},
    )
    got = {(e.source_column, e.kind): e.expr for e in edges if e.target_column == "w"}
    assert got[("x", "value")] == "SUM(x) OVER (PARTITION BY k ORDER BY t)"
    assert "PARTITION BY k" in got[("k", "control")]
    assert "ORDER BY t" in got[("t", "control")]
    assert ("k", "value") not in got, got  # 窗口键不得归 value
    assert ("t", "value") not in got, got


def test_case_then_value_when_control():
    edges, _ = _edges_from_sql(
        "CREATE TABLE stage_c AS SELECT CASE WHEN flag > 0 THEN qty ELSE 0 END AS v FROM raw_c;",
        schemas={"raw_c": {"flag": "unknown", "qty": "unknown"}},
    )
    got = {(e.source_column, e.kind) for e in edges if e.target_column == "v"}
    assert ("qty", "value") in got and ("flag", "control") in got
    assert ("flag", "value") not in got  # 谓词列不得归 value（THEN 有列时）


def test_case_constant_branch_predicate_also_value():
    """THEN 全常量：取值由谓词决定 → 谓词列同时记 value（标注口径）。"""
    edges, _ = _edges_from_sql(
        "CREATE TABLE stage_c AS SELECT CASE WHEN flag > 0 THEN 'y' END AS v FROM raw_c;",
        schemas={"raw_c": {"flag": "unknown"}},
    )
    got = {(e.source_column, e.kind) for e in edges if e.target_column == "v"}
    assert ("flag", "value") in got and ("flag", "control") in got


def test_where_join_group_having_qualify_control():
    edges, _ = _edges_from_sql(
        "INSERT INTO mart_m (dt, tot) SELECT dt, SUM(amt) AS tot FROM raw_m "
        "WHERE dt > '2020-01-01' GROUP BY dt HAVING COUNT(*) >= 1;",
        schemas={"raw_m": {"dt": "unknown", "amt": "unknown"}},
    )
    got = {(e.source_column, e.kind): e.expr for e in edges}
    assert ("dt", "value") in got
    ctrl_dt = [e.expr for e in edges if e.source_column == "dt" and e.kind == "control"]
    assert any("WHERE" in v for v in ctrl_dt)
    assert any("GROUP BY" in v for v in ctrl_dt)
    # HAVING COUNT(*)：行数谓词 → 由 GROUP BY 键承担
    assert any("HAVING" in v for v in ctrl_dt)
    assert ("amt", "value") in got


def test_join_on_control_with_join_path():
    edges, _ = _edges_from_sql(
        "CREATE TABLE stage_j AS SELECT a.x FROM raw_a a JOIN raw_b b ON b.id = a.id;",
        schemas={"raw_a": {"x": "unknown", "id": "unknown"},
                 "raw_b": {"id": "unknown"}},
    )
    on_edge = [e for e in edges if e.kind == "control" and "JOIN" in e.expr]
    assert on_edge, edges
    assert {e.source_table for e in on_edge} <= {"raw_a", "raw_b"}
    assert all(e.join_path == ("raw_a", "raw_b") for e in on_edge)


def test_cte_penetrates_to_base_table():
    """CTE 两层：外层窗口经内层聚合穿透到基表（duckdb/49 口径）。"""
    sql = (
        "CREATE TABLE stage_cte AS "
        "WITH agg AS (SELECT dt, SUM(likes) AS tot_likes FROM raw_s GROUP BY dt) "
        "SELECT dt, tot_likes, SUM(tot_likes) OVER (ORDER BY dt) AS cum FROM agg;"
    )
    edges, _ = _edges_from_sql(
        sql, schemas={"raw_s": {"dt": "unknown", "likes": "unknown"}}
    )
    got = {(e.source_table, e.source_column, e.kind): e.expr for e in edges}
    assert ("raw_s", "likes", "value") in got  # 窗口值参数穿透
    assert ("raw_s", "dt", "control") in got   # GROUP BY / ORDER BY 穿透
    assert not any(src == "agg" for (src, _c, _k) in got), got  # 不停在 CTE 名上


def test_union_positional_merge():
    edges, _ = _edges_from_sql(
        "CREATE TABLE mart_u AS SELECT id, nm FROM raw_u1 UNION ALL SELECT id, nm FROM raw_u2;",
        schemas={"raw_u1": {"id": "unknown", "nm": "unknown"},
                 "raw_u2": {"id": "unknown", "nm": "unknown"}},
    )
    got = {(e.source_table, e.source_column, e.kind) for e in edges}
    assert ("raw_u1", "id", "value") in got and ("raw_u2", "id", "value") in got
    assert ("raw_u1", "nm", "value") in got and ("raw_u2", "nm", "value") in got


def test_unknown_wildcard_unknown_schema():
    edges, _ = _edges_from_sql("CREATE TABLE stage_s AS SELECT * FROM raw_unknown;")
    unknowns = [e for e in edges if e.kind == "unknown"]
    assert unknowns and all(e.reason_code == "unknown_wildcard" for e in unknowns)
    assert all(e.approximate for e in unknowns)


def test_arity_mismatch_no_silent_guess():
    edges, diags = _edges_from_sql(
        "INSERT INTO stage_g (c1) SELECT a, b FROM raw_g;",
        schemas={"raw_g": {"a": "unknown", "b": "unknown"},
                 "stage_g": {"c1": "unknown", "c2": "unknown"}},
    )
    assert any(d.reason_code == "arity_mismatch" for d in diags)


def test_dynamic_sql_diagnostic():
    edges, diags = _edges_from_sql("EXEC('SELECT inv_id FROM raw_inv');", dialect="tsql")
    assert any(d.reason_code == "UNSUPPORTED_DYNAMIC_SQL" for d in diags)
    assert not edges


def test_parse_error_diagnostic():
    edges, diags = _edges_from_sql("SELEC FROM WHERE;")
    assert any(d.reason_code == "PARSE_ERROR" for d in diags)


def test_sort_key_and_dedup():
    edges, _ = _edges_from_sql(
        "CREATE TABLE stage_d AS SELECT a.x, a.x FROM raw_a a;",
        schemas={"raw_a": {"x": "unknown"}},
    )
    # 同语句重复来源去重；输出按 §4.6 排序键
    keys = [e.sort_key() for e in edges]
    assert keys == sorted(keys)
    assert len(keys) == len(set((e.target_table, e.target_column, e.kind,
                                 e.source_table, e.source_column, e.expr) for e in edges))


# ---------- §4.3 标注语料自评（常驻门槛） ----------

@pytest.fixture(scope="module")
def real_edges():
    corpus = load_corpus(CORPUS)
    edges, _ = build_edges(corpus)
    return edges


def _label_set():
    labeled = set()
    for p in sorted(LABELS.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for _f, es in data["edges"].items():
            for e in es:
                labeled.add((e["target"], e["source"], e["kind"]))
    return labeled


def test_value_precision_100(real_edges):
    labeled = _label_set()
    mine_value = {(f"{e.target_table}.{e.target_column}",
                   f"{e.source_table}.{e.source_column}", "value")
                  for e in real_edges if e.kind == "value" and e.source_table}
    bad = mine_value - labeled
    assert not bad, sorted(bad)


def test_recall_at_least_85(real_edges):
    labeled = _label_set()
    mine = {(f"{e.target_table}.{e.target_column}",
             f"{e.source_table}.{e.source_column}" if e.source_table else None, e.kind)
            for e in real_edges}
    hit = len(mine & labeled)
    recall = hit / len(labeled)
    assert recall >= 0.85, recall


def test_missed_labels_not_silent(real_edges):
    """未命中的标注边，其 target 须有 unknown 边或完全缺失于产出（不许 value/control 错判掩盖）。"""
    labeled = _label_set()
    mine = {(f"{e.target_table}.{e.target_column}",
             f"{e.source_table}.{e.source_column}" if e.source_table else None, e.kind)
            for e in real_edges}
    missed = labeled - mine
    unknown_targets = {f"{e.target_table}.{e.target_column}"
                       for e in real_edges if e.kind == "unknown"}
    for tgt, _src, kind in missed:
        assert tgt in unknown_targets or kind == "control", (tgt, kind)
