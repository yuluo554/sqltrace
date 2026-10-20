# -*- coding: utf-8 -*-
"""M5 lineage diff 闸门 + impact + golden 回归。

设计见 plan/03 §M5；退出码 data/README.md §4.4；diff / impact / golden 口径 §4.9。

- `diff --base <git-ref|dir>`：git 模式用 `git show <ref>:<path>` **只读**取基线语料（不切工作区），
  双目录模式直读两目录；**两种模式喂同一个装载内核**（`loader._assemble_corpus`）。
- 边级 diff：ADDED / REMOVED / CHANGED —— CHANGED = 同 `(target_table, target_column, kind)`
  的**来源集合**变化（§4.9 规则 1–3）。
- `impact <table>.<column>`：上游来源（边集反向闭包）+ 下游消费者（边集正向闭包，穿透中间表）
  + **表级读者**（`corpus.reads`，K13：纯 `SELECT` 不产边但它是消费者，不得从边集反推）。
- `golden`：五条期望侧冻结校验；期望 JSON 由口径人工推导（plan/04 §二），**不由实现反向生成**。
- 门复用：diff 与 golden 的**每一份**语料都跑同一份 `zero_silence_violations` + `assert_reason_codes`。

依赖方向：diffgate → census / core / fallback / loader / model / constants；本模块不被它们 import。
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .census import census
from .constants import (
    EXIT_INTERNAL,
    EXIT_NONBREAKING,
    EXIT_OK,
    EXIT_REMOVED,
    EXIT_USAGE,
    RECURSION_LIMIT,
)
from .core import build_edges
from .fallback import assert_reason_codes, zero_silence_violations
from .loader import load_corpus, load_corpus_from_texts
from .model import Corpus

GOLDEN_DIRS = ("g1", "g2", "g3", "g4", "g5")


class BaseUsageError(Exception):
    """基线取不到（`--base` 目录不存在 / git ref 不存在 / 不在 git 仓库内 / 无 git）→ §4.4 退出码 `3`。"""


# ---------------------------------------------------------------- 基线加载（两模式 → 同一内核）

def _git(root: Path, *args) -> tuple[int, bytes]:
    """只读 git 调用（`-C` 换目录，`core.quotepath=false` 让非 ASCII 路径不被转义）。"""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", "-C", str(root), *args],
            capture_output=True,
        )
    except OSError as exc:  # git 不存在
        raise BaseUsageError(f"git 不可用（{type(exc).__name__}）：`--base` 只能用目录模式")
    return proc.returncode, proc.stdout


def _repo_prefix(root: Path) -> str:
    """root 相对仓库根的路径前缀（**无尾斜杠**；root 即仓库根时为空串）。

    `git rev-parse --show-prefix` 带尾斜杠（`data/corpus/`），拼路径前必须剥掉——
    否则 `git show <ref>:data/corpus//x.sql` 退出码 128（§4.9 规则 4）。
    """
    rc, out = _git(root, "rev-parse", "--show-prefix")
    if rc != 0:
        raise BaseUsageError(f"`{root}` 不在 git 仓库内：git 模式不可用（改用目录模式）")
    return out.decode("utf-8", "replace").strip().rstrip("/")


def _git_files(root: Path, ref: str, prefix: str) -> list:
    """基线语料的 `[(rel_path, text)]`：`ls-tree` 列文件 + 逐个 `git show` 读内容。

    用 `ls-tree -z` 取原始路径（防转义），只收 `.sql`；`rel_path` 相对语料根目录。
    """
    rc, out = _git(root, "ls-tree", "-r", "-z", "--name-only", ref, "--", ".")
    if rc != 0:
        raise BaseUsageError(f"git ref `{ref}` 取不到（`git ls-tree` 退出码 {rc}）")
    files: list = []
    for raw in out.decode("utf-8", "replace").split("\0"):
        if not raw or not raw.endswith(".sql"):
            continue
        pathspec = f"{prefix}/{raw}" if prefix else raw
        rc2, blob = _git(root, "show", f"{ref}:{pathspec}")
        if rc2 != 0:
            raise BaseUsageError(f"`git show {ref}:{pathspec}` 失败（退出码 {rc2}）")
        files.append((raw, blob.decode("utf-8", "replace")))
    return files


def load_base(root: Path, base: str, dialect: str | None = None) -> tuple:
    """加载 diff 基线 → `(corpus, kind)`；`kind ∈ {"git", "dir"}`。

    判据：`base` 是存在的目录 → 目录模式；否则当 git ref。ref 不存在 = 使用错误（§4.4）。
    """
    p = Path(base)
    if p.is_dir():
        return load_corpus(p, None, dialect), "dir"

    rc, _ = _git(root, "rev-parse", "--verify", "--quiet", base)
    if rc != 0:
        raise BaseUsageError(f"`--base {base}` 既不是目录也不是存在的 git ref")
    prefix = _repo_prefix(root)
    return load_corpus_from_texts(_git_files(root, base, prefix), None, dialect), "git"


# ---------------------------------------------------------------- 边级 diff（§4.9 规则 1–3）

def _src_name(e) -> str | None:
    """来源身份：`table.column`；`unknown` 边（无来源表）记 `None`（不编造）。"""
    if e.source_table is None:
        return None
    return f"{e.source_table}.{e.source_column}"


def _src_key(s):
    """来源排序键：`None`（unknown 边）在前，其余按码点升序（§4.9 规则 3）。"""
    return (s is not None, s or "")


def _groups(edges) -> dict:
    """按 `(target_table, target_column, kind)` 归组 → 来源集合 + 语句集合。"""
    out: dict = {}
    for e in edges:
        key = (e.target_table, e.target_column, e.kind)
        g = out.setdefault(key, {"sources": set(), "statements": set()})
        g["sources"].add(_src_name(e))
        g["statements"].add(e.statement_id)
    return out


def _edge_node(key) -> dict:
    table, column, kind = key
    return {"target": f"{table}.{column}", "kind": kind}


def _added_or_removed(key, g) -> dict:
    d = _edge_node(key)
    d["sources"] = sorted(g["sources"], key=_src_key)
    d["statements"] = sorted(g["statements"])
    return d


def _changed(key, b, c) -> dict:
    d = _edge_node(key)
    d["base_sources"] = sorted(b["sources"], key=_src_key)
    d["current_sources"] = sorted(c["sources"], key=_src_key)
    d["base_statements"] = sorted(b["statements"])
    d["current_statements"] = sorted(c["statements"])
    return d


def diff_edges(base_edges, current_edges) -> dict:
    """ADDED / REMOVED / CHANGED（§4.9 规则 1–3）；三节各自按 `(表, 列, kind)` 升序。"""
    b = _groups(base_edges)
    c = _groups(current_edges)
    added: list = []
    removed: list = []
    changed: list = []
    for key in sorted(c):
        if key not in b:
            added.append(_added_or_removed(key, c[key]))
        elif b[key]["sources"] != c[key]["sources"]:
            changed.append(_changed(key, b[key], c[key]))
    for key in sorted(b):
        if key not in c:
            removed.append(_added_or_removed(key, b[key]))
    return {"added": added, "removed": removed, "changed": changed}


def diff_exit_code(changes: dict) -> int:
    """§4.4：有 `REMOVED` → `1`；仅 `ADDED`/`CHANGED` → `2`；无变化 → `0`。"""
    if changes["removed"]:
        return EXIT_REMOVED
    if changes["added"] or changes["changed"]:
        return EXIT_NONBREAKING
    return EXIT_OK


# ---------------------------------------------------------------- impact

def _split_target(target: str):
    """`<table>.<column>` → `(table, column)`；表名是裸名（§4.8 K8），故切最后一个点。"""
    if "." not in target:
        return None
    table, column = target.rsplit(".", 1)
    if not table or not column:
        return None
    return table, column


def _graphs(edges) -> tuple:
    """边集 → `(正向 source→target, 反向 target→source)`；`unknown` 边无来源表，不入图。"""
    fwd: dict = {}
    back: dict = {}
    for e in edges:
        src = _src_name(e)
        if src is None:
            continue
        tgt = f"{e.target_table}.{e.target_column}"
        if src == tgt:  # 自环（自更新）不进闭包，否则自身恒可达
            continue
        fwd.setdefault(src, set()).add(tgt)
        back.setdefault(tgt, set()).add(src)
    return fwd, back


def _closure(start: str, adj: dict, limit: int) -> dict:
    """BFS 闭包 `{node: depth}`（depth 从 1 起）；`limit` = §4.7 展开层数上限，兼防环。"""
    seen = {start: 0}
    frontier = [start]
    depth = 0
    while frontier and depth < limit:
        depth += 1
        nxt: list = []
        for n in frontier:
            for m in sorted(adj.get(n, ())):
                if m not in seen:
                    seen[m] = depth
                    nxt.append(m)
        frontier = nxt
    seen.pop(start, None)
    return seen


def _known_tables(corpus: Corpus) -> set:
    """血缘图里的已知表集合（schema / 写者台账 / 读者台账）——`impact` 打错表名的守卫。"""
    known = set(corpus.schemas)
    known |= {t for t in corpus.write_targets.values() if t}
    for refs in corpus.reads.values():
        known |= set(refs)
    return known


def impact(corpus: Corpus, edges, target: str) -> dict:
    """`impact <table>.<column>` 报表（§4.9 规则 5–7）。

    返回 `dict`（JSON 友好）；表名不在血缘图中 → 抛 `BaseUsageError`（退出码 `3`，防打错字得空结果）。
    """
    parts = _split_target(target)
    if parts is None:
        raise BaseUsageError(f"目标 `{target}` 不是 `<table>.<column>` 形态")
    table, _column = parts
    if table not in _known_tables(corpus):
        raise BaseUsageError(
            f"目标表 `{table}` 不在本目录血缘图中（表名必须是裸名，§4.8 K8）")

    node = f"{table}.{_column}"
    fwd, back = _graphs(edges)
    up = _closure(node, back, RECURSION_LIMIT)
    down = _closure(node, fwd, RECURSION_LIMIT)

    reachable = set(down) | {node}
    final = sorted(n for n in down if not (fwd.get(n, set()) & reachable))

    affected = sorted({t.rsplit(".", 1)[0] for t in {node} | set(down)})
    # 穿透的中间表 = 下游列所在的表里**既不是目标表也不是汇点**的那些（§4.9 规则 6 的机械判据）
    sink_tables = {n.rsplit(".", 1)[0] for n in final}
    intermediate = sorted({n.rsplit(".", 1)[0] for n in down} - sink_tables - {table})
    reading: list = []
    for stmt in corpus.statements:
        read = set(corpus.reads.get(stmt.statement_id, ()))
        for t in affected:
            if t in read:
                reading.append({"table": t, "file": stmt.file,
                                "statement_index": stmt.index, "dialect": stmt.dialect})
    reading.sort(key=lambda r: (r["table"], r["file"], r["statement_index"]))

    def _nodes(d):
        return [{"target": n, "depth": d[n]} for n in sorted(d, key=lambda n: (d[n], n))]

    return {
        "target": node,
        "upstream_sources": _nodes(up),
        "downstream_consumers": _nodes(down),
        "final_consumers": final,
        "max_depth": max(down.values()) if down else 0,
        "intermediate_tables": intermediate,
        "affected_tables": affected,
        # K13：表级读者取自 corpus.reads——纯 SELECT 不产边但它是消费者，不得从边集反推
        "reading_statements": reading,
    }


# ---------------------------------------------------------------- 输出（Markdown 评论块 + 一行摘要）

def _md_table(rows: list, cols: list) -> list:
    """Markdown 表（空行集给「（无）」）；单元格内换行用 `<br>`。"""
    if not rows:
        return ["（无）"]
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    out.extend("| " + " | ".join(cells) + " |" for cells in rows)
    return out


def _cells(items) -> str:
    """来源/语句列表 → 单元格文本；`None`（unknown 边的空来源）显式写成 `unknown`。"""
    got = [f"`{s}`" if s is not None else "`unknown`" for s in items]
    return "<br>".join(got) if got else "（无）"


def render_diff_markdown(payload: dict, version: str = "") -> str:
    """diff 的 Markdown 评论块（可直接贴 PR）；末尾 Mermaid 为**附加**块（plan/03 §M5）。"""
    ch = payload["changes"]
    title = "# 血缘 diff" + (f" · sqltrace {version}" if version else "")
    lines = [
        title,
        "",
        f"> 基线（{payload['base']['kind']}）：{payload['base']['ref']}"
        f" → 当前：{payload['current']['ref']}。退出码 {payload['summary']['exit_code']}。",
        "> 事实报表；口径：`data/README.md` §4.9 / §4.4。",
        "",
        "## 摘要",
        "",
        "| 类型 | 条数 |",
        "| --- | --- |",
        f"| REMOVED（破坏性） | {payload['summary']['removed']} |",
        f"| ADDED | {payload['summary']['added']} |",
        f"| CHANGED | {payload['summary']['changed']} |",
        "",
        "## REMOVED",
        "",
    ]
    lines += _md_table(
        [(f"`{r['target']}`", r["kind"], _cells(r["sources"]), _cells(r["statements"]))
         for r in ch["removed"]],
        ["目标", "kind", "原来源", "语句"],
    )

    lines += ["", "## ADDED", ""]
    lines += _md_table(
        [(f"`{r['target']}`", r["kind"], _cells(r["sources"]), _cells(r["statements"]))
         for r in ch["added"]],
        ["目标", "kind", "来源", "语句"],
    )

    lines += ["", "## CHANGED", ""]
    lines += _md_table(
        [(f"`{r['target']}`", r["kind"], _cells(r["base_sources"]), _cells(r["current_sources"]))
         for r in ch["changed"]],
        ["目标", "kind", "基线来源", "当前来源"],
    )

    # Mermaid：附加块（removed 用虚线，added/changed 用实线）
    pairs: set = set()
    for r in ch["removed"]:
        pairs |= {(s, r["target"], "removed") for s in r["sources"] if s is not None}
    for r in ch["added"]:
        pairs |= {(s, r["target"], "added") for s in r["sources"] if s is not None}
    for r in ch["changed"]:
        pairs |= {(s, r["target"], "added") for s in r["current_sources"] if s is not None}
    if pairs:
        lines += ["", "```mermaid", "graph LR"]
        for s, t, kind in sorted(pairs):
            arrow = "-.->" if kind == "removed" else "-->"
            lines.append(f"  {s.replace('.', '_')}[{s}] {arrow} {t.replace('.', '_')}[{t}]")
        lines.append("```")
    return "\n".join(lines) + "\n"


def diff_summary(payload: dict) -> str:
    s = payload["summary"]
    return (f"REMOVED {s['removed']} / ADDED {s['added']} / CHANGED {s['changed']} "
            f"（退出码 {s['exit_code']}）")


def render_impact_text(report: dict, version: str = "") -> str:
    """`impact` 的人读输出（非 JSON 模式）。"""
    lines = [
        f"sqltrace {version}: impact `{report['target']}` — "
        f"上游 {len(report['upstream_sources'])} / 下游 {len(report['downstream_consumers'])} / "
        f"最终消费者 {len(report['final_consumers'])} / 穿透层数 {report['max_depth']}。",
    ]
    if report["upstream_sources"]:
        lines.append("上游来源：" + ", ".join(
            f"{r['target']}（第 {r['depth']} 层）" for r in report["upstream_sources"]))
    if report["downstream_consumers"]:
        lines.append("下游消费者：" + ", ".join(
            f"{r['target']}（第 {r['depth']} 层）" for r in report["downstream_consumers"]))
    if report["final_consumers"]:
        lines.append("最终消费者：" + ", ".join(report["final_consumers"]))
    if report["reading_statements"]:
        lines.append("表级读者（§4.9 K13 口径）：" + ", ".join(
            f"`{r['table']}`←`{r['file']}#{r['statement_index']}`"
            for r in report["reading_statements"]))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- golden 期望侧校验

@dataclass
class GoldenResult:
    """一条 golden 的校验结果（若干子检查）。"""

    name: str
    checks: list = field(default_factory=list)  # [(check_name, ok, detail)]

    @property
    def ok(self) -> bool:
        return all(ok for _n, ok, _d in self.checks)

    def failures(self) -> list:
        return [(n, d) for n, ok, d in self.checks if not ok]


def _triples(edges) -> set:
    return {(f"{e.target_table}.{e.target_column}", _src_name(e), e.kind) for e in edges}


def _golden_lineage(spec: dict, edges) -> tuple:
    """期望边集 = `{target, source, kind}` 的**精确集合**（口径人工推导，不含实现风味字段）。"""
    want = {(e["target"], e.get("source"), e["kind"]) for e in spec["edges"]}
    got = _triples(edges)
    if want == got:
        return True, f"{len(got)} 条边与期望一致"
    return False, f"缺 {sorted(want - got)}；多 {sorted(got - want)}"


def _golden_lineage_forbid(spec: dict, edges) -> tuple:
    banned = {(e["target"], e.get("source"), e["kind"]) for e in spec["forbid"]}
    hit = sorted(banned & _triples(edges))
    return (not hit), (f"禁止边未被产出（{len(banned)} 条）" if not hit else f"产出禁止边 {hit}")


def _golden_census(spec: dict, corpus, edges) -> tuple:
    report = census(corpus, edges)
    bad: list = []
    if "orphan" in spec and report.orphan != sorted(spec["orphan"]):
        bad.append(f"orphan {report.orphan} != {sorted(spec['orphan'])}")
    if "write_only" in spec and report.write_only != sorted(spec["write_only"]):
        bad.append(f"write_only {report.write_only} != {sorted(spec['write_only'])}")
    if "multi_writer" in spec:
        want = [{"table": m["table"], "writers": [tuple(w) for w in m["writers"]]}
                for m in spec["multi_writer"]]
        got = [{"table": m["table"], "writers": [(r.file, r.index) for r in m["writers"]]}
               for m in report.multi_writer]
        if got != want:
            bad.append(f"multi_writer {got} != {want}")
    if report.edges_missing_writer:
        bad.append(f"台账自检 edges_missing_writer={report.edges_missing_writer}")
    return (not bad), ("普查五节与期望一致" if not bad else "；".join(bad))


def _golden_diff(spec: dict, dirpath: Path, dialect) -> tuple:
    base_dir = dirpath / spec["base"]
    cur_dir = dirpath / spec["current"]
    base_corpus = load_corpus(base_dir, None, dialect)
    cur_corpus = load_corpus(cur_dir, None, dialect)
    base_edges, _ = build_edges(base_corpus)
    cur_edges, _ = build_edges(cur_corpus)
    changes = diff_edges(base_edges, cur_edges)
    bad: list = []
    got_removed = {(r["target"], r["kind"]) for r in changes["removed"]}
    got_added = {(r["target"], r["kind"]) for r in changes["added"]}
    got_changed = {(r["target"], r["kind"]) for r in changes["changed"]}
    if "removed" in spec and got_removed != {(t, k) for t, k in spec["removed"]}:
        bad.append(f"removed {sorted(got_removed)} != {sorted(tuple(x) for x in spec['removed'])}")
    if "added" in spec and got_added != {(t, k) for t, k in spec["added"]}:
        bad.append(f"added {sorted(got_added)} != {sorted(tuple(x) for x in spec['added'])}")
    if "changed" in spec and got_changed != {(t, k) for t, k in spec["changed"]}:
        bad.append(f"changed {sorted(got_changed)} != {sorted(tuple(x) for x in spec['changed'])}")
    code = diff_exit_code(changes)
    if "exit_code" in spec and code != spec["exit_code"]:
        bad.append(f"exit_code {code} != {spec['exit_code']}")
    if "changed_sources" in spec:  # 换源断言：[target, kind, 基线来源, 当前来源]
        want = {tuple(tuple(x) if isinstance(x, list) else x for x in row)
                for row in spec["changed_sources"]}
        got = {(r["target"], r["kind"], tuple(r["base_sources"]), tuple(r["current_sources"]))
               for r in changes["changed"]}
        if got != want:
            bad.append(f"changed_sources {sorted(got)} != {sorted(want)}")
    return (not bad), ("diff 三态与退出码与期望一致" if not bad else "；".join(bad))


def _golden_impact(spec: dict, corpus, edges) -> tuple:
    report = impact(corpus, edges, spec["target"])
    bad: list = []
    if report["final_consumers"] != sorted(spec["final_consumers"]):
        bad.append(f"final_consumers {report['final_consumers']} != {sorted(spec['final_consumers'])}")
    if "max_depth" in spec and report["max_depth"] != spec["max_depth"]:
        bad.append(f"max_depth {report['max_depth']} != {spec['max_depth']}")
    if "downstream" in spec:
        want = {tuple(x) for x in spec["downstream"]}
        got = {(r["target"], r["depth"]) for r in report["downstream_consumers"]}
        if got != want:
            bad.append(f"downstream {sorted(got)} != {sorted(want)}")
    if "upstream" in spec:
        want = {tuple(x) for x in spec["upstream"]}
        got = {(r["target"], r["depth"]) for r in report["upstream_sources"]}
        if got != want:
            bad.append(f"upstream {sorted(got)} != {sorted(want)}")
    if "intermediate_tables" in spec:  # 「穿透 N 层中间表」的机械判据（§4.9 规则 6）
        if report["intermediate_tables"] != sorted(spec["intermediate_tables"]):
            bad.append(f"intermediate_tables {report['intermediate_tables']} "
                       f"!= {sorted(spec['intermediate_tables'])}")
    if "reading_tables" in spec:  # K13：表级读者取自 corpus.reads（纯 SELECT 也算）
        got = sorted({r["table"] for r in report["reading_statements"]})
        if got != sorted(spec["reading_tables"]):
            bad.append(f"reading_tables {got} != {sorted(spec['reading_tables'])}")
    return (not bad), ("impact 与期望一致" if not bad else "；".join(bad))


def gate_check(corpus: Corpus, edges, diags) -> tuple:
    """§4.2 规则 4 + 封闭枚举门（diff/golden 与 lineage/census 跑同一份，不得各判一套）。

    返回 `(passed, detail)`；`passed=False` 时调用方按 §4.4 退 `4`（内部一致性失败 = 缺陷）。
    """
    silent = zero_silence_violations(corpus.write_ids, edges, diags)
    codes = assert_reason_codes(edges, diags)
    bad = []
    if silent:
        bad.append(f"零静默门 FAIL：{silent}")
    if codes:
        bad.append(f"reason code 未登记：{codes}")
    return (not bad), ("零静默门 + 枚举守卫通过" if not bad else "；".join(bad))


GOLDEN_SPEC_KEYS = ("lineage", "census", "impact", "diff")


def run_golden(root: Path, dialect: str | None = None) -> tuple:
    """跑 `root` 下每条 golden（子目录含 `expected.json`）→ `([GoldenResult], 汇总退出码)`。

    汇总退出码：全绿 `0`；任一期望不符或门红 → `4`（§4.4 内部断言失败语义，§4.9 规则 8）。
    找不到任何 golden → `3`（使用错误，防"空跑全绿"）。

    期望 JSON 的顶层键必须落在 `GOLDEN_SPEC_KEYS` 内且**至少一个**——拼错键名不得静默通过
    （否则 `expected.json` 写坏会退化成"永远绿"的空判据）。
    """
    dirs = [p for p in sorted(root.iterdir()) if (p / "expected.json").is_file()]
    if not dirs:
        return [], EXIT_USAGE

    results: list = []
    for dirpath in dirs:
        spec = json.loads((dirpath / "expected.json").read_text(encoding="utf-8"))
        res = GoldenResult(name=dirpath.name)

        unknown_keys = [k for k in spec if k not in GOLDEN_SPEC_KEYS]
        if unknown_keys or not spec:
            res.checks.append((
                "spec", False,
                f"expected.json 顶层键非法 {unknown_keys}（只认 {list(GOLDEN_SPEC_KEYS)}，不能为空）"))
            results.append(res)
            continue

        corpus = load_corpus(dirpath / "corpus", None, dialect)
        edges, diags = build_edges(corpus)
        res.checks.append(("gate",) + gate_check(corpus, edges, diags))

        if "lineage" in spec:
            res.checks.append(("lineage",) + _golden_lineage(spec["lineage"], edges))
            if "forbid" in spec["lineage"]:
                res.checks.append(("lineage_forbid",) + _golden_lineage_forbid(spec["lineage"], edges))
        if "census" in spec:
            res.checks.append(("census",) + _golden_census(spec["census"], corpus, edges))
        if "impact" in spec:
            res.checks.append(("impact",) + _golden_impact(spec["impact"], corpus, edges))
        if "diff" in spec:
            res.checks.append(("diff",) + _golden_diff(spec["diff"], dirpath, dialect))
        results.append(res)

    code = EXIT_OK if all(r.ok for r in results) else EXIT_INTERNAL
    return results, code


def render_golden_text(results: list, version: str = "") -> str:
    """`golden` 的人读输出（逐条 + 子检查）。"""
    lines = [f"sqltrace {version}: golden 回归 {len(results)} 条"]
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        lines.append(f"  {mark}  {r.name}")
        for name, ok, detail in r.checks:
            if not ok:
                lines.append(f"        - {name}: {detail}")
    passed = sum(1 for r in results if r.ok)
    lines.append(f"  {passed}/{len(results)} 通过")
    return "\n".join(lines) + "\n"


def golden_to_dict(results: list) -> dict:
    """golden 结果的 JSON 形态（稳定排序；键序固定）。"""
    return {
        "golden": [
            {
                "name": r.name,
                "passed": r.ok,
                "checks": [{"name": n, "passed": ok, "detail": d} for n, ok, d in r.checks],
            }
            for r in results
        ],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.ok),
            "failed": [r.name for r in results if not r.ok],
        },
    }


# ---------------------------------------------------------------- CLI 载荷组装

def _rel_or_none(path: str) -> str | None:
    """§4.6：输出一律相对路径 + 分隔符 `/`；用户给绝对路径时只报计数不 echo 路径。

    Windows 上 `str(Path)` 用 `\\`，必须归一成 `/`，否则同一输入在两平台产出不同字节。
    """
    if path is None or os.path.isabs(path):
        return None
    return path.replace("\\", "/")


def diff_payload(version: str, base_corpus, base_kind: str, base_ref: str,
                 cur_corpus, cur_root: str, changes: dict,
                 base_gate: tuple, cur_gate: tuple) -> dict:
    """diff 的 JSON 载荷（键序固定；无时间戳、无绝对路径）。"""
    code = diff_exit_code(changes)
    return {
        "version": version,
        "mode": base_kind,
        "base": {
            "kind": base_kind,
            "ref": _rel_or_none(base_ref),
            "files": len(base_corpus.files),
            "statements": len(base_corpus.statements),
        },
        "current": {
            "ref": _rel_or_none(cur_root),
            "files": len(cur_corpus.files),
            "statements": len(cur_corpus.statements),
        },
        "changes": changes,
        "summary": {
            "added": len(changes["added"]),
            "removed": len(changes["removed"]),
            "changed": len(changes["changed"]),
            "exit_code": code,
        },
        "zero_silence": {
            "passed": base_gate[0] and cur_gate[0],
            "base": {"passed": base_gate[0], "detail": base_gate[1]},
            "current": {"passed": cur_gate[0], "detail": cur_gate[1]},
        },
    }