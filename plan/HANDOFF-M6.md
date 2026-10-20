# HANDOFF-M6 — 发布交接单

> 续接对话第一件事：`py -X utf8 tools/check_sprint_layout.py`（必须绿）。
> 本份是**最后一棒**：M0–M6 全部 ✅，项目进入维护期（`ai-tool-ops-cadence`）。

## 一、当前进度 + 证据

- **M0–M6 全部完成**。M6 = 发布三件套：①annotated tag ②GitHub Release（附 `release/*.whl` + `release/*.tar.gz` + `SHA256SUMS`）③`plan/RELEASE-M6.md`（tag 前入库，§二 tag 后追加）。
- 证据（tag 前）：
  - 常驻测试 **107 passed**（`PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q`）。
  - 布局门全绿（10 文档 / 6 交接单 / 3 状态副本）。
  - `sqltrace golden data/golden` → **5/5**，退出码 `0`（干净 venv 里跑，不是 `-e .`）。
  - 干净环境双通道：wheel 与 sdist **各建全新 venv** 安装成功；README 五条命令逐条实跑（退出码 `0/0/1/0/0`，`1` 是 g5 diff 的破坏性变更语义）。
  - 双跑确定性：`diff --json`、`census --md` 两次输出相同，且与 `docs/diff-sample.json` / `docs/census-sample.md` 逐字节一致。
  - 产物 SHA256：wheel `908a6b61…21ef`（42,267 B）、sdist `06f9c00c…273c`（56,717 B）。产物从**最终交付树**重建（首版构建早于 README 状态行改写，sdist 内 README 与 tag 树不一致，已删重建）。
  - 3.8 语法兼容：`ast.parse(feature_version=(3,8))` 对 `src/sqltrace` + `tests` + `tools` 全绿。
- 证据（tag 后）：见 §七「发布事实」与 `plan/RELEASE-M6.md` §二。

## 二、当前事实·状态不变量（维护期必读）

1. M0 的 7 条 + M1 的 K1–K8 + M2 的 K9 + M3 的 K10–K12 + M4 的 K13–K14 + M5 的 K15–K17 **全部继续有效**；M6 新增 K18–K19（见 §四）。
2. **口径单点仍是 `data/README.md` §四**。发布后任何行为变更都要先改那一节，再改 `constants.py`，再改代码——顺序不能反。
3. **版本号双处同源**：`src/sqltrace/__init__.py` 的 `__version__` 与 `pyproject.toml` 的 `version` 必须一致。改一处不改另一处 → wheel 元数据与 `--version` 不一致（M6 把 `0.1.0.dev0` 定稿为 `0.1.0` 就是两处同改）。
4. **`docs/census-sample.md` / `docs/diff-sample.json` 内嵌版本号**。版本号一改，两份样例必须重生成（`test_census_markdown_sample_*` / `test_diff_sample_doc_*` 逐字节比对会红）。M6 已重生成。
5. **`release/` 不入库**（`.gitignore` 忽略 `release/*.whl`、`release/*.tar.gz`；`release/SHA256SUMS` 入库）。产物只走 Release 附件。
6. **CI 不依赖 git 历史**：g5 的 diff 断言走目录模式（`corpus` → `corpus_v2`），`actions/checkout` 默认浅克隆即可。**不要**给 g5 加 `--base HEAD~1`。
7. **CI 里 `sqltrace golden` 用安装后的命令**（`pip install -e ".[dev]"` 后 `sqltrace golden data/golden`），不是 `python -c` 拼 `sys.path`——这样 CI 顺带验证了入口点。
8. **tag 之后只允许非交付面提交**：`plan/**`、`*.md`、`.github/**` 之外的路径不许动。判据：`git diff <tag> -- src data tests docs pyproject.toml` 为空 + 提交路径 ⊆ `plan/` 或 `*.md`。

## 三、下一棒待办（维护期，非阻塞）

1. **CI 首推回填**：`gh run list --limit 5` 拿真实 run id 与结论，写进 `plan/RELEASE-M6.md` §二 与 `plan/05 §四`；在此之前一切 CI 表述只能是"本地等价校验（未接远端，CI 待首推验证）"。
2. **跨平台字节级一致**：CI 首次跑通后，把 Linux 侧的 `diff --json` / `census --md` 字节比对结果回填 `plan/05 §四`。
3. **PyPI 首发（可选）**：当前只发 GitHub Release（D13）。若要发 PyPI，先 `py -3.12 -m twine check dist/*`，再 `twine upload`；`release/` 产物与 PyPI 上的必须同哈希。
4. **sqlglot 升级巡检**：`pyproject` 钉 `>=30.20,<31`。放开区间前必须重跑五条 golden + 107 测试；升级后若 golden 红，先判"实现缺陷"还是"口径漂移"，后者要改 `data/README.md` §四 再改代码。

## 四、既定口径清单（K 编号，动了会打挂测试）

> K1–K17 见 `plan/HANDOFF-M5.md` §四（逐条仍有效）。M6 新增两条：

- **K18（M6）**：**版本号与样例同步**——`__version__`、`pyproject.version`、`docs/census-sample.md`、`docs/diff-sample.json` 四处的版本字符串必须一致；改版本 = 四件同改（后两者用重生成命令，不手改）。
- **K19（M6）**：**发布产物口径**——`release/` 里只放 `python -m build` 的两个产物 + `SHA256SUMS`（`<hash>  <name>` 两空格）；`SHA256SUMS` 入库、二进制不入库；Release 附件与 `SHA256SUMS` 同源；**tag 树内的 `RELEASE-M6.md` §二 只能是占位**（不自指写 tag SHA / Release URL / 产物哈希）。

## 五、本机环境坑（实测日期 2026-10-21）

- M0–M5 交接单 §五 全部继续有效（`py`/`-X utf8`/`PYTHONDONTWRITEBYTECODE=1`、pip 代理污染需 `NO_PROXY="*"`、`python` 是商店占位符、Bash heredoc 写 Python 会吃 `\n`）。
- **`py -3.12 -m build --no-isolation`** 可用（build 1.6.1 + setuptools 84.0.0 + wheel 0.48.0 已装）。不加 `--no-isolation` 会尝试联网建隔离环境，在代理污染下会卡。
- **`project.license` 用 TOML 表会打 deprecation 警告**（setuptools ≥77 建议 SPDX 字符串）。当前保留 `{ text = "MIT" }`：警告不影响构建与 `License-File` 落盘，改动会牵动 metadata 与已有留档哈希。
- **Windows 下 Bash 重定向 `> file` 会写 CRLF**：拿 CLI 输出与 `docs/*` 样例 `cmp` 会假红。判定方法 = 读字节做 `replace(b"\r\n", b"\n")` 后再比；程序自身输出（`sys.stdout.write`）恒为 `\n`。
- **干净 venv 里 `pip install` 必须带清华源**：`NO_PROXY="*" ... -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <artifact>`。
- **`gh` 已登录 `yuluo554`**（keyring，scopes 含 `repo`）；`gh api /user` 在 Git Bash 里会被路径重写成 `D:/program/Git/user`，用 `gh auth status` 或 `gh repo list` 代替。
- **`git ls-files` 对中文路径默认转义**：看路径用 `git -c core.quotepath=false status --short`。

## 六、M6 DoD checklist

- [x] 脱敏扫描：`git ls-files` 全量无邮箱/人名/公司名/内网路径/IP；表名全为假名
- [x] 干净环境验证：wheel 与 sdist 各建新 venv 安装；README 五条命令逐条真跑（不是 `--help`）
- [x] `plan/RELEASE-M6.md` 两栏（§一 tag 前事实 / §二 tag 后追加）+ 覆盖对账表三态行 ≥3（实测 17 行）
- [x] 构建产物：`release/sqltrace-0.1.0-py3-none-any.whl` + `release/sqltrace-0.1.0.tar.gz` + `release/SHA256SUMS`
- [x] 版本定稿 `0.1.0`（`__init__.py` + `pyproject.toml` 同源）+ `LICENSE` 入库 + 两份样例重生成
- [x] CI 接线：`.github/workflows/ci.yml`（布局门 / pytest + 五条 golden / 3.8 语法）
- [x] 状态三副本回写 M6 ✅（`plan/00` 里程碑表 + `plan/05` 状态表 + `README.md` 状态行）+ `plan/06` 缺口列改写
- [x] 布局门绿（含本份交接单）
- [x] annotated tag `v0.1.0`（annotated，指向 `e579c77`）→ 见 §七
- [x] `gh release create` 附三份产物（whl / tar.gz / SHA256SUMS，均 `uploaded`）→ 见 §七
- [x] tag 后追加 `RELEASE-M6.md` §二（tag 名 / tag SHA / Release URL / 下载后复核哈希 / CI run id）

## 七、发布事实（tag 后回填）

| 项 | 值 |
| --- | --- |
| tag 名 | `v0.1.0`（annotated） |
| tag 对象 SHA | `a5ecc0ba3729ee765616ece0648b7c5bf574030d` |
| tag 指向 commit | `e579c772cbae35d23add43a4e458927292d78b36` |
| Release URL | `https://github.com/yuluo554/sqltrace/releases/tag/v0.1.0` |
| 上传产物（3 件） | `sqltrace-0.1.0-py3-none-any.whl`（42,267 B）、`sqltrace-0.1.0.tar.gz`（56,717 B）、`SHA256SUMS`（186 B）——`gh release view` 三件均 `uploaded` |
| 下载后复核 | `gh release download v0.1.0` 取回三件，哈希与 `SHA256SUMS` 及 `RELEASE-M6.md` §一 表**逐字节相同**；取回的 wheel 装进全新 venv → `golden` 5/5，退出码 `0` |
| CI run id | `39466283266`（`ci` / `main` / push / **success**；三 job 全绿） |

> **CI 措辞已升级**：首推已完成、真实 run id 已回填，故可写"**CI 绿**"（不再是"待首推验证"）。`plan/05 §四` 与 `plan/06` 已同步。

## 八、关键命令速查

```bash
py -X utf8 tools/check_sprint_layout.py                          # 布局门（第一件事）
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q    # 全量测试（107 个）
py -3.12 -X utf8 -c "import sys; sys.path.insert(0,'src'); from sqltrace.cli import main; sys.exit(main(['golden','data/golden']))"

# 构建与校验和（改交付面后重跑；tag 后不许重跑）
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m build --no-isolation
cp dist/sqltrace-0.1.0-py3-none-any.whl dist/sqltrace-0.1.0.tar.gz release/
cd release && py -3.12 -c "import hashlib,pathlib; [print(hashlib.sha256(p.read_bytes()).hexdigest(), p.name) for p in sorted(pathlib.Path('.').glob('sqltrace-*'))]"

# 干净环境验证（两条通道各一次）
py -3.12 -m venv /tmp/v && NO_PROXY="*" /tmp/v/Scripts/python.exe -m pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple release/sqltrace-0.1.0-py3-none-any.whl
/tmp/v/Scripts/sqltrace.exe golden data/golden

# 重生成样例（改版本号或输出后必做）
py -3.12 -X utf8 -c "import sys,io,contextlib; sys.path.insert(0,'src'); from sqltrace.cli import main; b=io.StringIO(); c=contextlib.redirect_stdout(b); c.__enter__(); main(['census','data/corpus','--md']); c.__exit__(None,None,None); open('docs/census-sample.md','w',encoding='utf-8',newline='\n').write(b.getvalue())"
py -3.12 -X utf8 -c "import sys,io,contextlib; sys.path.insert(0,'src'); from sqltrace.cli import main; b=io.StringIO(); c=contextlib.redirect_stdout(b); c.__enter__(); main(['diff','data/golden/g5/corpus_v2','--base','data/golden/g5/corpus','--json']); c.__exit__(None,None,None); open('docs/diff-sample.json','w',encoding='utf-8',newline='\n').write(b.getvalue())"

# 发布
git tag -a v0.1.0 -m "sqltrace v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 release/sqltrace-0.1.0-py3-none-any.whl release/sqltrace-0.1.0.tar.gz release/SHA256SUMS --title "v0.1.0" --notes-file <notes>

py -3.8 -X utf8 -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,8)) for d in ('src/sqltrace','tests','tools') for p in pathlib.Path(d).glob('*.py')]; print('3.8 ok')"
```
