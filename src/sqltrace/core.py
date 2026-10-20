# -*- coding: utf-8 -*-
"""M2 确定性列血缘内核（骨架占位）。设计见 plan/03 §M2；口径 data/README.md §4.1。"""
from __future__ import annotations

from .model import Corpus


def build_edges(corpus: Corpus):
    """sqlglot AST + 自研 scope walker。M2 落地；不调用 sqlglot lineage()/qualify()。"""
    return [], []
