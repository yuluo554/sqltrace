# RELEASE-M6 — SQLTrace v0.1.0 发布留档

> 纪律：**本文件在 tag 之前入库**（进 tag 树）。§一 只写 tag 前可核验的事实；§二 在 tag 之后追加，**tag 树内不自指写哈希**（tag 内的 §二 是"待追加"占位，真实值写进 tag 之后的提交）。
> 口径单点：`data/README.md` §四。里程碑台账：`plan/00` §六。

## 一、tag 前事实（tag 之前落盘）

### 1. 发布身份

| 项 | 值 |
| --- | --- |
| 包名 / 命令名 | `sqltrace` |
| 版本 | `0.1.0`（`src/sqltrace/__init__.py` 与 `pyproject.toml` 同源） |
| 仓库 | `https://github.com/yuluo554/sqltrace`（公开） |
| 许可证 | MIT（`LICENSE` 入库，随 wheel 的 `dist-info/licenses/` 与 sdist 一起分发） |
| Python | `requires-python >=3.8`（库代码 3.8 语法兼容；测试通道走 3.12） |
| 运行期依赖 | 仅 `sqlglot>=30.20,<31` + 标准库（零网络、零数据库连接） |

### 2. 构建命令（本机 Windows，3.12 通道）

```bash
PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m build --no-isolation
mkdir -p release && cp dist/sqltrace-0.1.0-py3-none-any.whl dist/sqltrace-0.1.0.tar.gz release/
cd release && py -3.12 -c "import hashlib,pathlib; [print(hashlib.sha256(p.read_bytes()).hexdigest(), p.name) for p in sorted(pathlib.Path('.').glob('sqltrace-*'))]"
```

`release/*.whl` / `release/*.tar.gz` 按 D13 与 `.gitignore` **不入库**（本地留副本，随 Release 上传）。

### 3. 产物清单与 SHA256（本机实测，2026-10-21）

| 产物 | 字节 | SHA256 |
| --- | --- | --- |
| `sqltrace-0.1.0-py3-none-any.whl` | 42,267 | `908a6b6189a9edd23cb7f80fa0d7eba70cbb9533490ef88104c89480c2de21ef` |
| `sqltrace-0.1.0.tar.gz` | 56,717 | `06f9c00c75cc2dc607e4728fa6d8b0dc4f1b5ad66ed87fcb05b38758cf92273c` |

> 构建纪律：产物必须从**最终交付树**构建（含 README / LICENSE / `pyproject.toml` 定稿后）。本次首版产物在 README 状态行改写**之前**构建，sdist 内的 README 与 tag 树不一致，已删除重建；上表为重建后的值。

`release/SHA256SUMS` 与上表同源（`<hash>  <filename>` 两空格分隔，`sha256sum -c` 可校验）。

wheel 内容：`sqltrace/{__init__,census,cli,constants,core,diffgate,fallback,loader,model,output}.py` + `dist-info`（`METADATA` 含 `License-File: LICENSE`、`Requires-Dist: sqlglot<31,>=30.20`）。
sdist 内容：`src/` + `tests/` + `pyproject.toml` + `README.md` + `LICENSE` + `PKG-INFO`。

### 4. 干净环境验证（真下载 → 新 venv → 逐条敲 README）

两条通道各建一个**全新 venv**，用 `release/` 里的产物安装（不是 `-e .`）：

| 通道 | 安装 | `--version` | 五条命令 |
| --- | --- | --- | --- |
| wheel | `pip install release/sqltrace-0.1.0-py3-none-any.whl`（清华源） | `sqltrace 0.1.0` | 全部通过，见下表 |
| sdist | `pip install release/sqltrace-0.1.0.tar.gz`（现场构建） | `sqltrace 0.1.0` | `golden` 5/5，退出码 `0` |

README §命令树 五条命令逐条实跑（wheel 通道）：

| 命令 | 退出码 | 观测 |
| --- | --- | --- |
| `sqltrace lineage data/corpus --json` | `0` | 53 文件 / 59 语句 / 232 边 / 8 诊断 / `zero_silence.passed = true` |
| `sqltrace census data/corpus --md` | `0` | 写入者语句 42 / 读者语句 54 / orphan 11 / multi_writer 1 |
| `sqltrace diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus` | `1` | `REMOVED 1 / ADDED 2 / CHANGED 1`（有破坏性变更 → 闸门拦截） |
| `sqltrace impact raw_cust.nm data/corpus` | `0` | 下游 5 / 最终消费者 2 / 穿透 2 层 |
| `sqltrace golden data/golden` | `0` | 5/5 PASS |

> **本表是 v0.1.0 的冻结记录，不要改数值。** v0.1.1（D11 加了两条真实 DML 语料）后同一批命令的观测是
> **54 文件 / 61 语句 / 232 边 / 10 诊断**（census 与 impact 数字不变），见 `plan/RELEASE-M6.1.md`。

双跑确定性：`diff --json` 两次输出 `cmp` 相同；`census --md` 两次相同；且与仓库内 `docs/diff-sample.json`、`docs/census-sample.md` **逐字节一致**（终端重定向的 CRLF 归一后比对，Windows 控制台换行不是程序输出差异）。

### 5. 脱敏扫描（`git ls-files` 全量）

| 扫描项 | 结果 |
| --- | --- |
| 邮箱 / 人名 | 0 命中 |
| 公司名 / 组织名（含中英文） | 0 命中 |
| 绝对路径（`C:\`、`/home/`、`/Users/`、`/mnt/`） | 0 命中（仅 `AGENTS.md` 有本机 pip 源 URL，属工具链说明，非数据） |
| 内网 IP | 0 命中 |
| 表名 / 列名 | 全部 `raw_/stage_/mart_` 假名 + 语义化短列名，无真实业务口径 |
| 语料注释 | 只描述 SQL 构造（"窗口分型""JOIN ON 为 control"），无业务事实 |

`plan/` 内的 GitHub issue / 竞品 URL 是**公开依据引用**（基准日 2026-10-20），不属于需脱敏内容。

### 6. 覆盖对账表（承诺项 × 发布态）

| 承诺项（`plan/00` §三） | 发布态 | 核验证据 |
| --- | --- | --- |
| 值/控制双通道分型 | 实现 | 标注语料 `value` 精确率 100%；`golden` g1 绿；`tests/test_m2_core.py` |
| sqlglot 分区键误判被修正 | 实现 | 窗口用例 `w←x`(value) + `w←k`(control)；g1 |
| sqllineage #276 谓词血缘被覆盖 | 实现 | WHERE/ON/USING/HAVING/QUALIFY control 边；g1 |
| 降级 reason code 枚举 + 零静默 | 实现 | `grep -c unknown` 与诊断计数一致；`lineage --json` 的 `zero_silence.passed` |
| `SELECT *` 未知 schema 不猜列名 | 实现 | g2：输出无猜测列名 |
| `INSERT` 列清单位置映射 | 实现 | g3 |
| `CREATE VIEW v(c1,c2)` 列名对齐 | 实现 | `tests/test_m3_fallback.py` 专项 |
| 写入者普查五节 | 实现 | `census` 报表 + g4；`docs/census-sample.md` 真实输出 |
| lineage diff 闸门 | 实现 | `diff --base` 双模式；g5；退出码 `0/1/2` |
| `impact` 穿透两层 | 实现 | g5 + `impact raw_cust.nm` 实测 2 层 |
| 零网络 / 无数据库连接 | 实现 | `test_no_network_imports`（静态扫描 `src/`） |
| 同输入两次运行字节级一致 | 实现（Windows） | 本机双跑 `sha256` 相同；Linux/macOS 侧待首推 CI 回填 |
| 五条 golden 回归 | 实现 | `sqltrace golden data/golden` → 5/5，退出码 `0` |
| 三个切口检索为 0 | 不适用（软论据） | 检索式未穷尽，`plan/00` §三已标"软论据"；不在发布面宣称 |
| 跨平台字节级一致（Linux/macOS） | 实现（Windows 本机 + Linux CI） | Windows 双跑 + run `39466283266` 的 Linux pytest 双跑字节比对；**macOS 未验**（CI 无 macOS runner） |
| CI 实跑 | 实现 | run `39466283266` 三 job 全绿（布局门 / pytest + 五条 golden / 3.8 语法）；真实 run id 已回填 §二 |
| 发布三件套 | 实现（本文件 + tag + Release） | tag 名与 Release URL 见 §二 |

### 7. CI 接线

`.github/workflows/ci.yml` 三个 job：

1. `layout` — `python -X utf8 tools/check_sprint_layout.py`（布局门，含 `test_layout_gate_passes` 之外的独立步骤）；
2. `test` — `pip install -e ".[dev]"` → `pytest tests -q` → `sqltrace golden data/golden`（**五条 golden 在 CI 里跑**）；
3. `py38-syntax` — `ast.parse(feature_version=(3,8))` 覆盖 `src/sqltrace`、`tests`、`tools`。

CI 不需要 git 历史：g5 的 diff 断言走**目录模式**（`corpus` → `corpus_v2`），浅克隆下也能跑。首推 run `39466283266` **三 job 全绿**（布局门 4s / 全量测试 + 五条 golden 13s / 3.8 语法 15s），见 §二。

### 8. tag 前状态

- 交付面（`src/`、`data/`、`tests/`、`docs/`、`pyproject.toml`、`README.md`、`LICENSE`、`.github/workflows/ci.yml`）已冻结。
- tag 之后**只允许非交付面提交**（`plan/RELEASE-M6.md` §二、状态回写、`plan/HANDOFF-M6.md`）；两条判据：POST_TAG_SCOPE（提交路径 ⊆ `plan/` 或 `*.md`）+ DELIVERABLE_UNCHANGED（`git diff <tag> -- src data tests docs pyproject.toml` 为空）。

## 二、tag 后追加（tag 之后写，tag 树内为占位）

> 本节在 tag 提交里是"待追加"状态——tag 树内不自指写哈希与 URL。以下为 tag 之后的事实。

| 项 | 值 |
| --- | --- |
| tag 名 | `v0.1.0`（annotated，`git cat-file -t` = `tag`） |
| tag 对象 SHA | `a5ecc0ba3729ee765616ece0648b7c5bf574030d` |
| tag 指向的 commit | `e579c772cbae35d23add43a4e458927292d78b36` |
| 远端仓库 | `https://github.com/yuluo554/sqltrace`（public） |
| Release URL | `https://github.com/yuluo554/sqltrace/releases/tag/v0.1.0` |
| 上传产物 | `sqltrace-0.1.0-py3-none-any.whl`（42,267 B）、`sqltrace-0.1.0.tar.gz`（56,717 B）、`SHA256SUMS`（186 B），三件状态均为 `uploaded` |
| 下载后复核 SHA256 | wheel `908a6b6189a9edd23cb7f80fa0d7eba70cbb9533490ef88104c89480c2de21ef`；sdist `06f9c00c75cc2dc607e4728fa6d8b0dc4f1b5ad66ed87fcb05b38758cf92273c`——**与 `SHA256SUMS` 及 §一 表逐字节相同** |
| 下载产物安装验证 | `gh release download` 取回的 wheel → 全新 venv 安装 → `sqltrace 0.1.0`、`golden` 5/5，退出码 `0` |
| CI run id（首推） | `39466283266`（`ci` / `main` / push，**success**）：布局门 4s、全量测试 + 五条 golden 13s、3.8 语法兼容 15s |
| CI run id（tag 后追加提交） | `39466653904`（**success**，20s）——tag 后的文档追加不破坏任何门 |
| CI 结论措辞 | **CI 绿**（真实 run id 已回填；Linux/ubuntu-latest 侧三 job 全绿） |

### tag 后提交范围（POST_TAG_SCOPE + DELIVERABLE_UNCHANGED）

本次 tag 后提交只改 `plan/RELEASE-M6.md`、`plan/HANDOFF-M6.md`、`plan/00`、`plan/05`、`plan/06` 与 `README.md`（安装段）；`src/`、`data/`、`tests/`、`docs/`、`pyproject.toml`、`release/SHA256SUMS` **零改动**（判据命令见 `plan/HANDOFF-M6.md` §二 #8）。

> 如实登记：tag 后追加的 README「安装发布版」段**不在**已发布的 sdist 内（sdist 打包的是 tag 版本的 README）。wheel 功能与两件产物哈希不受影响；sdist 用户按 Release 页安装即可。

### 未验证项（如实登记）

- macOS 侧未跑（CI 只有 ubuntu-latest）；Windows 本机双跑与 Linux CI 均已验字节级一致，macOS 仍属未验证。
- PyPI 未发布（D13 定案：只走 GitHub Release 附产物）。
