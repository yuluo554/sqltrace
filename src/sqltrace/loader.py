# -*- coding: utf-8 -*-
"""M1 语料装载 + schema 推导。设计见 plan/03 §M1；口径 data/README.md §四。

- .gitignore 最小解析（嵌套 + 取反 + 跳过 .git/），被忽略文件进 corpus.ignored[] 带原因。
- 方言判定：一级目录名 ∈ DIALECTS → 该方言；否则默认 postgres 并记 dialect_defaulted 诊断（§4.5）。
- schema 推导：CREATE TABLE 直出；CTAS / CREATE VIEW ... AS SELECT 正向传播（类型 unknown，不编造）。
- 拓扑排序：语句按写→读依赖排序（同层按 文件+语句序号）；环报 cycle_detected（§4.2）。
- 失败路径：单文件语句数超 MAX_STATEMENTS_PER_FILE → 中止该文件 + 诊断（§4.7）。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .constants import (
    DIALECTS,
    DEFAULT_DIALECT,
    MAX_STATEMENTS_PER_FILE,
    REASON_CODES,
)
from .model import Corpus, Diagnostic, Statement

# 语句切分（M1 最小实现：按分号断句，字符串/注释感知由 M2 内核侧细化为按 AST 解析）
_SPLIT_RE = re.compile(r";\s*(?:\n|$)")

# DDL 识别
_CREATE_TABLE_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w]*|\"[^\"]+\"|\[[^\]]+\]|`[^`]+`)\s*\(",
    re.I,
)
_CTAS_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w]*|\"[^\"]+\"|\[[^\]]+\]|`[^`]+`)"
    r"(?:\s*\([^)]*\))?\s+AS\b",
    re.I | re.S,
)
_CREATE_VIEW_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([A-Za-z_][\w]*|\"[^\"]+\"|\[[^\]]+\]|`[^`]+`)",
    re.I,
)
# DDL 派生表（无显式列清单）：从 AS SELECT 顶层输出推导列名
_SELECT_ITEMS_RE = re.compile(r"^\s*SELECT\s+(.*?)\s+FROM\b", re.I | re.S)


def _norm_ident(raw: str) -> str:
    raw = raw.strip()
    if raw[:1] in "\"[`":
        return raw[1:-1]
    return raw


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    return sql


def _split_statements(sql: str) -> list[str]:
    parts = _SPLIT_RE.split(sql)
    return [p.strip() for p in parts if p.strip()]


class _Gitignore:
    """最小 .gitignore：逐目录叠加；只支持整名/目录/通配与 `!` 取反（M1 够用面）。"""

    def __init__(self, root: Path):
        self.root = root
        self.rules: list[tuple[Path, re.Pattern, bool]] = []  # (base, pattern, negate)
        self._collect(root)

    def _collect(self, base: Path) -> None:
        gi = base / ".gitignore"
        if gi.is_file():
            for line in gi.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                negate = line.startswith("!")
                if negate:
                    line = line[1:]
                if line.endswith("/"):
                    line = line.rstrip("/")
                    pat = re.escape(line) + r"(?:/|$)"
                else:
                    pat = re.escape(line).replace(r"\*\*/", r"(?:.*/)?").replace(r"\*", r"[^/]*") + r"(?:/|$)?"
                self.rules.append((base, re.compile(r"(?:^|/)" + pat + r"$"), negate))
        for d in sorted(base.iterdir()):
            if d.is_dir() and d.name not in (".git", ".hg", ".svn"):
                self._collect(d)

    def ignored(self, rel_parts: tuple[str, ...]) -> str | None:
        verdict: str | None = None
        base_rel = ()
        for base, pat, negate in self.rules:
            try:
                sub = Path(*rel_parts).relative_to(base.relative_to(self.root))
            except ValueError:
                continue
            rel = sub.as_posix()
            if pat.search(rel) or pat.search(rel_parts[-1]):
                verdict = "negated_by_gitignore" if negate else "gitignore"
        return verdict


def _dialect_for(rel: str, override: str | None = None) -> tuple[str, bool]:
    """方言判定（§4.5）：`--dialect` 显式指定 > 一级目录名 > 默认 postgres（记诊断）。"""
    if override:
        return override, False
    top = rel.split("/", 1)[0]
    if top in DIALECTS:
        return top, False
    return DEFAULT_DIALECT, True


def _derive_columns(ctas_body: str) -> list[str] | None:
    """从 AS SELECT 顶层 SELECT 列表推导输出列名（无别名取列名；取不到则 None）。"""
    m = _SELECT_ITEMS_RE.search(ctas_body)
    if not m:
        return None
    items = _split_top_commas(m.group(1))
    names: list[str] = []
    for it in items:
        alias = re.search(r"\bAS\s+([A-Za-z_][\w]*|\"[^\"]+\")\s*$", it, re.I)
        if alias:
            names.append(_norm_ident(alias.group(1)))
            continue
        plain = re.search(r"([A-Za-z_][\w]*)\s*$", it)
        if plain:
            names.append(plain.group(1))
        else:
            return None  # 复杂表达式无别名：不编造（schema 推导纪律）
    return names or None


def _split_top_commas(s: str) -> list[str]:
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def _parse_ddl(stmt: str) -> tuple[str, list[str]] | None:
    """返回 (table, columns)。CREATE TABLE 直读列名；CTAS/VIEW 从 AS SELECT 推导。"""
    m = _CREATE_TABLE_RE.match(stmt)
    if m:
        body = stmt[m.end():]
        # 截到首个未配对的右括号
        depth = 1
        end = 0
        for i, ch in enumerate(body):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        cols = []
        for item in _split_top_commas(body[:end]):
            item = _strip_comments(item).strip()
            if not item:
                continue
            first = re.match(
                r"(?:CONSTRAINT\s+\w+\s+)?(?:PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK|KEY|INDEX)\b",
                item, re.I,
            )
            if first:
                continue
            cm = re.match(r"(\"[^\"]+\"|\[[^\]]+\]|`[^`]+`|[A-Za-z_][\w]*)", item)
            if cm:
                cols.append(_norm_ident(cm.group(1)))
        return _norm_ident(m.group(1)), cols

    m = _CTAS_RE.match(stmt)
    if m:
        cols = _derive_columns(stmt[m.end():])
        if cols is not None:
            return _norm_ident(m.group(1)), cols
        return None

    m = _CREATE_VIEW_RE.match(stmt)
    if m:
        cols = _derive_columns(stmt[m.end():])
        if cols is not None:
            return _norm_ident(m.group(1)), cols
        return None
    return None


def _table_refs(sql: str) -> set[str]:
    """语句读到的表名（M1 近似：FROM/JOIN 后的裸标识符；字符串/列点号误报由 M2 AST 消除）。"""
    refs: set[str] = set()
    for m in re.finditer(
        r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w]*|\"[^\"]+\"|\[[^\]]+\]|`[^`]+`)", sql, re.I
    ):
        refs.add(_norm_ident(m.group(1)))
    return refs


def _writes_target(stmt: str) -> str | None:
    m = re.match(
        r"^\s*(?:INSERT\s+INTO|CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?)"
        r"([A-Za-z_][\w]*|\"[^\"]+\"|\[[^\]]+\]|`[^`]+`)",
        stmt, re.I,
    )
    if m:
        return _norm_ident(m.group(1))
    return None


def load_corpus(root: Path, schema_file: Path | None = None,
                dialect: str | None = None) -> Corpus:
    """装载语料目录为 Corpus（M1 最小闭环）。`dialect` = CLI `--dialect` 覆盖（§4.5）。"""
    corpus = Corpus()
    root = Path(root)
    ignore = _Gitignore(root)

    # ---- 文件清单（目录枚举 + .gitignore + sha256）----
    items: list[tuple[str, str, str]] = []
    for p in sorted(root.rglob("*.sql")):
        if any(part in (".git", ".hg", ".svn") for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        why = ignore.ignored(Path(rel).parts)
        if why:
            corpus.ignored.append({"path": rel, "reason": why})
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        items.append((rel, text, _sha256_text(text)))

    return _assemble_corpus(corpus, items, schema_file, dialect)


def load_corpus_from_texts(files, schema_file: Path | None = None,
                           dialect: str | None = None) -> Corpus:
    """从"已取好的文本"装载 Corpus（M5 git 模式：内容来自 `git show`，不切工作区）。

    `files` = `[(rel_path, text)]`，`rel_path` **相对语料根目录**（调用方已剥掉仓库前缀）、
    分隔符 `/`（§4.6）。与目录模式共用 `_assemble_corpus`——**两种 diff 模式喂同一内核**。
    """
    items = [(rel, text, _sha256_text(text)) for rel, text in sorted(files)]
    return _assemble_corpus(Corpus(), items, schema_file, dialect)


def _assemble_corpus(corpus: Corpus, items, schema_file: Path | None,
                     dialect: str | None) -> Corpus:
    """装载内核（目录 / git 两模式共用）：方言判定 + 语句切分 + schema 推导 + 拓扑排序。

    `items` = `[(rel_path, text, sha256)]`，顺序即 `corpus.files` 顺序（调用方已排序）。
    """
    # ---- 文件清单 + 语句切分（方言判定 §4.5 / 语句数上限 §4.7） ----
    stmts: list[Statement] = []
    for rel, text, sha in items:
        file_dialect, defaulted = _dialect_for(rel, dialect)
        if defaulted:
            corpus.diagnostics.append(Diagnostic(
                file=rel, statement_index=0,
                reason_code="dialect_defaulted",  # §4.2 专用码（M3 接线）
                message=f"dialect defaulted to {DEFAULT_DIALECT}",
                approximate=True,
            ))
        corpus.files.append({"path": rel, "sha256": sha, "dialect": file_dialect})

        raw_parts = _split_statements(text)
        if len(raw_parts) > MAX_STATEMENTS_PER_FILE:
            corpus.diagnostics.append(Diagnostic(
                file=rel, statement_index=MAX_STATEMENTS_PER_FILE,
                reason_code="PARSE_ERROR",
                message=f"statement count {len(raw_parts)} exceeds {MAX_STATEMENTS_PER_FILE}; file aborted",
            ))
            continue
        for idx, stmt in enumerate(raw_parts):
            stmts.append(Statement(file=rel, index=idx, sql=stmt, dialect=file_dialect))

    # ---- schema 推导 + 语句读写依赖 ----
    writes: dict[int, str] = {}
    reads: dict[int, set[str]] = {}
    for i, st in enumerate(stmts):
        clean = _strip_comments(st.sql)
        ddl = _parse_ddl(clean)
        if ddl:
            table, cols = ddl
            corpus.schemas[table] = {c: "unknown" for c in cols}
            writes[i] = table
            if _CTAS_RE.match(clean) or _CREATE_VIEW_RE.match(clean):
                reads[i] = _table_refs(clean)
        else:
            w = _writes_target(clean)
            if w:
                writes[i] = w
                reads[i] = _table_refs(clean)
            else:
                reads[i] = _table_refs(clean)

    # ---- 拓扑排序（完整依赖图：读表 → 一切写同表的语句；Kahn；环报 cycle_detected） ----
    n = len(stmts)
    write_idx: dict[str, list[int]] = {}
    for i in range(n):
        if i in writes:
            write_idx.setdefault(writes[i], []).append(i)

    deps_of: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for t in reads.get(i, ()):
            for j in write_idx.get(t, ()):
                if j != i:
                    deps_of[i].add(j)

    order: list[int] = []
    indeg = [len(deps_of[i]) for i in range(n)]
    dependents: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in deps_of[i]:
            dependents[j].add(i)
    # Kahn：同层按 (file, index) 升序（§4.6 拓扑同层序）
    import heapq
    heap = [(stmts[i].file, stmts[i].index, i) for i in range(n) if indeg[i] == 0]
    heapq.heapify(heap)
    while heap:
        _, _, i = heapq.heappop(heap)
        order.append(i)
        for j in sorted(dependents[i]):
            indeg[j] -= 1
            if indeg[j] == 0:
                heapq.heappush(heap, (stmts[j].file, stmts[j].index, j))
    if len(order) < n:  # 环：cycle_detected，环内语句保持文件序追加（不静默）
        cyclic = sorted((i for i in range(n) if i not in set(order)),
                        key=lambda i: (stmts[i].file, stmts[i].index))
        for i in cyclic:
            involved = sorted(reads.get(i, ()) & set(write_idx))
            corpus.diagnostics.append(Diagnostic(
                file=stmts[i].file, statement_index=stmts[i].index,
                reason_code="cycle_detected",
                message=f"table dependency cycle involves {involved or 'unknown tables'}",
            ))
            order.append(i)

    corpus.statements = [stmts[i] for i in order]

    # ---- 外部 schema 覆盖 ----
    if schema_file is not None and Path(schema_file).is_file():
        text = _strip_comments(Path(schema_file).read_text(encoding="utf-8", errors="replace"))
        for stmt in _split_statements(text):
            ddl = _parse_ddl(stmt)
            if ddl:
                table, cols = ddl
                had = table in corpus.schemas
                corpus.schemas[table] = {c: "unknown" for c in cols}
                # plan/01 模块①：覆盖必须留痕（不静默）
                corpus.diagnostics.append(Diagnostic(
                    file=Path(schema_file).as_posix(), statement_index=0,
                    reason_code="schema_overridden",
                    message=(f"external schema overrides `{table}` "
                             f"({'derived' if had else 'new'}, {len(cols)} column(s))"),
                ))

    # 诊断排序（§4.6）
    corpus.diagnostics.sort(key=lambda d: d.sort_key())
    return corpus


def iter_statements(corpus: Corpus):
    yield from corpus.statements


def _sha256_text(text: str) -> str:
    """语料文件 sha256 = **解码后文本**的 sha256（目录模式与 git 模式共用这一个出口）。

    不能哈希原始字节：`read_text` 走通用换行（CRLF→LF），git 模式拿到的是已解码文本；
    若目录模式哈希原始字节，同一棵树在两模式下 sha 不同（M5 实测缺陷）。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
