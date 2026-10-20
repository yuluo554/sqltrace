# -*- coding: utf-8 -*-
"""M1 语料装载 + schema 推导（骨架占位）。设计见 plan/03 §M1。"""
from __future__ import annotations

from pathlib import Path

from .model import Corpus, Statement


def load_corpus(root: Path, schema_file: Path | None = None) -> Corpus:
    """装载语料目录为 Corpus。

    M0 骨架：只实现文件清单（排序 + sha256）与忽略项占位；
    .gitignore 解析 / DDL schema 推导 / 拓扑排序在 M1 落地。
    """
    corpus = Corpus()
    for p in sorted(root.rglob("*.sql")):
        rel = p.relative_to(root).as_posix()
        if any(part == ".git" for part in p.parts):
            corpus.ignored.append({"path": rel, "reason": "git_dir"})
            continue
        corpus.files.append({"path": rel, "sha256": _sha256(p), "dialect": "postgres"})
    return corpus


def iter_statements(corpus: Corpus):
    yield from corpus.statements


def _sha256(p: Path) -> str:
    import hashlib

    return hashlib.sha256(p.read_bytes()).hexdigest()
