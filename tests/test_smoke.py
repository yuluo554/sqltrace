# -*- coding: utf-8 -*-
"""M0 骨架冒烟：命令树可跑、口径常量齐、确定性 JSON、零网络静态扫描。"""
import io
import json
import pathlib
import subprocess
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import shutil


def _which(name):
    return shutil.which(name)

from sqltrace import __version__  # noqa: E402
from sqltrace.cli import main  # noqa: E402
from sqltrace.constants import REASON_CODES, DIALECTS  # noqa: E402
from sqltrace.loader import load_corpus  # noqa: E402
from sqltrace.output import dumps_json  # noqa: E402
from sqltrace.model import Edge  # noqa: E402


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["--version"])
    assert ei.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_subcommands_placeholder_exit0():
    for argv in (["lineage", "."], ["census", "."], ["golden"]):
        assert main(argv) == 0


def test_cli_unknown_command_exits_usage():
    with pytest.raises(SystemExit) as ei:
        main(["no-such-command"])
    assert ei.value.code == 2  # argparse 语义


def test_constants_match_data_readme():
    """口径单点（K2）：constants.REASON_CODES 必须与 data/README.md §4.2 表逐行一致。"""
    import pathlib
    import re
    readme = pathlib.Path(__file__).resolve().parents[1] / "data" / "README.md"
    text = readme.read_text(encoding="utf-8")
    section = text.split("### 4.2 reason code 枚举", 1)[1].split("###", 1)[0]
    documented = re.findall(r"^\|\s*`([A-Za-z_][\w]*)`\s*\|", section, re.M)
    assert documented, "§4.2 表没解析出条目（判据为空）"
    assert set(documented) == set(REASON_CODES), (
        sorted(set(documented) ^ set(REASON_CODES)))
    assert DIALECTS == ("postgres", "snowflake", "bigquery", "tsql", "duckdb")


def test_edge_sort_key_deterministic(tmp_path):
    a = Edge("m.t", "c", "value", "r.s", "x", "x")
    b = Edge("m.t", "c", "control", "r.s", "k", "k")
    keys = sorted([a.sort_key(), b.sort_key()])
    assert keys[0] == b.sort_key()  # control < value（码点序）
    assert keys[1] == a.sort_key()


def test_loader_lists_files_sorted(tmp_path):
    (tmp_path / "b.sql").write_text("SELECT 1", encoding="utf-8")
    (tmp_path / "a.sql").write_text("SELECT 2", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.sql").write_text("SELECT 3", encoding="utf-8")
    corpus = load_corpus(tmp_path)
    assert [f["path"] for f in corpus.files] == ["a.sql", "b.sql", "sub/c.sql"]
    assert all(len(f["sha256"]) == 64 for f in corpus.files)


def test_dumps_json_format():
    text = dumps_json({"a": 1})
    assert text.endswith("\n") and "\r" not in text
    assert json.dumps(json.loads(text), ensure_ascii=False, indent=2) + "\n" == text


def test_no_network_imports():
    """零网络纪律（D8）：src/ 下不得出现网络客户端导入。"""
    banned = ("requests", "urllib", "http.client", "socket", "httpx", "aiohttp")
    for p in (SRC / "sqltrace").glob("*.py"):
        text = p.read_text(encoding="utf-8")
        for b in banned:
            assert b not in text, f"{p.name} 引用了网络模块 {b}"


@pytest.mark.skipif(_which("git") is None, reason="git 不在 PATH")
def test_layout_gate_passes():
    """布局门在仓库树上必须绿（这是它第一次被 CI 之外真调）。"""
    root = pathlib.Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, str(root / "tools" / "check_sprint_layout.py")],
        capture_output=True, text=True, encoding="utf-8", cwd=str(root),
    )
    assert r.returncode == 0, r.stdout + r.stderr
