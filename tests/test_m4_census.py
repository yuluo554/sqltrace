# -*- coding: utf-8 -*-
"""M4 常驻测试：写入者普查五节 / 零误报 / 台账一致性 / golden g4 / 确定性输出。

口径单点：data/README.md §4.8（判据 + 规则 1–8）。
"""
from __future__ import annotations

import io
import json
import pathlib
import contextlib
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import sqltrace.cli as cli  # noqa: E402
from sqltrace.cli import main  # noqa: E402
from sqltrace.census import census, render_markdown  # noqa: E402
from sqltrace.core import build_edges  # noqa: E402
from sqltrace.loader import load_corpus  # noqa: E402
from sqltrace.model import Corpus, Edge, Statement  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "corpus"
G4 = REPO / "data" / "golden" / "g4" / "corpus"


def _census(sqls, schemas=None, dialect="postgres"):
    c = Corpus()
    c.statements = [Statement(file="t.sql", index=i, sql=s, dialect=dialect)
                    for i, s in enumerate(sqls)]
    if schemas:
        c.schemas.update(schemas)
    edges, diags = build_edges(c)
    return c, edges, diags, census(c, edges)


def _cli_json(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(argv)
    return rc, json.loads(buf.getvalue())


# ---------- 五节判定 ----------

def test_writers_and_readers_from_statement_ledgers():
    _, _, _, r = _census(
        ["CREATE TABLE raw_x (a int)", "CREATE TABLE mart_y AS SELECT a FROM raw_x"])
    assert [x.file for x in r.writers["mart_y"]] == ["t.sql"]
    assert r.writers["mart_y"][0].index == 1
    assert r.writers["mart_y"][0].dialect == "postgres"  # §4.8 条目三字段
    assert "raw_x" not in r.writers  # 纯 DDL 不是写者（规则 5）
    assert [x.index for x in r.readers["raw_x"]] == [1]


def test_write_only_constant_write_still_counts_as_writer():
    """规则 1：`CREATE TABLE ... AS SELECT 1` 边集为空（no_source_columns），仍是写者。"""
    _, edges, diags, r = _census(["CREATE TABLE t_const AS SELECT 1 AS a"])
    assert edges == [] and [d.reason_code for d in diags] == ["no_source_columns"]
    assert "t_const" in r.writers          # 不从边集反推
    assert r.write_only == ["t_const"]
    assert r.orphan == []


def test_pure_select_is_reader_but_not_writer():
    """规则 2：纯 SELECT 不产边，但它是读者（否则 orphan 判定失真）。"""
    _, edges, _, r = _census(["CREATE TABLE raw_x (a int)", "SELECT a FROM raw_x"])
    assert edges == []  # 纯 SELECT 无边
    assert "raw_x" in r.readers
    assert r.orphan == ["raw_x"] and r.write_only == []


def test_reader_cannot_come_from_unknown_edges():
    """规则 2：unknown 边 source_table=None，不得变成一张"读到的表"。"""
    _, edges, _, r = _census(["CREATE TABLE mart_z AS SELECT * FROM raw_missing"])
    assert any(e.kind == "unknown" and e.source_table is None for e in edges)
    assert None not in r.readers and "" not in r.readers
    assert all(t is not None for t in r.readers)


def test_cte_name_is_not_a_table():
    """规则 3：CTE 名在 AST 里是 Table 节点，但报表里不出现。"""
    _, _, _, r = _census(
        ["WITH agg AS (SELECT id FROM raw_y) INSERT INTO mart_z (id) SELECT id FROM agg"],
        {"raw_y": {"id": "unknown"}},
    )
    assert "agg" not in r.readers and "agg" not in r.writers
    assert list(r.readers) == ["raw_y"]


def test_self_write_target_is_not_a_reader():
    """规则 4：`INSERT INTO t ... FROM t` 的读集合剔除自身。"""
    _, _, _, r = _census(["INSERT INTO t_self (a) SELECT a FROM t_self"],
                         {"t_self": {"a": "unknown"}})
    assert "t_self" in r.writers
    assert "t_self" not in r.readers
    assert r.write_only == ["t_self"]


def test_merge_target_counts_as_writer():
    _, _, _, r = _census(
        ["MERGE INTO mart_a t USING stage_a s ON t.id = s.id "
         "WHEN MATCHED THEN UPDATE SET t.q = s.q"],
        {"mart_a": {"id": "unknown", "q": "unknown"},
         "stage_a": {"id": "unknown", "q": "unknown"}},
        dialect="tsql",
    )
    assert "mart_a" in r.writers
    assert "stage_a" in r.readers and "mart_a" not in r.readers


# ---------- 多写 / 零误报 ----------

def test_multi_writer_and_zero_false_positive():
    _, _, _, r = _census([
        "CREATE TABLE raw_x (a int)",
        "CREATE TABLE stage_1 AS SELECT a FROM raw_x",
        "CREATE TABLE stage_1 AS SELECT a FROM raw_x",
    ])
    assert [m["table"] for m in r.multi_writer] == ["stage_1"]
    assert len(next(m for m in r.multi_writer if m["table"] == "stage_1")["writers"]) == 2
    # 单写入者表绝不出现（§4.8 multi_writer 判据 len >= 2）
    assert all(m["table"] != "raw_x" for m in r.multi_writer)


def test_only_single_writer_tables_never_in_multi_writer():
    _, _, _, r = _census([
        "CREATE TABLE raw_x (a int)",
        "CREATE TABLE mart_a AS SELECT a FROM raw_x",
        "CREATE TABLE mart_b AS SELECT a FROM raw_x",
    ])
    assert r.multi_writer == []
    assert sorted(r.writers) == ["mart_a", "mart_b"]


# ---------- 排序（§4.6） ----------

def test_census_sorting_table_asc_writers_by_file_index():
    c = Corpus()
    c.statements = [
        Statement(file="z_sub.sql", index=0,
                  sql="INSERT INTO mart_x (a) SELECT a FROM raw_x", dialect="postgres"),
        Statement(file="a_sub.sql", index=2,
                  sql="INSERT INTO mart_x (a) SELECT a FROM raw_x", dialect="postgres"),
        Statement(file="a_sub.sql", index=0,
                  sql="INSERT INTO mart_x (a) SELECT a FROM raw_x", dialect="postgres"),
    ]
    c.schemas.update({"raw_x": {"a": "unknown"}, "mart_x": {"a": "unknown"}})
    edges, _ = build_edges(c)
    r = census(c, edges)
    refs = r.writers["mart_x"]
    assert [(x.file, x.index) for x in refs] == [
        ("a_sub.sql", 0), ("a_sub.sql", 2), ("z_sub.sql", 0)]
    mw = next(m for m in r.multi_writer if m["table"] == "mart_x")
    assert [x.file for x in mw["writers"]] == ["a_sub.sql", "a_sub.sql", "z_sub.sql"]


# ---------- 真实语料（合成植入项命中） ----------

def test_real_corpus_planted_items_hit():
    """M1 语料植入（`data/corpus` 根目录三件）：`51_*`+`52_*` 同写 `stage_hot` → 多写命中。

    备注（实测纠正，见 HANDOFF-M4 §四）：`plan/03 §M4` 与 `HANDOFF-M3 §三#5` 曾写
    "`50_*` 写 `raw_orphan`（无人读 → write_only）"，但 `51_*` 的 `SELECT id FROM raw_orphan`
    确实读了它 —— 故 `raw_orphan` 在本语料里**既不是 orphan 也不是 write_only**（写者 1、读者 1）。
    真实语料中的 write_only 植入项是 `stage_hot`（写者有 51/52，无任何读者）。这是文档与语料的
    事实不符，不是实现偏差；g4 golden（专为多写+孤儿构造）是权威植入项，见
    `test_golden_g4_multi_writer_and_orphan`。
    """
    c = load_corpus(CORPUS)
    edges, _ = build_edges(c)
    r = census(c, edges)
    mw = {m["table"]: m for m in r.multi_writer}
    assert "stage_hot" in mw
    who = {(x.file, x.index) for x in mw["stage_hot"]["writers"]}
    assert ("51_mart_multi_writer.sql", 0) in who
    assert ("52_stage_hot_w2.sql", 0) in who
    # stage_hot 只写不读（51/52 写它，无人读）→ 真实语料的 write_only 植入项
    assert "stage_hot" in r.write_only
    # raw_orphan 写者 50、读者 51 → 两边都不落（实测，纠正 M3 交接单的说法）
    assert [x.file for x in r.writers["raw_orphan"]] == ["50_mart_orphan.sql"]
    assert [x.file for x in r.readers["raw_orphan"]] == ["51_mart_multi_writer.sql"]
    assert "raw_orphan" not in r.write_only and "raw_orphan" not in r.orphan
    # 零误报：多写节里每张表都确有 ≥2 个写入者
    assert all(len(m["writers"]) >= 2 for m in r.multi_writer)
    # 五节互斥口径：orphan ∩ writers = ∅，write_only ∩ readers = ∅
    assert set(r.orphan) & set(r.writers) == set()
    assert set(r.write_only) & set(r.readers) == set()
    # 台账自检（§4.8 规则 8）：每条边的目标表都登记过写者
    assert r.edges_missing_writer == []


# ---------- golden g4 ----------

def test_golden_g4_multi_writer_and_orphan():
    c = load_corpus(G4)
    edges, _ = build_edges(c)
    r = census(c, edges)
    assert [m["table"] for m in r.multi_writer] == ["stage_hot"]
    assert {(x.file, x.index) for x in r.writers["stage_hot"]} == {
        ("a.sql", 1), ("b.sql", 0)}
    assert "raw_orphan" in r.write_only          # 只写不读
    assert r.orphan == ["raw_g4"]                # 有读无写
    assert r.edges_missing_writer == []


# ---------- 门复用（零静默 + 台账一致性） ----------

def test_census_cli_zero_silence_gate_is_reused(monkeypatch, tmp_path):
    """§4.8 规则 7：census 复用同一门；门报违规 → 退出码 4（阳性对照）。"""
    (tmp_path / "a.sql").write_text(
        "CREATE TABLE raw_x (a int);\n", encoding="utf-8")
    monkeypatch.setattr(cli, "zero_silence_violations", lambda *a, **k: ["a.sql#0"])
    rc, payload = _cli_json(["census", str(tmp_path), "--json"])
    assert rc == 4
    assert payload["zero_silence"]["silent_statements"] == ["a.sql#0"]
    assert payload["zero_silence"]["passed"] is False


def test_census_cli_ledger_mismatch_gate(monkeypatch, tmp_path):
    """§4.8 规则 8：边集有目标表但写者台账缺它 → 退出码 4（阳性对照）。"""
    (tmp_path / "a.sql").write_text(
        "CREATE TABLE raw_x (a int);\n", encoding="utf-8")

    def fake_edges(corpus):
        return ([Edge("ghost_tbl", "c", "value", "raw_x", "a", "a",
                      statement_id="a.sql#0")], [])

    monkeypatch.setattr(cli, "build_edges", fake_edges)
    rc, payload = _cli_json(["census", str(tmp_path), "--json"])
    assert rc == 4
    assert payload["zero_silence"]["edges_missing_writer"] == ["ghost_tbl"]


def test_census_cli_real_corpus_exit0_and_shape():
    rc, payload = _cli_json(["census", str(CORPUS), "--json"])
    assert rc == 0
    body = payload["census"]
    assert set(body) == {"writers", "readers", "orphan", "multi_writer",
                         "write_only", "edges_missing_writer"}
    assert payload["zero_silence"]["passed"] is True
    # 键序固定 + 表名升序（§4.6）
    assert list(body["writers"]) == sorted(body["writers"])


def test_census_markdown_sample_is_real_output_and_deterministic():
    """`docs/census-sample.md` 必须是真实运行输出，且两次运行逐字节一致。"""
    sample = REPO / "docs" / "census-sample.md"
    assert sample.is_file(), "docs/census-sample.md 缺失（M4 DoD 承诺项）"
    c = load_corpus(CORPUS)
    edges, _ = build_edges(c)
    expected = render_markdown(census(c, edges), _version())
    assert sample.read_text(encoding="utf-8") == expected
    assert sample.read_text(encoding="utf-8") == render_markdown(
        census(*_reload()), _version())


def _version() -> str:
    from sqltrace import __version__
    return __version__


def _reload():
    c = load_corpus(CORPUS)
    edges, _ = build_edges(c)
    return c, edges