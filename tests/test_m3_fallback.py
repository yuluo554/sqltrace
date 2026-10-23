# -*- coding: utf-8 -*-
"""M3 常驻测试：降级策略 / reason code 全覆盖 / 零静默机械门 / golden g2·g3。

口径单点：data/README.md §4.2（枚举 + 挂载点 + 规则 1–5）。
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sqltrace.cli import main  # noqa: E402
from sqltrace.constants import EDGE_AND_DIAG_CODES, REASON_CODES  # noqa: E402
from sqltrace.core import build_edges  # noqa: E402
from sqltrace.fallback import (  # noqa: E402
    assert_reason_codes,
    diagnose_missing_edges,
    zero_silence_violations,
)
from sqltrace.loader import load_corpus  # noqa: E402
from sqltrace.model import Corpus, Statement  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "corpus"
GOLDEN = REPO / "data" / "golden"


def _run(sql: str, dialect: str = "postgres", schemas: dict | None = None):
    corpus = Corpus()
    corpus.statements = [Statement(file="t.sql", index=0, sql=sql, dialect=dialect)]
    if schemas:
        corpus.schemas.update(schemas)
    edges, diags = build_edges(corpus)
    return corpus, edges, diags


MERGE_SCHEMAS = {
    "stage_inv": {"id": "unknown", "qty": "unknown", "dt": "unknown"},
    "mart_inv": {"id": "unknown", "qty": "unknown", "dt": "unknown"},
}


# ---------- MERGE（skipped_merge_branch / arity_mismatch） ----------

def test_merge_update_and_insert_produce_value_edges():
    _, edges, diags = _run(
        "MERGE INTO mart_inv t USING stage_inv s ON t.id = s.id "
        "WHEN MATCHED THEN UPDATE SET t.qty = s.qty "
        "WHEN NOT MATCHED THEN INSERT (id, qty) VALUES (s.id, s.qty)",
        "tsql", MERGE_SCHEMAS,
    )
    got = {(e.target_column, e.source_column, e.kind) for e in edges}
    assert ("qty", "qty", "value") in got          # UPDATE SET 分支
    assert ("id", "id", "value") in got            # INSERT 分支（列清单位置映射）
    assert ("qty", "id", "control") in got         # ON 条件 → control
    assert all(e.join_path == ("mart_inv", "stage_inv") for e in edges)
    assert not [d for d in diags if d.reason_code == "skipped_merge_branch"]


def test_merge_target_side_not_an_upstream():
    """ON 条件里的目标表自引用不得产出 self-loop 边（D7：不得假边）。"""
    _, edges, _ = _run(
        "MERGE INTO mart_inv t USING stage_inv s ON t.id = s.id "
        "WHEN MATCHED THEN UPDATE SET t.qty = s.qty",
        "tsql", MERGE_SCHEMAS,
    )
    assert not [e for e in edges if e.source_table == "mart_inv"]


def test_merge_delete_branch_is_reported_not_silent():
    _, edges, diags = _run(
        "MERGE INTO mart_inv t USING stage_inv s ON t.id = s.id "
        "WHEN MATCHED THEN DELETE",
        "tsql", MERGE_SCHEMAS,
    )
    skips = [d for d in diags if d.reason_code == "skipped_merge_branch"]
    assert skips and skips[0].approximate is True
    assert not edges  # DELETE 没有列级边，但留痕了


def test_merge_insert_without_column_list_is_reported():
    _, edges, diags = _run(
        "MERGE INTO mart_inv t USING stage_inv s ON t.id = s.id "
        "WHEN NOT MATCHED THEN INSERT VALUES (s.id, s.qty)",
        "tsql", MERGE_SCHEMAS,
    )
    assert not edges
    assert any(d.reason_code == "skipped_merge_branch" for d in diags)


def test_merge_insert_arity_mismatch():
    _, edges, diags = _run(
        "MERGE INTO mart_inv t USING stage_inv s ON t.id = s.id "
        "WHEN NOT MATCHED THEN INSERT (id, qty, dt) VALUES (s.id, s.qty)",
        "tsql", MERGE_SCHEMAS,
    )
    assert not edges
    assert any(d.reason_code == "arity_mismatch" and d.approximate is False for d in diags)


def test_merge_using_subquery_penetrates():
    _, edges, _ = _run(
        "MERGE INTO mart_inv t USING (SELECT id, qty FROM stage_inv) u ON t.id = u.id "
        "WHEN MATCHED THEN UPDATE SET t.qty = u.qty",
        "bigquery", MERGE_SCHEMAS,
    )
    assert {(e.target_column, e.source_column) for e in edges if e.kind == "value"} == {
        ("qty", "qty")}


# ---------- recursion_limit（真实触发，两条路径） ----------

def test_recursion_limit_depth_trigger():
    sql = "SELECT id FROM raw_x"
    for i in range(20):  # 嵌套 20 层 > §4.7 上限 16
        sql = f"SELECT id FROM ({sql}) s{i}"
    _, edges, diags = _run(f"CREATE TABLE mart_deep AS {sql}",
                           schemas={"raw_x": {"id": "unknown"}})
    limit = [d for d in diags if d.reason_code == "recursion_limit"]
    assert len(limit) == 1 and limit[0].approximate is True
    # 深度截断后不得编造来源：只允许 unknown 边
    assert all(e.kind == "unknown" for e in edges)


def test_recursion_limit_self_reference_trigger():
    _, edges, diags = _run(
        "WITH RECURSIVE r AS (SELECT id FROM raw_x UNION ALL SELECT id FROM r) "
        "INSERT INTO mart_x (id) SELECT id FROM r",
        schemas={"raw_x": {"id": "unknown"}, "mart_x": {"id": "unknown"}},
    )
    assert any(d.reason_code == "recursion_limit" for d in diags)
    assert any(e.kind == "value" and e.source_table == "raw_x" for e in edges)  # 非递归半边仍解析
    assert not [e for e in edges if e.source_table == "r"]  # 不得把 CTE 名当基表


# ---------- dialect_defaulted（M3 接线：从占位码改为真码） ----------

def test_dialect_defaulted_uses_dedicated_code(tmp_path):
    (tmp_path / "unsorted").mkdir()
    (tmp_path / "unsorted" / "a.sql").write_text(
        "CREATE TABLE t_a AS SELECT 1 AS x;", encoding="utf-8")
    corpus = load_corpus(tmp_path)
    dias = [d for d in corpus.diagnostics if d.reason_code == "dialect_defaulted"]
    assert len(dias) == 1
    assert dias[0].approximate is True
    assert not [d for d in corpus.diagnostics if d.reason_code == "PARSE_ERROR"]


def test_dialect_override_suppresses_defaulted(tmp_path):
    (tmp_path / "unsorted").mkdir()
    (tmp_path / "unsorted" / "a.sql").write_text(
        "CREATE TABLE t_a AS SELECT 1 AS x;", encoding="utf-8")
    corpus = load_corpus(tmp_path, None, "bigquery")
    assert not [d for d in corpus.diagnostics if d.reason_code == "dialect_defaulted"]
    assert corpus.files[0]["dialect"] == "bigquery"


# ---------- no_source_columns / 根节点 CTE ----------

def test_constant_only_write_is_explicit_not_silent():
    corpus, edges, diags = _run("CREATE TABLE mart_c AS SELECT 1 AS id, 'x' AS nm")
    assert not edges
    assert any(d.reason_code == "no_source_columns" for d in diags)
    assert zero_silence_violations(corpus.write_ids, edges, diags) == []


def test_with_cte_on_dml_root_not_treated_as_base_table():
    """`WITH c AS (...) INSERT ...` 的 CTE 挂在 DML 根节点：不得产出 `c` 假基表边。"""
    _, edges, _ = _run(
        "WITH c AS (SELECT id FROM raw_x) INSERT INTO mart_x (id) SELECT id FROM c",
        schemas={"raw_x": {"id": "unknown"}, "mart_x": {"id": "unknown"}},
    )
    assert [(e.target_column, e.kind, e.source_table, e.source_column) for e in edges] == [
        ("id", "value", "raw_x", "id")]


def test_stored_procedure_body_is_reported_not_silent():
    """D11 边界：存储过程体内血缘首期不做，但整条语句必须留痕（零静默）。"""
    _, edges, diags = _run(
        "CREATE PROCEDURE p AS BEGIN INSERT INTO mart_x (id) SELECT id FROM raw_x; END",
        "tsql", {"raw_x": {"id": "unknown"}, "mart_x": {"id": "unknown"}},
    )
    assert not edges
    proc = [d for d in diags if d.reason_code == "unsupported_stored_procedure"]
    assert proc and proc[0].approximate is True


# ---------- 零静默机械门（§4.2 规则 4） ----------

@pytest.fixture(scope="module")
def real_run():
    corpus = load_corpus(CORPUS)
    edges, diags = build_edges(corpus)
    return corpus, edges, diags


def test_zero_silence_gate_on_corpus(real_run):
    corpus, edges, diags = real_run
    assert zero_silence_violations(corpus.write_ids, edges, diags) == []
    assert corpus.write_ids  # 非空跑：真有写语句参与判定


def test_zero_silence_gate_catches_violation():
    """阳性对照：门必须能红，否则是空判据。"""
    assert zero_silence_violations(["x.sql#0"], [], []) == ["x.sql#0"]


def test_reason_codes_closed_enum(real_run):
    _, edges, diags = real_run
    assert assert_reason_codes(edges, diags) == []


# ---------- D1：数据写语句（UPDATE / DELETE / TRUNCATE）必须被门看见 ----------

@pytest.mark.parametrize("sql,label", [
    ("UPDATE mart_x SET v = v + 1", "UPDATE"),
    ("DELETE FROM mart_y WHERE id = 1", "DELETE"),
    ("TRUNCATE TABLE mart_z", "TRUNCATE TABLE"),
])
def test_data_write_statement_is_visible_to_zero_silence_gate(sql, label):
    """D1（DEC-1 乙案）：根节点是数据写类型就必须"有边或有诊断"，不得静默丢弃。

    本期不产边，所以判据落在诊断上；`write_ids` 必须包含它——否则门根本不去看。
    """
    corpus, edges, diags = _run(sql, "postgres", {"mart_x": {"v": "unknown"},
                                                  "mart_y": {"id": "unknown"}})
    assert corpus.write_ids == ["t.sql#0"], "数据写语句未登记进零静默门的输入集合"
    got = [d for d in diags if d.reason_code == "unsupported_write_statement"]
    assert len(got) == 1 and got[0].approximate is True
    assert label in got[0].message          # 诊断点名语句类型，不是空 message
    assert zero_silence_violations(corpus.write_ids, edges, diags) == []


def test_data_write_statement_negative_control_exits_4(tmp_path, monkeypatch):
    """阳性对照：把留痕去掉后同一条 SQL 必须 rc=4（门真的会红，不是空判据）。"""
    import sqltrace.core as core

    (tmp_path / "postgres").mkdir()
    (tmp_path / "postgres" / "a.sql").write_text("UPDATE mart_x SET v = v + 1;\n",
                                                 encoding="utf-8")
    monkeypatch.setattr(core, "_flag_unsupported_write", lambda *a, **k: None)
    rc = main(["lineage", str(tmp_path), "--json"])
    assert rc == 4


def test_data_write_statement_is_not_a_census_writer():
    """§4.8 writers 口径不变：UPDATE / DELETE 不进写者台账（普查数字不漂）。"""
    corpus, _, _ = _run("UPDATE mart_x SET v = v + 1", "postgres",
                        {"mart_x": {"v": "unknown"}})
    assert corpus.write_targets == {}


# ---------- D4：动态 SQL 诊断点名那条语句，不是文件开头注释 ----------

@pytest.mark.parametrize("sql,dialect,must_contain", [
    ("EXEC('SELECT inv_id FROM raw_inv')", "tsql", "SELECT inv_id FROM raw_inv"),
    ("EXEC sp_help", "tsql", "sp_help"),
    ("CALL p()", "postgres", "p()"),
])
def test_dynamic_sql_diagnostic_names_the_statement(sql, dialect, must_contain):
    """`Execute.sql()` 实测返回 `''`（且会 warn），message 不得因此退化成空/注释。"""
    _, _, diags = _run(sql, dialect)
    got = [d for d in diags if d.reason_code == "UNSUPPORTED_DYNAMIC_SQL"]
    assert got, "动态 SQL 诊断丢了"
    assert must_contain in got[0].message, got[0].message
    assert got[0].message.strip() != "dynamic SQL statement stopped:"


def test_dynamic_sql_diagnostic_on_comment_prefixed_corpus_statement():
    """语料里那条带文件头注释的 EXEC：message 必须点名 EXEC，不能显示注释（D4 现场）。"""
    _, _, diags = _run(
        "-- 动态 SQL：M3 将以 UNSUPPORTED_DYNAMIC_SQL 降级（unknown 不预标）\n"
        "EXEC('SELECT inv_id FROM raw_inv')", "tsql")
    got = [d for d in diags if d.reason_code == "UNSUPPORTED_DYNAMIC_SQL"]
    assert got and "EXEC(" in got[0].message
    assert "动态 SQL：M3" not in got[0].message


def test_every_unknown_edge_has_reason_and_diag(real_run):
    """§4.2 规则 5：unknown 边必带 reason code + approximate，且有同键诊断。"""
    _, edges, diags = real_run
    unknown = [e for e in edges if e.kind == "unknown"]
    assert unknown
    for e in unknown:
        assert e.reason_code in EDGE_AND_DIAG_CODES
        assert e.approximate is True
    assert diagnose_missing_edges(edges, diags) == []
    keys = {(d.file, d.statement_index, d.reason_code) for d in diags}
    for e in unknown:
        f, i = e.statement_id.rsplit("#", 1)
        assert (f, int(i), e.reason_code) in keys


def test_every_reason_code_has_a_triggering_case(tmp_path):
    """每档全覆盖：枚举里每个码都必须有可复现的触发用例（防"枚举写了没实现"）。"""
    cases = {
        "unknown_wildcard": ("CREATE TABLE s AS SELECT * FROM raw_u", "postgres", {}),
        "unknown_type": ("CREATE TABLE s AS SELECT zz FROM raw_a JOIN raw_b ON raw_a.id = raw_b.id",
                         "postgres", {"raw_a": {"id": "unknown"}, "raw_b": {"id": "unknown"}}),
        "positional_union": ("CREATE TABLE m AS SELECT id AS a FROM raw_x "
                             "UNION ALL SELECT id FROM raw_y", "postgres",
                             {"raw_x": {"id": "unknown"}, "raw_y": {"id": "unknown"}}),
        "arity_mismatch": ("INSERT INTO s (c1) SELECT a, b FROM raw_g", "postgres",
                           {"raw_g": {"a": "unknown", "b": "unknown"}, "s": {"c1": "unknown"}}),
        "skipped_merge_branch": ("MERGE INTO mart_inv t USING stage_inv s ON t.id = s.id "
                                 "WHEN MATCHED THEN DELETE", "tsql", MERGE_SCHEMAS),
        "UNSUPPORTED_DYNAMIC_SQL": ("EXEC('SELECT inv_id FROM raw_inv')", "tsql", {}),
        "PARSE_ERROR": ("SELEC FROM WHERE", "postgres", {}),
        "recursion_limit": ("", "postgres", {}),  # 见下方真实构造
        "dialect_defaulted": ("", "postgres", {}),  # loader 侧（见上方 dialect 用例）
        "no_source_columns": ("CREATE TABLE m AS SELECT 1 AS id", "postgres", {}),
        "wildcard_expanded": ("CREATE TABLE s AS SELECT * FROM raw_s", "postgres",
                              {"raw_s": {"a": "unknown"}}),
        "schema_overridden": ("", "postgres", {}),  # loader 侧（见 test_m1_loader）
        "unsupported_stored_procedure": (
            "CREATE PROCEDURE p AS BEGIN INSERT INTO mart_x (id) SELECT id FROM raw_x; END",
            "tsql", {}),
        "unsupported_write_statement": ("UPDATE mart_x SET v = v + 1", "postgres",
                                       {"mart_x": {"v": "unknown"}}),
    }
    # recursion_limit 用真实构造（嵌套 20 层 > §4.7 上限 16）
    deep = "SELECT id FROM raw_x"
    for i in range(20):
        deep = f"SELECT id FROM ({deep}) d{i}"
    cases["recursion_limit"] = (f"CREATE TABLE m AS {deep}", "postgres",
                                {"raw_x": {"id": "unknown"}})

    produced = set()
    for code, (sql, dialect, schemas) in cases.items():
        if not sql:
            continue
        _, edges, diags = _run(sql, dialect, schemas)
        produced |= {e.reason_code for e in edges if e.reason_code}
        produced |= {d.reason_code for d in diags}

    # loader 侧：dialect_defaulted（无方言目录）+ cycle_detected（互引两张表）
    (tmp_path / "unsorted").mkdir()
    (tmp_path / "unsorted" / "a.sql").write_text(
        "CREATE TABLE t1 AS SELECT x FROM t2;\n"
        "CREATE TABLE t2 AS SELECT x FROM t1;\n", encoding="utf-8")
    produced |= {d.reason_code for d in load_corpus(tmp_path).diagnostics}

    # loader 侧：schema_overridden（外部 --schema 覆盖同名表）
    sch = tmp_path / "schema.sql"
    sch.write_text("CREATE TABLE t1 (x int, y int);", encoding="utf-8")
    produced |= {d.reason_code for d in load_corpus(tmp_path, sch).diagnostics}
    produced |= {d.reason_code for d in load_corpus(CORPUS).diagnostics}

    assert set(REASON_CODES) - produced == set(), sorted(set(REASON_CODES) - produced)


# ---------- golden g2 / g3（M3 验收；期望冻结留 M5） ----------

def _golden_edges(name: str):
    corpus = load_corpus(GOLDEN / name / "corpus")
    edges, diags = build_edges(corpus)
    return corpus, edges, diags


def test_golden_g2_unknown_wildcard_never_guesses():
    """g2：未知 schema 的 SELECT * → 只有 unknown_wildcard，一个列名都不猜。"""
    _, edges, diags = _golden_edges("g2")
    assert edges and all(e.kind == "unknown" for e in edges)
    assert {e.reason_code for e in edges} == {"unknown_wildcard"}
    assert all(e.approximate for e in edges)
    assert all(e.source_column is None and e.source_table is None for e in edges)
    assert any(d.reason_code == "unknown_wildcard" for d in diags)
    # 目标列名也不得被编造（用占位 `*`）
    assert {e.target_column for e in edges} == {"*"}


def test_golden_g3_insert_column_list_positional_mapping():
    """g3：INSERT (c2, c1) SELECT a, b → c2←a、c1←b（按清单位置，不按名字猜）。"""
    _, edges, _ = _golden_edges("g3")
    got = {(e.target_column, e.source_column, e.kind) for e in edges}
    assert ("c2", "a", "value") in got
    assert ("c1", "b", "value") in got
    assert ("c1", "a", "value") not in got  # 反例：按名字对齐才是错的
    assert ("c2", "b", "value") not in got


# ---------- CLI：零静默门接到退出码 4 + `grep -c unknown` 对账 ----------

def test_cli_reports_zero_silence_block_and_exits_0(capsys):
    rc = main(["lineage", str(CORPUS), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["zero_silence"]["passed"] is True
    assert payload["zero_silence"]["silent_statements"] == []
    assert payload["zero_silence"]["unregistered_reason_codes"] == []


def test_cli_grep_unknown_count_matches_unresolved_diagnostics(capsys):
    """DoD：`grep -c unknown` 与未解析计数一致（逐语句键集合对账）。"""
    assert main(["lineage", str(CORPUS), "--json"]) == 0
    text = capsys.readouterr().out
    payload = json.loads(text)

    # ① 字面 grep：JSON 文本里 kind=unknown 的边行数
    grep_count = sum(1 for line in text.splitlines() if '"kind": "unknown"' in line)
    unknown_edges = [e for e in payload["edges"] if e["kind"] == "unknown"]
    assert grep_count == len(unknown_edges) > 0

    # ② 每条 unknown 边都能在 diagnostics 里找到同键项
    diag_keys = {(d["file"], d["statement_index"], d["reason_code"])
                 for d in payload["diagnostics"]}
    for e in unknown_edges:
        f, i = e["statement_id"].rsplit("#", 1)
        assert (f, int(i), e["reason_code"]) in diag_keys, e

    # ③ 反向：不允许多出"没有对应 unknown 边"的边类诊断
    edge_keys = {(e["statement_id"].rsplit("#", 1)[0],
                  int(e["statement_id"].rsplit("#", 1)[1]), e["reason_code"])
                 for e in unknown_edges}
    for d in payload["diagnostics"]:
        if d["reason_code"] in EDGE_AND_DIAG_CODES:
            assert (d["file"], d["statement_index"], d["reason_code"]) in edge_keys, d


def test_cli_help_shows_m3_state(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "lineage" in capsys.readouterr().out
