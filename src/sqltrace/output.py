# -*- coding: utf-8 -*-
"""稳定排序 + 序列化单一出口。口径 data/README.md §4.6（UTF-8 无 BOM、\n、indent=2）。"""
from __future__ import annotations

import json
import sys


def ensure_deterministic_stdio() -> None:
    """入口 reconfigure：cp1252 等 locale 下中文输出不崩（本机 -X utf8 掩盖的盲区），
    且**换行恒为 `\\n`**——§4.6 的「字节级一致」是程序写出的字节，不是控制台的翻译。

    Windows 上 `sys.stdout` 默认 `newline=None`（写 `\\n` 即译成 `\\r\\n`），D2 就是这里漏的。
    """
    for stream in (sys.stdout, sys.stderr):
        enc = getattr(stream, "encoding", "") or ""
        want_enc = enc.lower() not in ("utf-8", "utf8")
        # newline 无条件设：encoding 已是 utf-8 时仍要关掉 os.linesep 翻译
        kwargs = {"newline": "\n"}
        if want_enc:
            kwargs.update(encoding="utf-8", errors="replace")
        try:
            stream.reconfigure(**kwargs)
        except (AttributeError, ValueError):
            pass


def silence_library_logging() -> None:
    """把 sqlglot 的库噪声挡在自家 stderr 之外（D5）。

    实测：`sqlglot.parse_one("EXEC('...')", read="tsql")` 后调 `.sql()` 会
    `logger.warning("Unsupported Execute syntax")`，未配 logging ⇒ Python 的 lastResort
    handler 把它直接打到 stderr，四个子命令每次多一行。本工具的诊断一律走
    `diagnostics[]` + 自家 `sqltrace:` 前缀，库噪声没有归属，必须隔离。
    """
    import logging

    lg = logging.getLogger("sqlglot")
    if not any(isinstance(h, logging.NullHandler) for h in lg.handlers):
        lg.addHandler(logging.NullHandler())
    lg.propagate = False


def dumps_json(obj) -> str:
    """确定性 JSON：ensure_ascii=False / indent=2 / \n（§4.6）。调用方先排序。"""
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
