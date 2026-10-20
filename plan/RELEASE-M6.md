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
| `sqltrace-0.1.0-py3-none-any.whl` | 42,279 | `1c9b88b8954656b1127260a95b3d63b5d71bcf7b0ee0337014b3c472291fbd6a` |
| `sqltrace-0.1.0.tar.gz` | 56,761 | `29a94d3076450a866c0f082f236a1406efaca6d48ca283804d6dfb496fd952ee` |

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
| 跨平台字节级一致（Linux/macOS） | 待首推 | CI 首次运行后回填 run id（`plan/05` §四） |
| CI 实跑 | 待首推 | 本机为"本地等价校验（未接远端，CI 待首推验证）"；`gh run list` 有结果后回填 |
| 发布三件套 | 实现（本文件 + tag + Release） | tag 名与 Release URL 见 §二 |

### 7. CI 接线（本机等价校验，未接远端）

`.github/workflows/ci.yml` 三个 job：

1. `layout` — `python -X utf8 tools/check_sprint_layout.py`（布局门，含 `test_layout_gate_passes` 之外的独立步骤）；
2. `test` — `pip install -e ".[dev]"` → `pytest tests -q` → `sqltrace golden data/golden`（**五条 golden 在 CI 里跑**）；
3. `py38-syntax` — `ast.parse(feature_version=(3,8))` 覆盖 `src/sqltrace`、`tests`、`tools`。

CI 不需要 git 历史：g5 的 diff 断言走**目录模式**（`corpus` → `corpus_v2`），浅克隆下也能跑。本地等价校验已通过（布局门绿 / 107 tests 绿 / 五条 golden 5/5）；**首推后**回填真实 run id。

### 8. tag 前状态

- 交付面（`src/`、`data/`、`tests/`、`docs/`、`pyproject.toml`、`README.md`、`LICENSE`、`.github/workflows/ci.yml`）已冻结。
- tag 之后**只允许非交付面提交**（`plan/RELEASE-M6.md` §二、状态回写、`plan/HANDOFF-M6.md`）；两条判据：POST_TAG_SCOPE（提交路径 ⊆ `plan/` 或 `*.md`）+ DELIVERABLE_UNCHANGED（`git diff <tag> -- src data tests docs pyproject.toml` 为空）。

## 二、tag 后追加（tag 之后写，tag 树内为占位）

> 本节在 tag 提交里是"待追加"状态——tag 树内不自指写哈希与 URL。

| 项 | 值 |
| --- | --- |
| tag 名 | 待追加 |
| tag 对象 | 待追加（annotated tag 的 SHA） |
| Release URL | 待追加 |
| 上传产物 SHA256（下载后复核） | 待追加 |
| CI run id（首推） | 待追加 |
