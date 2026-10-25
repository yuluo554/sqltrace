# -*- coding: utf-8 -*-
"""版本指针守门（SI-048）：README / release 台账里的**发布指针**必须等于当前版本。

背景（实测，2026-10-25）：`v0.1.2` 的 tag 树里 README 仍写「当前发布版 `v0.1.1`」，
安装行仍指 `releases/download/v0.1.1/sqltrace-0.1.1-...whl`，`release/SHA256SUMS`
也还是 v0.1.1 的两行；而 `v0.1.0` / `v0.1.1` 两版都指向自己。
⇒ 这是**本版引入的回归**，不是历史形态。用户从 `v0.1.2` 的 tag 树或 sdist 进去照
README 装，拿到的是 v0.1.1。

判据（三条都定位到**声明性那一行**，不做全文存在性判断 —— presence ≠ correctness）：

  ① README「当前发布版 `vX.Y.Z`」的 X.Y.Z == 当前版本；
  ② README 的 `releases/download/vX.Y.Z/sqltrace-X.Y.Z-...` == 当前版本（tag 段与
     文件名段**都要**等于；只比其中一段会被「tag 对、文件名旧」这种形态骗过）；
  ③ `release/SHA256SUMS` 若存在，**每一行**的文件名都必须含当前版本，不能有旧版本残留。

④ 是**门本身的负控**：喂合成的旧版本 README，三条必须都报错。没有这组，上面的
断言只证明「当前文件是对的」，不证明「这个门会红」。

版本源是 `pyproject.toml` 与 `src/sqltrace/__init__.py` 的一致性检查（两条都读，
不一致本身就红 —— 否则改了其中一处这套断言会自相矛盾）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"
INIT = REPO_ROOT / "src" / "sqltrace" / "__init__.py"
SUMS = REPO_ROOT / "release" / "SHA256SUMS"

PKG = "sqltrace"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pyproject_version(text: str) -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert m, "pyproject.toml 里找不到 project.version"
    return m.group(1)


def _init_version(text: str) -> str:
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    assert m, "src/sqltrace/__init__.py 里找不到 __version__"
    return m.group(1)


# ---------------------------------------------------------------- 审计函数
# 全部做成「吃文本、返回问题列表」的纯函数，负控才不会碰真实文件。

def audit_current_release(readme: str, version: str) -> list[str]:
    """① README 的「当前发布版 `vX.Y.Z`」指针。"""
    found = re.findall(r"当前发布版\s*`?v(\d+\.\d+\.\d+)`?", readme)
    if not found:
        return ["README 找不到「当前发布版 vX.Y.Z」声明 —— 该指针被删或改写了措辞"]
    return [
        f"README「当前发布版」= v{v}，期望 v{version}"
        for v in found
        if v != version
    ]


def audit_download_link(readme: str, version: str) -> list[str]:
    """② README 的 Release 下载链接：tag 段与文件名段都必须等于当前版本。"""
    problems: list[str] = []
    links = re.findall(
        r"releases/download/v(\d+\.\d+\.\d+)/" + re.escape(PKG) + r"-(\d+\.\d+\.\d+)-",
        readme,
    )
    if not links:
        return ["README 找不到 releases/download/vX.Y.Z/sqltrace-X.Y.Z-... 安装行"]
    for tag_v, file_v in links:
        if tag_v != version:
            problems.append(
                f"README 下载链接的 tag 段 = v{tag_v}，期望 v{version}"
            )
        if file_v != version:
            problems.append(
                f"README 下载链接的文件名段 = {PKG}-{file_v}-…，期望 {PKG}-{version}-…"
            )
    return problems


def audit_sums(text: str, version: str) -> list[str]:
    """③ release/SHA256SUMS 每一行的文件名都必须含当前版本。"""
    problems: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            problems.append(f"SHA256SUMS 行格式不对（少于两列）：{line[:60]}")
            continue
        name = parts[1].lstrip("*")
        if version not in name:
            problems.append(
                f"SHA256SUMS 条目 {name} 不含当前版本 {version}（指针落后一版）"
            )
    if not problems and not text.strip():
        problems.append("release/SHA256SUMS 存在但为空")
    return problems


# ---------------------------------------------------------------- 真文件断言

def test_pyproject_and_init_version_agree():
    """版本号两处必须一致 —— 否则下面三条指针无从判「当前」是哪一版。"""
    pj = _pyproject_version(_read(PYPROJECT))
    init = _init_version(_read(INIT))
    assert pj == init, (
        f"pyproject.toml version={pj} 与 __init__.__version__={init} 不一致"
    )


def test_readme_current_release_pointer_matches_version():
    """① —— README 的「当前发布版」必须等于当前版本。"""
    version = _pyproject_version(_read(PYPROJECT))
    problems = audit_current_release(_read(README), version)
    assert problems == [], "\n".join(problems)


def test_readme_download_link_matches_version():
    """② —— README 安装行的 tag 段与文件名段都必须等于当前版本。"""
    version = _pyproject_version(_read(PYPROJECT))
    problems = audit_download_link(_read(README), version)
    assert problems == [], "\n".join(problems)


def test_release_sums_match_version():
    """③ —— release/SHA256SUMS 不残留旧版本条目。"""
    version = _pyproject_version(_read(PYPROJECT))
    if not SUMS.exists():
        pytest.skip("release/SHA256SUMS 不存在（本仓当前形态）")
    problems = audit_sums(_read(SUMS), version)
    assert problems == [], "\n".join(problems)


# ---------------------------------------------------------------- ④ 负控
# 每条都喂「上一版」的合成输入，必须报错；再喂当前版，必须干净。
# 这组证明门会红，而不是恒绿。

def test_negative_control_current_release_detects_stale():
    stale = "状态：**当前发布版 `v0.9.8`**（旧）"
    assert audit_current_release(stale, "0.9.9") != []
    assert audit_current_release("状态：**当前发布版 `v0.9.9`**", "0.9.9") == []


def test_negative_control_current_release_detects_missing():
    """把指针删掉也是缺陷（否则「删掉声明」能让门变绿）。"""
    assert audit_current_release("状态：已发布", "0.9.9") != []


def test_negative_control_download_link_detects_stale_tag():
    stale = (
        "pip install https://github.com/o/r/releases/download/v0.9.8/"
        f"{PKG}-0.9.9-py3-none-any.whl"
    )
    problems = audit_download_link(stale, "0.9.9")
    assert any("tag 段" in p for p in problems), problems
    assert not any("文件名段" in p for p in problems), problems


def test_negative_control_download_link_detects_stale_filename():
    """tag 对、文件名旧 —— 必须单独抓出来（只比 tag 的门会漏这种）。"""
    stale = (
        "pip install https://github.com/o/r/releases/download/v0.9.9/"
        f"{PKG}-0.9.8-py3-none-any.whl"
    )
    problems = audit_download_link(stale, "0.9.9")
    assert any("文件名段" in p for p in problems), problems
    assert not any("tag 段" in p for p in problems), problems


def test_negative_control_sums_detects_stale_entry():
    stale = (
        "aaa  sqltrace-0.9.9-py3-none-any.whl\n"
        "bbb  sqltrace-0.9.8.tar.gz\n"
    )
    problems = audit_sums(stale, "0.9.9")
    assert len(problems) == 1, problems
    assert "0.9.8" in problems[0]


def test_negative_control_sums_detects_empty():
    assert audit_sums("", "0.9.9") != []
