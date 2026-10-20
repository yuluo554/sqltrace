#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""布局门（方法论装订第②件）—— ai-tool-project-sprint 硬约束③。

判据集照抄 references/templates/check-sprint-layout.mjs（Python 重写，判据别改）。
已知假门族（自我参照真值源 / 表头定位 / 或关系 / 写死顺序 / 扫自由文本 /
标识符撞状态 token / 扫描面超长）在对应判据处有注释说明规避方式。

判据一律落**仓库内文件**（不读 git 元数据——浅克隆下 git tag/历史深度会翻转）。
退出码：0 全绿 / 1 有 FAIL。
门永不崩：被检查对象不存在报 FAIL 并继续；每轮打印"扫到了几个"（非空跑自证）。
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "data/README.md",
    "plan/00-README总览.md",
    "plan/01-题目文档.md",
    "plan/02-架构与技术选型.md",
    "plan/03-模块详设.md",
    "plan/04-数据计划.md",
    "plan/05-里程碑与发布.md",
    "plan/06-交付对标与决策.md",
]

# 装订行判据：三锚点同现一行，前瞻顺序无关（防"写死顺序"假红），单形态（防"或关系"放行残句）。
BINDING_LINE = re.compile(
    r"^>(?=.*ai-tool-project-sprint)(?=.*check_sprint_layout)(?=.*20\d{2}-\d{2}-\d{2}).*$", re.M
)

REQUIRED_SECTIONS = {
    "plan/00-README总览.md": ["文档索引", "决策记录", "承诺-证据台账", "里程碑"],
    "plan/01-题目文档.md": ["任务要求", "评分标准", "边界与非目标"],
    "plan/02-架构与技术选型.md": ["分层", "构建"],
    "plan/04-数据计划.md": ["数据清单", "真值纪律", "数值口径"],
    "plan/05-里程碑与发布.md": ["DoD", "已知未验证项"],
    "plan/06-交付对标与决策.md": ["评分对标", "风险登记"],
    "data/README.md": ["依据查证记录", "数值口径"],
}

# 七节交接单（超集合法：断言"必需节都存在"，不断言节数恰好）
HANDOFF_SECTIONS = ["证据", "待办", "既定口径", "环境坑", "DoD", "命令速查"]

# 项目已声明的豁免与冻结规则——门必须复用，别另立更严的一套
EXEMPT_MILESTONES = {0}
HANDOFF_FORMAT_FROM = 3

STATUS_COPIES = [
    ("plan/00-README总览.md", "里程碑表"),
    ("plan/05-里程碑与发布.md", "状态表"),
    ("README.md", "状态行"),
]

# 只认"状态行"：表格行且首格就是里程碑号（不扫自由文本——防张冠李戴假红）
STATUS_LINE = re.compile(r"^\|\s*\*{0,2}M(\d+)\b")
PENDING_MARKERS = ("⬜", "🟡", "未开始", "未执行", "待执行", "待确认")

READ_CACHE: dict[str, str | None] = {}


def read(rel: str) -> str | None:
    if rel not in READ_CACHE:
        p = ROOT / rel
        try:
            READ_CACHE[rel] = p.read_text(encoding="utf-8") if p.exists() else None
        except (OSError, UnicodeDecodeError):
            READ_CACHE[rel] = None
    return READ_CACHE[rel]


checks: list[tuple[bool, str, str]] = []
scanned = {"docs": 0, "handoffs": 0, "copies": 0, "doc_tools": 0}


def add(cid: str, ok: bool, detail: str) -> None:
    checks.append((ok, cid, detail))


def check_required_files() -> None:
    missing = [rel for rel in REQUIRED_FILES if (ROOT / rel).exists() is False]
    scanned["docs"] = len(REQUIRED_FILES) - len(missing)
    add(
        "LAYOUT.FILES",
        not missing,
        ("缺: " + ",".join(missing)) if missing else f"{scanned['docs']} 份齐备",
    )


def check_binding_head() -> None:
    text = read("plan/00-README总览.md") or ""
    ok = BINDING_LINE.search(text) is not None
    add(
        "LAYOUT.BINDING_HEAD",
        ok,
        "plan/00 顶部有装订行（三锚点齐）" if ok
        else "plan/00 顶部缺装订行（需同现：方法论名 + 布局门命令 + 装订日期）",
    )


def check_sections() -> None:
    bad = []
    for rel, needles in REQUIRED_SECTIONS.items():
        text = read(rel)
        if text is None:
            continue
        lack = [n for n in needles if n not in text]
        if lack:
            bad.append(f"{rel}: {'/'.join(lack)}")
    add(
        "LAYOUT.SECTIONS",
        not bad,
        ("；".join(bad)) if bad else f"{len(REQUIRED_SECTIONS)} 份小节齐备",
    )


def collect_states() -> dict[int, set[str]]:
    """逐副本采集状态：真值不取自任何一个副本（防自我参照真值源恒绿）。"""
    states: dict[int, set[str]] = {}
    for rel, _kind in STATUS_COPIES:
        text = read(rel)
        if text is None:
            continue
        scanned["copies"] += 1
        for line in text.splitlines():
            m = STATUS_LINE.match(line)
            if not m:
                continue
            k = int(m.group(1))
            pending = any(mark in line for mark in PENDING_MARKERS)
            states.setdefault(k, set()).add("pending" if pending else "done")
    return states


def check_status_agreement(states: dict[int, set[str]]) -> None:
    conflicts = [
        f"M{k} 在副本间状态不一致（{' vs '.join(sorted(s))}）"
        for k, s in sorted(states.items())
        if len(s) > 1
    ]
    add(
        "LAYOUT.STATUS",
        not conflicts,
        ("；".join(conflicts)) if conflicts
        else f"{scanned['copies']} 处副本 × {len(states)} 个里程碑 状态全一致",
    )


def check_handoffs(done: list[int]) -> None:
    missing = []
    for k in done:
        if k in EXEMPT_MILESTONES:
            continue
        rel = f"plan/HANDOFF-M{k}.md"
        text = read(rel)
        if text is None:
            missing.append(f"{rel}(缺)")
            continue
        scanned["handoffs"] += 1
        if k < HANDOFF_FORMAT_FROM:
            continue
        lack = [n for n in HANDOFF_SECTIONS if n not in text]
        if lack:
            missing.append(f"{rel}(缺节: {'/'.join(lack)})")
    add(
        "LAYOUT.HANDOFFS",
        not missing,
        ("；".join(missing)) if missing else f"{scanned['handoffs']} 份交接单齐（M0 已声明豁免）",
    )


def check_stale_gaps(done: list[int]) -> None:
    """plan/06 缺口列是状态的隐蔽副本。按表头定位列号再取单元格（防"行内关键词"假门）；
    匹配里程碑号时锚定单元格开头（防文件名 RELEASE-M6 之类的标识符撞 token 假红）。"""
    text = read("plan/06-交付对标与决策.md") or ""
    lines = text.splitlines()
    header_idx = next(
        (i for i, l in enumerate(lines) if l.startswith("|") and "缺口" in l), None
    )
    if header_idx is None:
        add("LAYOUT.GAPS", False, "plan/06 找不到含『缺口』表头的表（判据表搬走了？）")
        return
    col = len(lines[header_idx].split("|")) - 2  # 最后一个有效列
    stale = []
    for line in lines[header_idx + 2:]:
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        cell = (cells[col] if col < len(cells) else "").strip()
        for k in done:
            if re.match(rf"^\*{{0,2}}M{k}\b", cell):
                stale.append(f"plan/06 缺口列仍提 M{k}: {cell}")
    add(
        "LAYOUT.GAPS",
        not stale,
        ("；".join(stale)) if stale else "plan/06 缺口列无已完成里程碑（按表头定位列，锚定单元格开头）",
    )


def check_release_doc(done: list[int]) -> None:
    if not done:
        add("LAYOUT.RELEASE", True, "尚无 ✅ 里程碑（按副本集合），跳过")
        return
    last = max(done)
    release = read(f"plan/RELEASE-M{last}.md")
    wrapup = read(f"plan/WRAPUP-M{last}.md")
    if release is None and wrapup is None:
        add("LAYOUT.RELEASE", False, f"缺 plan/RELEASE-M{last}.md 或 plan/WRAPUP-M{last}.md")
        return
    if release is not None:
        cols = (
            re.search(r"^##\s*一、tag 前事实", release, re.M) is not None
            and re.search(r"^##\s*二、tag 后追加", release, re.M) is not None
        )
        heading = re.search(r"^#{2,3}.*覆盖对账", release, re.M) is not None
        rows = len(re.findall(r"^\|.*(实现|不适用|待首推).*\|$", release, re.M))
        add("LAYOUT.RELEASE", cols and heading and rows >= 3, f"两栏:{cols} 覆盖对账小节:{heading} 三态行数:{rows}")
        return
    add("LAYOUT.RELEASE", True, "WRAPUP 形态")


def check_documented_tools_exist() -> None:
    """文档点名的 tools/ 脚本必须有实物（判据只认路径形态，不读文档语义）。"""
    exempt: set[str] = set()  # 形如 "tools/xxx.py"：确实不实现时逐条登记理由
    docs = ["AGENTS.md"]
    plan_dir = ROOT / "plan"
    if plan_dir.exists():
        docs += [f"plan/{p.name}" for p in sorted(plan_dir.glob("*.md"))]
    referenced: set[str] = set()
    for rel in docs:
        text = read(rel)
        if text is None:
            continue
        for m in re.finditer(r"tools/[\w.-]+\.(?:mjs|js|cjs|py|sh|ps1)", text):
            referenced.add(m.group(0))
    if not referenced:
        add("LAYOUT.DOC_TOOLS", False, f"扫了 {len(docs)} 份文档，0 处 tools/ 引用——判据是空的（阳性对照失败）")
        return
    scanned["doc_tools"] = len(referenced)
    missing = [rel for rel in sorted(referenced) if rel not in exempt and not (ROOT / rel).exists()]
    add(
        "LAYOUT.DOC_TOOLS",
        not missing,
        ("文档点名但不存在的工具: " + ",".join(missing)) if missing
        else f"{len(referenced)} 个文档点名的 tools/ 脚本全部在位",
    )


def main() -> int:
    steps = [
        check_required_files,
        check_binding_head,
        check_sections,
        check_documented_tools_exist,
    ]
    for step in steps:
        try:
            step()
        except Exception as exc:  # 门永不崩：报 FAIL 并继续
            add(step.__name__, False, f"门内部异常: {exc!r}")
    states = collect_states()
    done = sorted(k for k, s in states.items() if "done" in s)
    for step in (
        lambda: check_status_agreement(states),
        lambda: check_handoffs(done),
        lambda: check_stale_gaps(done),
        lambda: check_release_doc(done),
    ):
        try:
            step()
        except Exception as exc:
            add("layout-step", False, f"门内部异常: {exc!r}")

    failed = [c for c in checks if not c[0]]
    bar = "=" * 56
    print("布局门（方法论装订） · 判据只落仓库内文件")
    print(bar)
    for ok, cid, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {cid}  {detail}")
    print(bar)
    print(
        f"这轮扫到：文档 {scanned['docs']} / 交接单 {scanned['handoffs']} / "
        f"状态副本 {scanned['copies']} / 文档点名工具 {scanned['doc_tools']}"
    )
    print(f"结论: {'全绿' if not failed else f'{len(failed)} 项 FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
