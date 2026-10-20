# -*- coding: utf-8 -*-
"""稳定排序 + 序列化单一出口。口径 data/README.md §4.6（UTF-8 无 BOM、\n、indent=2）。"""
from __future__ import annotations

import json
import sys


def ensure_deterministic_stdio() -> None:
    """入口 reconfigure：cp1252 等 locale 下中文输出不崩（本机 -X utf8 掩盖的盲区）。"""
    for stream in (sys.stdout, sys.stderr):
        enc = getattr(stream, "encoding", "") or ""
        if enc.lower() not in ("utf-8", "utf8"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):
                pass


def dumps_json(obj) -> str:
    """确定性 JSON：ensure_ascii=False / indent=2 / \n（§4.6）。调用方先排序。"""
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
