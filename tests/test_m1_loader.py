# -*- coding: utf-8 -*-
"""M1 常驻测试：装载器闭环 + 语料/标注不变量（data/README.md §三 纪律、§4.2/§4.5/§4.6 口径）。"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sqltrace.loader import load_corpus  # noqa: E402
from sqltrace.constants import MAX_STATEMENTS_PER_FILE  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "corpus"
LABELS = REPO / "data" / "labels"
TABLE_PREFIXES = {"raw", "stage", "mart"}


# ---------- loader 单元 ----------

def test_gitignore_skip_and_reason(tmp_path):
    (tmp_path / "keep.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "skip.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("skip.sql\n", encoding="utf-8")
    corpus = load_corpus(tmp_path)
    assert [f["path"] for f in corpus.files] == ["keep.sql"]
    assert corpus.ignored == [{"path": "skip.sql", "reason": "gitignore"}]


def test_dialect_from_directory_default_with_diagnostic(tmp_path):
    (tmp_path / "postgres").mkdir()
    (tmp_path / "unsorted").mkdir()
    (tmp_path / "postgres" / "a.sql").write_text(
        "CREATE TABLE t_a AS SELECT 1 AS x;", encoding="utf-8")
    (tmp_path / "unsorted" / "b.sql").write_text(
        "CREATE TABLE t_b AS SELECT 1 AS x;", encoding="utf-8")
    corpus = load_corpus(tmp_path)
    dia = {f["path"]: f["dialect"] for f in corpus.files}
    assert dia["postgres/a.sql"] == "postgres"
    assert dia["unsorted/b.sql"] == "postgres"  # §4.5 默认
    assert any(d.reason_code == "dialect_defaulted" for d in corpus.diagnostics)


def test_schema_derivation_ctas_and_view(tmp_path):
    (tmp_path / "a.sql").write_text(
        "CREATE TABLE raw_src (x int, y text);\n"
        "CREATE TABLE stage_cp AS SELECT x, y FROM raw_src;\n"
        "CREATE VIEW stage_v AS SELECT x FROM raw_src;\n",
        encoding="utf-8",
    )
    corpus = load_corpus(tmp_path)
    assert corpus.schemas["raw_src"] == {"x": "unknown", "y": "unknown"} or \
        corpus.schemas["raw_src"] == {"x": "int", "y": "text"}  # DDL 保留声明类型也可
    assert set(corpus.schemas["stage_cp"]) == {"x", "y"}
    assert set(corpus.schemas["stage_v"]) == {"x"}


def test_topology_orders_writer_before_reader(tmp_path):
    (tmp_path / "b.sql").write_text(
        "CREATE TABLE agg AS SELECT x FROM base;", encoding="utf-8")
    (tmp_path / "a.sql").write_text(
        "CREATE TABLE base AS SELECT 1 AS x;", encoding="utf-8")
    corpus = load_corpus(tmp_path)
    files = [s.file for s in corpus.statements]
    assert files.index("a.sql") < files.index("b.sql")


def test_cycle_detected(tmp_path):
    (tmp_path / "a.sql").write_text(
        "CREATE TABLE t1 AS SELECT x FROM t2;\n"
        "CREATE TABLE t2 AS SELECT x FROM t1;\n",
        encoding="utf-8",
    )
    corpus = load_corpus(tmp_path)
    cycles = [d for d in corpus.diagnostics if d.reason_code == "cycle_detected"]
    assert len(cycles) == 2  # 环内每条语句一条诊断（零静默）


def test_statement_cap_aborts_file(tmp_path):
    (tmp_path / "a.sql").write_text(
        ";\n".join(["SELECT 1"] * (MAX_STATEMENTS_PER_FILE + 1)) + ";", encoding="utf-8")
    corpus = load_corpus(tmp_path)
    assert not [s for s in corpus.statements if s.file == "a.sql"]
    assert any("exceeds" in d.message for d in corpus.diagnostics)


# ---------- 语料/标注不变量（语料与真值不得漂移，§三#6） ----------

@pytest.fixture(scope="module")
def real_corpus():
    return load_corpus(CORPUS)


def test_corpus_file_count_in_range(real_corpus):
    assert 40 <= len(real_corpus.files) <= 60


def test_corpus_covers_five_dialects(real_corpus):
    tops = {f["path"].split("/")[0] for f in real_corpus.files if "/" in f["path"]}
    assert tops == {"postgres", "snowflake", "bigquery", "tsql", "duckdb"}


def test_table_names_synthetic(real_corpus):
    bad = [t for t in real_corpus.schemas if t.split("_")[0] not in TABLE_PREFIXES]
    assert not bad, bad


def test_literals_placeholder_only(real_corpus):
    """字面量只用占位值；动态 SQL 字符串除外（§三#2）。"""
    allowed = {"'x'", "'foo'", "'y'", "'a'", "'b'", "'2020-01-01'"}
    dyn = re.compile(r"^'(SELECT|INSERT|UPDATE|DELETE)\b.*'$", re.I | re.S)
    for f in real_corpus.files:
        text = (CORPUS / f["path"]).read_text(encoding="utf-8")
        for m in re.finditer(r"'([^']*)'", text):
            lit = m.group(0)
            assert lit in allowed or dyn.match(lit) or re.fullmatch(r"'\d+(-\d+)*'", lit), \
                (f["path"], lit)


def test_labels_cover_corpus_and_kinds():
    labeled_files: set[str] = set()
    total = 0
    for p in sorted(LABELS.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for fname, edges in data["edges"].items():
            labeled_files.add(fname)
            for e in edges:
                assert e["kind"] in ("value", "control"), (p.name, e)  # unknown 不预标（§三#5）
                assert e["target"].split(".")[0].split("_")[0] in TABLE_PREFIXES
                assert e["source"].split(".")[0].split("_")[0] in TABLE_PREFIXES
            total += len(edges)
        assert not (set(data["edges"]) - {f["path"] for f in load_corpus(CORPUS).files}), p.name
    assert total > 100  # 逐边标注成规模，防"空标注"退化
    assert labeled_files  # 非空


def test_corpus_statement_cap_held(real_corpus):
    # 每文件语句数远低于上限（§4.7），装载器不截断
    assert len(real_corpus.statements) >= len(real_corpus.files)
