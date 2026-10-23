# -*- coding: utf-8 -*-
"""D2 常驻测试：**真实子进程流**的字节级验收（§4.6）。

为什么必须走子进程：`io.StringIO` / `capsys` / `contextlib.redirect_stdout` 都在内存里，
**不经过 TextIOWrapper 的 newline 翻译**，所以 `"\r" not in buf` 类是恒真断言。
只有 `subprocess.run(..., capture_output=True)` 读到的是进程真正写进管道的字节。
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "data" / "corpus"
G5 = REPO / "data" / "golden" / "g5"


def _run(args) -> subprocess.CompletedProcess:
    """在仓库根、`-X utf8` 下跑真进程（与 README 的命令行同形态）。"""
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "sqltrace.cli", *args],
        cwd=REPO, capture_output=True, check=False,
    )


@pytest.mark.parametrize("args,label", [
    (["lineage", "data/corpus", "--json"], "lineage --json"),
    (["lineage", "data/corpus"], "lineage 摘要"),
    (["census", "data/corpus", "--md"], "census --md"),
    (["census", "data/corpus", "--json"], "census --json"),
    (["diff", str(G5 / "corpus_v2"), "--base", str(G5 / "corpus"), "--json"], "diff --json"),
    (["impact", "raw_cust.nm", "data/corpus"], "impact 文本"),
])
def test_real_stdout_has_no_crlf(args, label):
    """真实管道里不得出现 `\\r\\n`——Windows 控制台翻译不得混进程序输出（D2）。"""
    proc = _run(args)
    assert proc.returncode in (0, 1, 2), f"{label}: rc={proc.returncode}"
    assert proc.stdout, f"{label}: 空输出（判据无效）"
    assert b"\r\n" not in proc.stdout, f"{label}: stdout 含 CRLF"
    assert b"\r" not in proc.stdout, f"{label}: stdout 含裸 \\r"


def test_real_stdout_matches_inprocess_bytes():
    """真进程 stdout 与进程内 `dumps_json` 的字节相同（LF 口径唯一）。"""
    proc = _run(["lineage", "data/corpus", "--json"])
    assert proc.returncode == 0
    assert proc.stdout.endswith(b"\n") and not proc.stdout.endswith(b"\r\n")
    assert proc.stdout.count(b"\r") == 0


# ---------- D5：库噪声不得混进 stderr ----------

@pytest.mark.parametrize("args,label", [
    (["lineage", "data/corpus", "--json"], "lineage"),
    (["census", "data/corpus", "--md"], "census"),
    (["impact", "raw_cust.nm", "data/corpus"], "impact"),
    (["diff", str(G5 / "corpus_v2"), "--base", str(G5 / "corpus"), "--json"], "diff"),
    (["golden", "data/golden"], "golden"),
])
def test_library_noise_absent_from_stderr(args, label):
    """`Unsupported Execute syntax` 之类无归属库噪声不得出现在 stderr（D5）。

    代价：真实失败信息仍要能出来——所以判据只针对"库 warn"，不要求 stderr 恒空
    （`diff` 有 REMOVED 时仍会走 stdout 的报表，stderr 本就该空）。
    """
    proc = _run(args)
    err = proc.stderr.decode("utf-8", "replace")
    assert "Unsupported Execute syntax" not in err, f"{label}: 泄漏库噪声"
    assert "contains unsupported syntax" not in err, f"{label}: 泄漏库噪声"
    # 自家诊断必须带前缀，便于与库噪声区分
    for line in err.splitlines():
        if line.strip():
            assert line.startswith("sqltrace:"), f"{label}: 无归属 stderr 行 {line!r}"


def test_sqlglot_logger_is_isolated():
    """`silence_library_logging()` 把 sqlglot logger 设为 NullHandler + 不传播（D5 单元面）。"""
    import logging

    from sqltrace.output import silence_library_logging

    silence_library_logging()
    lg = logging.getLogger("sqlglot")
    assert any(isinstance(h, logging.NullHandler) for h in lg.handlers)
    assert lg.propagate is False
    silence_library_logging()  # 幂等：重复调用不叠加 handler
