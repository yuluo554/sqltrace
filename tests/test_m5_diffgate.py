# -*- coding: utf-8 -*-
"""M5 常驻测试：diff 闸门（ADDED/REMOVED/CHANGED + 退出码）/ impact 穿透 / golden 五条 / 确定性。

口径单点：data/README.md §4.4（退出码）+ §4.9（diff / impact / golden 判据）。
"""
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import sqltrace.cli as cli  # noqa: E402
import sqltrace.diffgate as diffgate  # noqa: E402
from sqltrace.cli import main  # noqa: E402
from sqltrace.constants import (  # noqa: E402
    EXIT_INTERNAL,
    EXIT_NONBREAKING,
    EXIT_OK,
    EXIT_REMOVED,
    EXIT_USAGE,
)
from sqltrace.core import build_edges  # noqa: E402
from sqltrace.diffgate import (  # noqa: E402
    BaseUsageError,
    diff_edges,
    diff_exit_code,
    impact,
    load_base,
    run_golden,
)
from sqltrace.loader import load_corpus, load_corpus_from_texts  # noqa: E402
from sqltrace.model import Corpus, Edge, Statement  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "corpus"
GOLDEN = REPO / "data" / "golden"
G5 = GOLDEN / "g5"


def _edges(sqls, schemas=None, dialect="postgres"):
    c = Corpus()
    c.statements = [Statement(file="t.sql", index=i, sql=s, dialect=dialect)
                    for i, s in enumerate(sqls)]
    if schemas:
        c.schemas.update(schemas)
    edges, diags = build_edges(c)
    return c, edges, diags


def _cli_json(argv):
    buf, err = io.StringIO(), io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, (json.loads(buf.getvalue()) if buf.getvalue().strip() else None), err.getvalue()


def _e(target_table, target_column, kind, source_table, source_column, expr="x", sid="t.sql#0"):
    return Edge(target_table, target_column, kind, source_table, source_column, expr,
                statement_id=sid)


# ---------- 边级 diff 三态（§4.9 规则 1–3） ----------

def test_diff_added_removed_changed_classification():
    base = [_e("m", "a", "value", "r", "x"), _e("m", "b", "value", "r", "y"),
            _e("m", "c", "control", "r", "k")]
    cur = [_e("m", "a", "value", "r", "x"),           # 不变
           _e("m", "c", "control", "r", "k2"),         # CHANGED（来源换了）
           _e("m", "d", "value", "r", "z")]            # ADDED
    ch = diff_edges(base, cur)
    assert [x["target"] for x in ch["added"]] == ["m.d"]
    assert [x["target"] for x in ch["removed"]] == ["m.b"]     # 消失
    assert [x["target"] for x in ch["changed"]] == ["m.c"]
    assert ch["changed"][0]["base_sources"] == ["r.k"]
    assert ch["changed"][0]["current_sources"] == ["r.k2"]


def test_diff_same_key_multiple_sources_set_change_is_changed():
    """同一 `(target, column, kind)` 多来源时，来源**集合**变化 = CHANGED（不是 ADDED/REMOVED）。"""
    base = [_e("m", "a", "value", "r", "x"), _e("m", "a", "value", "r", "y")]
    cur = [_e("m", "a", "value", "r", "x"), _e("m", "a", "value", "r", "z")]
    ch = diff_edges(base, cur)
    assert ch["added"] == [] and ch["removed"] == []
    assert len(ch["changed"]) == 1
    assert ch["changed"][0]["base_sources"] == ["r.x", "r.y"]
    assert ch["changed"][0]["current_sources"] == ["r.x", "r.z"]


def test_diff_kind_change_is_removed_plus_added_not_changed():
    """kind 变了 = 旧 key 消失 + 新 key 出现（key 含 kind，§4.9 规则 1）。"""
    base = [_e("m", "a", "value", "r", "x")]
    cur = [_e("m", "a", "control", "r", "x")]
    ch = diff_edges(base, cur)
    assert [(x["target"], x["kind"]) for x in ch["removed"]] == [("m.a", "value")]
    assert [(x["target"], x["kind"]) for x in ch["added"]] == [("m.a", "control")]
    assert ch["changed"] == []


def test_diff_unknown_edge_sorts_first_and_never_fabricates_source():
    """unknown 边无来源表 → 来源记 `None`（不编造表名），且排在具名来源之前（§4.9 规则 3）。"""
    base = [_e("m", "a", "unknown", None, None)]
    cur = [_e("m", "a", "unknown", None, None)]
    assert diff_edges(base, cur)["changed"] == []  # 同集合：None == None
    # kind 相同、来源集合从 {None} 变成 {r.x} → CHANGED，且 None 排在具名来源之前
    cur2 = [_e("m", "a", "unknown", "r", "x")]
    ch = diff_edges(base, cur2)
    assert ch["changed"][0]["base_sources"] == [None]
    assert ch["changed"][0]["current_sources"] == ["r.x"]
    # unknown 边 + 另一个具名来源：None 恒在首位
    ch2 = diff_edges([_e("m", "a", "unknown", None, None)],
                     [_e("m", "a", "unknown", None, None), _e("m", "a", "unknown", "r", "x")])
    assert ch2["changed"][0]["current_sources"] == [None, "r.x"]


def test_diff_nodes_sorted_by_table_column_kind():
    cur = [_e("z", "b", "value", "r", "x"), _e("a", "b", "value", "r", "x"),
           _e("a", "a", "value", "r", "x")]
    targets = [x["target"] for x in diff_edges([], cur)["added"]]
    assert targets == ["a.a", "a.b", "z.b"]


# ---------- 退出码（§4.4） ----------

def test_diff_exit_code_matrix():
    assert diff_exit_code({"added": [], "removed": [], "changed": []}) == EXIT_OK
    assert diff_exit_code({"added": [1], "removed": [], "changed": []}) == EXIT_NONBREAKING
    assert diff_exit_code({"added": [], "removed": [], "changed": [1]}) == EXIT_NONBREAKING
    # REMOVED 优先：只要有一条破坏性变更就是 1
    assert diff_exit_code({"added": [1], "removed": [1], "changed": [1]}) == EXIT_REMOVED


def test_diff_cli_exit_codes_dir_mode(tmp_path):
    root = tmp_path / "cur"
    base = tmp_path / "base"
    root.mkdir()
    base.mkdir()
    (base / "a.sql").write_text("CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n",
                                encoding="utf-8")
    # 无变化 → 0
    (root / "a.sql").write_text("CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n",
                                encoding="utf-8")
    rc, payload, _ = _cli_json(["diff", str(root), "--base", str(base), "--json"])
    assert rc == EXIT_OK and payload["summary"]["exit_code"] == EXIT_OK
    # 仅 ADDED → 2
    (root / "a.sql").write_text(
        "CREATE TABLE r (x int, y int);\nCREATE TABLE m AS SELECT x, y FROM r;\n", encoding="utf-8")
    rc, payload, _ = _cli_json(["diff", str(root), "--base", str(base), "--json"])
    assert rc == EXIT_NONBREAKING and payload["changes"]["added"]
    # 有 REMOVED → 1
    (root / "a.sql").write_text("CREATE TABLE r (x int);\n", encoding="utf-8")
    rc, payload, _ = _cli_json(["diff", str(root), "--base", str(base), "--json"])
    assert rc == EXIT_REMOVED and payload["changes"]["removed"]


def test_diff_cli_usage_error_on_missing_base(tmp_path):
    (tmp_path / "a.sql").write_text("CREATE TABLE r (x int);", encoding="utf-8")
    rc, _, err = _cli_json(["diff", str(tmp_path), "--base", "definitely-not-a-ref-or-dir"])
    assert rc == EXIT_USAGE and "既不是目录也不是存在的 git ref" in err


def test_diff_cli_usage_error_on_missing_root(tmp_path):
    missing = tmp_path / "nope"
    rc, _, err = _cli_json(["diff", str(missing), "--base", str(tmp_path)])
    assert rc == EXIT_USAGE and "语料目录不存在" in err


# ---------- 两模式喂同一内核（§4.9 规则 4） ----------

def test_git_and_dir_base_produce_identical_edges():
    """git 模式（`git show`）与目录模式在同一棵树同一点上必须产出**同一份边集**。

    用仓库内已提交的 `data/golden/g5/corpus`（v1）对照：dir 直读 vs git@HEAD。
    浅/脏工作区下 ref 取不到则跳过（不伪造通过）。
    """
    if not (REPO / ".git").exists():
        pytest.skip("非 git 工作区")
    proc = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", "HEAD"],
                          capture_output=True)
    if proc.returncode != 0:
        pytest.skip("HEAD 取不到（无提交）")
    # HEAD 树里该文件必须与工作区一致，否则两模式天然不同（跳过，不误判）
    proc2 = subprocess.run(
        ["git", "-C", str(REPO), "show", "HEAD:data/golden/g5/corpus/v1.sql"],
        capture_output=True)
    disk = (G5 / "corpus" / "v1.sql").read_bytes()
    if proc2.returncode != 0 or proc2.stdout != disk:
        pytest.skip("HEAD 的 v1.sql 与工作区不一致（本条只验两模式同源）")

    cur = load_corpus(G5 / "corpus", None, "postgres")
    git_base, kind = load_base(G5 / "corpus", "HEAD", "postgres")
    assert kind == "git"
    cur_edges, _ = build_edges(cur)
    git_edges, _ = build_edges(git_base)
    assert [e.sort_key() for e in git_edges] == [e.sort_key() for e in cur_edges]
    assert [f["sha256"] for f in git_base.files] == [f["sha256"] for f in cur.files]


def test_load_corpus_from_texts_matches_dir_mode(tmp_path):
    (tmp_path / "postgres").mkdir()
    (tmp_path / "postgres" / "a.sql").write_text(
        "CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n", encoding="utf-8")
    disk = load_corpus(tmp_path)
    texts = load_corpus_from_texts([
        ("postgres/a.sql", "CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n")])
    assert [f["path"] for f in texts.files] == [f["path"] for f in disk.files]
    assert [f["sha256"] for f in texts.files] == [f["sha256"] for f in disk.files]
    assert [f["dialect"] for f in texts.files] == [f["dialect"] for f in disk.files]
    de, _ = build_edges(disk)
    te, _ = build_edges(texts)
    assert [e.sort_key() for e in de] == [e.sort_key() for e in te]


def test_sha_normalized_across_line_endings(tmp_path):
    """两模式的 sha 必须同口径：**解码文本**的 sha，不是原始字节。

    CRLF 文件是判据：目录模式 `read_text` 走通用换行（CRLF→LF），git 模式拿到的是已解码文本。
    若目录模式哈希原始字节，同一棵树在两模式下 sha 不同 → `--base` 显式目录与 `--base <ref>`
    对同一点给出不同的 `files[].sha256`（M5 实测到的真实缺陷）。
    """
    lf_dir, crlf_dir = tmp_path / "lf", tmp_path / "crlf"
    lf_dir.mkdir()
    crlf_dir.mkdir()
    lf = "CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n"
    (lf_dir / "a.sql").write_text(lf, encoding="utf-8", newline="\n")
    (crlf_dir / "a.sql").write_text(lf, encoding="utf-8", newline="\r\n")
    assert (crlf_dir / "a.sql").read_bytes() != (lf_dir / "a.sql").read_bytes()  # 判据非空

    a = load_corpus(lf_dir)
    b = load_corpus(crlf_dir)
    assert a.files[0]["sha256"] == b.files[0]["sha256"]
    # git 模式侧：文本直喂，必须与目录模式同 sha
    assert load_corpus_from_texts([("a.sql", lf)]).files[0]["sha256"] == a.files[0]["sha256"]


def test_git_mode_does_not_touch_worktree():
    """git 模式只读（`git show`），不得切工作区/写文件：跑完 `git status` 仍干净。"""
    if not (REPO / ".git").exists():
        pytest.skip("非 git 工作区")
    before = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                            capture_output=True).stdout
    load_base(G5 / "corpus", "HEAD", "postgres")
    after = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                           capture_output=True).stdout
    assert before == after


# ---------- golden g5：diff + impact（穿透两层） ----------

def test_golden_g5_diff_all_three_states_and_exit_code():
    base = load_corpus(G5 / "corpus", None, "postgres")
    cur = load_corpus(G5 / "corpus_v2", None, "postgres")
    be, _ = build_edges(base)
    ce, _ = build_edges(cur)
    ch = diff_edges(be, ce)
    assert [(x["target"], x["kind"]) for x in ch["removed"]] == [("leaf.nm", "value")]
    assert [(x["target"], x["kind"]) for x in ch["added"]] == [("mid1.cd", "value"),
                                                              ("mid2.cd", "value")]
    assert [(x["target"], x["kind"]) for x in ch["changed"]] == [("mid1.nm", "value")]
    # 换源（核心断言）：raw_src.nm → raw_src2.nm
    assert ch["changed"][0]["base_sources"] == ["raw_src.nm"]
    assert ch["changed"][0]["current_sources"] == ["raw_src2.nm"]
    assert diff_exit_code(ch) == EXIT_REMOVED


def test_golden_g5_impact_penetrates_two_intermediate_tables():
    c = load_corpus(G5 / "corpus", None, "postgres")
    edges, _ = build_edges(c)
    rep = impact(c, edges, "raw_src.nm")
    assert rep["final_consumers"] == ["leaf.nm"]
    assert rep["intermediate_tables"] == ["mid1", "mid2"]  # 穿透两层中间表
    assert rep["max_depth"] == 3
    assert {r["target"] for r in rep["downstream_consumers"]} == {"mid1.nm", "mid2.nm", "leaf.nm"}


def test_impact_target_must_be_in_graph(tmp_path):
    (tmp_path / "a.sql").write_text("CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n",
                                    encoding="utf-8")
    c = load_corpus(tmp_path, None, "postgres")
    edges, _ = build_edges(c)
    with pytest.raises(BaseUsageError):  # 打错表名不得静默给空结果（退出码 3）
        impact(c, edges, "typo_tbl.x")
    with pytest.raises(BaseUsageError):  # 缺列名
        impact(c, edges, "no_column")


def test_impact_cli_reports_readers_from_table_ledger():
    """K13：表级读者取自 `corpus.reads`——纯 SELECT 不产边但它是消费者。"""
    rc, payload, _ = _cli_json(["impact", "raw_cust.nm", str(CORPUS), "--json"])
    assert rc == EXIT_OK
    tables = {r["table"] for r in payload["impact"]["reading_statements"]}
    assert {"raw_cust", "stage_cust_enrich"} <= tables


def test_impact_cli_usage_error(tmp_path):
    rc, _, err = _cli_json(["impact", "bogus.x", str(tmp_path)])
    assert rc == EXIT_USAGE


# ---------- golden 五条一条命令全绿 ----------

def test_all_five_golden_green():
    results, code = run_golden(GOLDEN)
    assert [r.name for r in results] == ["g1", "g2", "g3", "g4", "g5"]
    assert all(r.ok for r in results), [(r.name, r.failures()) for r in results if not r.ok]
    assert code == EXIT_OK


def test_golden_cli_exit0_and_shape():
    rc, payload, _ = _cli_json(["golden", str(GOLDEN), "--json"])
    assert rc == EXIT_OK
    assert payload["summary"] == {"total": 5, "passed": 5, "failed": []}
    assert [g["name"] for g in payload["golden"]] == ["g1", "g2", "g3", "g4", "g5"]
    assert all(g["passed"] for g in payload["golden"])


def test_golden_missing_dir_is_usage_error(tmp_path):
    rc, _, err = _cli_json(["golden", str(tmp_path)])
    assert rc == EXIT_USAGE and "没有含 expected.json" in err


def test_golden_empty_expected_key_is_red_not_silent(tmp_path):
    """期望 JSON 写坏（顶层键拼错/为空）必须红——否则 golden 退化成"永远绿"的空判据。"""
    g = tmp_path / "gx"
    (g / "corpus").mkdir(parents=True)
    (g / "corpus" / "a.sql").write_text("CREATE TABLE r (x int);", encoding="utf-8")
    (g / "expected.json").write_text('{"lineag": {}}', encoding="utf-8")
    results, code = run_golden(tmp_path)
    assert code == EXIT_INTERNAL
    assert not results[0].ok and any(n == "spec" for n, _d in results[0].failures())


def test_golden_wrong_expectation_is_red(tmp_path):
    """期望值写错 → 必红（门不是空判据的阳性对照）。"""
    g = tmp_path / "gy"
    (g / "corpus").mkdir(parents=True)
    (g / "corpus" / "a.sql").write_text(
        "CREATE TABLE r (x int);\nCREATE TABLE m AS SELECT x FROM r;\n", encoding="utf-8")
    (g / "expected.json").write_text(json.dumps({
        "lineage": {"edges": [{"target": "m.zzz", "source": "r.x", "kind": "value"}]}
    }), encoding="utf-8")
    results, code = run_golden(tmp_path)
    assert code == EXIT_INTERNAL and not results[0].ok


def test_golden_expectations_are_hand_derived_not_implementation_dump():
    """期望 JSON 只含**口径字段** `target/source/kind`（无实现风味字段如 expr/statement_id）。

    期望侧由口径人工推导（plan/04 §二），不得由实现反向生成——实现字段漏进期望值就是循环论证。
    """
    allowed_node_keys = {"target", "source", "kind"}
    for p in sorted(GOLDEN.glob("g*/expected.json")):
        spec = json.loads(p.read_text(encoding="utf-8"))
        for e in spec.get("lineage", {}).get("edges", []):
            assert set(e) <= allowed_node_keys, (p.name, e)
        for e in spec.get("lineage", {}).get("forbid", []):
            assert set(e) <= allowed_node_keys, (p.name, e)


# ---------- 门复用（§4.9 规则 8） ----------

def test_diff_and_golden_reuse_same_gate(monkeypatch, tmp_path):
    """diff 跑同一份零静默门：门报违规 → 退出码 4（阳性对照），不掩盖成 diff 语义码。"""
    root, base = tmp_path / "cur", tmp_path / "base"
    root.mkdir()
    base.mkdir()
    (base / "a.sql").write_text("CREATE TABLE r (x int);\n", encoding="utf-8")
    (root / "a.sql").write_text("CREATE TABLE r (x int);\n", encoding="utf-8")
    monkeypatch.setattr(cli, "gate_check", lambda *a, **k: (False, "合成门红"))
    rc, payload, err = _cli_json(["diff", str(root), "--base", str(base), "--json"])
    assert rc == EXIT_INTERNAL
    assert payload["zero_silence"]["passed"] is False
    assert "门 FAIL" in err


def test_golden_gate_reuse_can_go_red(monkeypatch, tmp_path):
    """golden 同样跑零静默门：门红 → 条目 FAIL + 退 4。"""
    g = tmp_path / "gz"
    (g / "corpus").mkdir(parents=True)
    (g / "corpus" / "a.sql").write_text("CREATE TABLE r (x int);", encoding="utf-8")
    (g / "expected.json").write_text(
        '{"lineage": {"edges": []}}', encoding="utf-8")
    monkeypatch.setattr(diffgate, "gate_check", lambda *a, **k: (False, "合成门红"))
    results, code = run_golden(tmp_path)
    assert code == EXIT_INTERNAL
    assert not results[0].ok and any(n == "gate" for n, _d in results[0].failures())


# ---------- 确定性输出（§4.9 规则 9） ----------

def test_diff_json_two_runs_byte_identical():
    _, a, _ = _cli_json(["diff", str(G5 / "corpus_v2"), "--base", str(G5 / "corpus"), "--json"])
    _, b, _ = _cli_json(["diff", str(G5 / "corpus_v2"), "--base", str(G5 / "corpus"), "--json"])
    assert a == b
    assert a["changes"] == b["changes"]


def test_diff_markdown_two_runs_byte_identical_and_no_crlf():
    buf1, buf2 = io.StringIO(), io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(buf1):
        main(["diff", str(G5 / "corpus_v2"), "--base", str(G5 / "corpus"), "--md"])
    with contextlib.redirect_stdout(buf2):
        main(["diff", str(G5 / "corpus_v2"), "--base", str(G5 / "corpus"), "--md"])
    assert buf1.getvalue() == buf2.getvalue()
    assert "\r" not in buf1.getvalue()
    assert "REMOVED" in buf1.getvalue() and "mermaid" in buf1.getvalue()


def test_diff_sample_doc_is_real_output_and_deterministic():
    """`docs/diff-sample.json` 必须是真实运行输出（plan/00 §五承诺项，M5 DoD）。"""
    sample = REPO / "docs" / "diff-sample.json"
    assert sample.is_file(), "docs/diff-sample.json 缺失（M5 DoD 承诺项）"
    text = sample.read_text(encoding="utf-8")
    _, payload, _ = _cli_json(["diff", "data/golden/g5/corpus_v2",
                               "--base", "data/golden/g5/corpus", "--json"])
    assert text == json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    assert "\r" not in text and text.endswith("\n")
    assert "\\" not in text  # §4.6 路径分隔符统一 /，不 leak Windows 反斜杠


def test_diff_output_has_no_absolute_path(tmp_path):
    """§4.6：输出不得含绝对路径（用户给绝对路径时只报计数）。"""
    root, base = tmp_path / "cur", tmp_path / "base"
    root.mkdir()
    base.mkdir()
    (base / "a.sql").write_text("CREATE TABLE r (x int);\n", encoding="utf-8")
    (root / "a.sql").write_text("CREATE TABLE r (x int, y int);\n", encoding="utf-8")
    _, payload, _ = _cli_json(["diff", str(root), "--base", str(base), "--json"])
    assert payload["base"]["ref"] is None
    assert payload["current"]["ref"] is None


def test_golden_json_two_runs_byte_identical():
    _, a, _ = _cli_json(["golden", str(GOLDEN), "--json"])
    _, b, _ = _cli_json(["golden", str(GOLDEN), "--json"])
    assert a == b


def test_diff_json_key_order_fixed():
    """键序固定（§4.6）：顶层与 changes 三节的键序不得依赖 dict 插入顺序。"""
    _, payload, _ = _cli_json(["diff", str(G5 / "corpus_v2"),
                               "--base", str(G5 / "corpus"), "--json"])
    assert list(payload) == ["version", "mode", "base", "current", "changes",
                             "summary", "zero_silence"]
    assert list(payload["changes"]) == ["added", "removed", "changed"]
    assert list(payload["summary"]) == ["added", "removed", "changed", "exit_code"]