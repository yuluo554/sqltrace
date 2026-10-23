# RELEASE-M6.1 — SQLTrace v0.1.1 发布留档

> 纪律：**本文件在 tag 之前入库**（进 tag 树）。§一 只写 tag 前可核验的事实；§二 在 tag 之后追加，**tag 树内不自指写哈希**。
> 上一版留档：`plan/RELEASE-M6.md`（v0.1.0，**冻结不改**）。口径单点：`data/README.md` §四。

## 一、tag 前事实（tag 之前落盘）

### 1. 发布身份

| 项 | 值 |
| --- | --- |
| 包名 / 命令名 | `sqltrace` |
| 版本 | `0.1.1`（`src/sqltrace/__init__.py` 与 `pyproject.toml` 两处手写，均 `0.1.1`） |
| 仓库 | `https://github.com/yuluo554/sqltrace`（公开） |
| 许可证 | MIT（`LICENSE` 入库，随 wheel 的 `dist-info/licenses/` 与 sdist 一起分发） |
| Python | **`requires-python >=3.9`（v0.1.1 变更，D3）**；CI 有 3.9 与 3.12 两条真装真跑腿 |
| 运行期依赖 | 仅 `sqlglot>=30.20,<31` + 标准库（零网络、零数据库连接） |

**为什么抬到 3.9（D3）**：`requires-python` 是给 pip 的承诺，不是语法标签。区间 `>=30.20,<31` 内只有
5 个版本（30.20.0 / 30.21.0 / 30.22.0 / 30.23.0 / 30.24.0），**全部** `requires_python >=3.9`；py3.8
上 `pip install -e ".[dev]"` 与**已发布的 v0.1.0 wheel** 均实测 `No matching distribution found for
sqlglot<31,>=30.20`。旧的 `py38-syntax` job 只跑 `ast.parse(feature_version=(3,8))`、从不装包，所以永远
看不见这个必然失败。

### 2. 本轮修的是什么（对应 `update/00-诊断报告.md`）

| 编号 | 级别 | 修法 | 用户可见后果 |
| --- | --- | --- | --- |
| D1 | P0 | DEC-1 **乙案**：AST 根是数据写类型（`Update`/`Delete`/`TruncateTable`/`Copy`）即登记进 `write_ids` 并落 `unsupported_write_statement` 诊断，**不产边** | `UPDATE` / `DELETE` / `TRUNCATE` 不再"0 边 0 诊断 rc=0"；静默丢弃会让 `lineage` 退 `4` |
| D2 | P1 | DEC-2 **丙案**：`ensure_deterministic_stdio()` 无条件 `reconfigure(newline="\n")` | Windows 输出不再带 CRLF，兑现跨平台字节级一致 |
| D3 | P1 | DEC-3 **甲案**：`requires-python = ">=3.9"`，删 3.8 classifier，CI 的 `py38-syntax` → 真装真跑的 `py39-min` | py3.8 上不再"看起来能装、装时必失败" |
| D4 | P1 | DEC-4 **甲案**：`_dynamic_sql_snippet()` 取被执行的 SQL，不走 `Execute.sql()` | `UNSUPPORTED_DYNAMIC_SQL` 的 message 点名 `EXEC('SELECT inv_id FROM raw_inv')`，不再是文件开头注释 |
| D5 | P1 | DEC-4 **甲案**：`silence_library_logging()`（`NullHandler` + `propagate=False`） | 四个子命令的 stderr 不再多一行 `Unsupported Execute syntax` |
| D6 | P1 | DEC-5：`checkout@v7` / `setup-python@v7`，`runs-on: ubuntu-24.04`（三 job） | Node20 弃用注解清零；镜像迁移变成有意识的决定 |
| D10 | P2 | `13 档` / `14 档` → **15 档**，四处文档 + K2 行统一，并写清"13 是 `cases` 键数" | 同一事实不再有两个值 |
| D11 | P2 | 语料加 1 条 `UPDATE` + 1 条 `DELETE`（`data/corpus/postgres/10_dml_mart_amend.sql`） | 语料覆盖真实 DML 形态；边数不变，诊断 +2 |
| 2C | — | 新增 `.gitattributes`（`* text=auto eol=lf`） | tag 树归档不再产出 CRLF，重建产物可逐字节复现源码成员 |

### 3. 构建命令（本机 Windows，py3.12 通道）

```bash
rm -rf dist
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -X utf8 -m build --no-isolation
mkdir -p release && cp dist/sqltrace-0.1.1-py3-none-any.whl dist/sqltrace-0.1.1.tar.gz release/
# SHA256SUMS：<hash>␠␠<filename>（两空格、单 LF）
```

`release/*.whl` / `release/*.tar.gz` 按 D13 与 `.gitignore` **不入库**（本地留副本，随 Release 上传）；`release/SHA256SUMS` **入库**（DEC-6 保持现状）。

### 4. 产物清单与 SHA256（本机实测）

| 产物 | 字节 | SHA256 |
| --- | --- | --- |
| `sqltrace-0.1.1-py3-none-any.whl` | 45,094 | `3e1730c87e6cc9d5186713883c38caf41c7c95744135d8d4181b7509336ccd0e` |
| `sqltrace-0.1.1.tar.gz` | 62,487 | `d307dcce85f245bc1a8b74fef5a5d9835254b52d67adcd5d0f28c856b24b942c` |

wheel 内容 **16 条目**（10 模块 + `dist-info`），`METADATA` 含 `Requires-Python: >=3.9`、
`License-File: LICENSE`、`Requires-Dist: sqlglot<31,>=30.20`。

### 5. 干净环境验证（新 venv 装 wheel → 中立 cwd）

| 项 | 观测 |
| --- | --- |
| `--version` | `sqltrace 0.1.1` |
| `golden data/golden` | 5/5 通过，退出码 `0` |
| `lineage data/corpus --json` | **232 边 / 10 诊断** / `zero_silence.passed = true`（与源码态逐项相同） |
| D1 现场复核 | 三条真实 DML（UPDATE/DELETE/TRUNCATE）→ 3 条 `unsupported_write_statement`、`passed=true` |
| §4.8 口径复核 | 同一 DML 语料 `census` 的 `writers`/`readers` 均为空（DML 不进写者台账，普查数字不漂） |

### 6. 命令级基线（v0.1.0 → v0.1.1 对照）

| 命令 | v0.1.0（`RELEASE-M6` §4） | v0.1.1（本轮） | 变化原因 |
| --- | --- | --- | --- |
| `lineage data/corpus --json` | 53 文件 / 59 语句 / 232 边 / 8 诊断 | **54 文件 / 61 语句 / 232 边 / 10 诊断** | D11 加 1 文件 2 语句 → 2 条 `unsupported_write_statement`；**边数不变** |
| `census data/corpus --md` | 写入者 42 / 读者 54 / orphan 11 / mw 1 | 同上（不变） | DML 只碰自身表，不新增读写关系 |
| `diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus` | `REMOVED 1 / ADDED 2 / CHANGED 1`，rc=1 | 同上 | golden 语料未改 |
| `impact raw_cust.nm data/corpus` | 下游 5 / 最终消费者 2 / 穿透 2 层 | 同上 | — |
| `golden data/golden` | 5/5，rc=0 | 5/5，rc=0 | — |

> `docs/census-sample.md` 与 `docs/diff-sample.json` 都内嵌版本号，**抬版本必重生成**（本轮各只变版本行 1 行，与 v0.1.2 那次的经验一致）。

### 7. 覆盖对账表（承诺项 × 发布态）

| 承诺项 | 发布态 | 核验证据 |
| --- | --- | --- |
| 值/控制双通道分型 | 实现 | 标注语料 `value` 精确率 100%；golden g1 |
| **零静默门覆盖所有写语句** | **实现（v0.1.1 修正）** | 写语句 = INSERT / CREATE…AS / MERGE / **UPDATE / DELETE / TRUNCATE / COPY**；后四类由 `unsupported_write_statement` 满足"有诊断"。三档参数化测试 + 1 条 rc=4 负控 |
| **跨平台输出字节级一致** | **实现（v0.1.1 修正）** | `tests/test_output_stream.py` 6 条真实子进程用例断言 stdout 无 `\r`；旧 StringIO 断言保留并注明只覆盖逻辑层 |
| **requires-python 与依赖自洽** | **实现（v0.1.1 修正）** | `>=3.9`；CI `py39-min` 真装真跑 `python 3.9.25 / sqlglot 30.24.0`、129 passed |
| **动态 SQL 诊断可读** | **实现（v0.1.1 修正）** | message 含 `EXEC('SELECT inv_id FROM raw_inv')`；stderr 无库噪声（5 个命令参数化断言） |
| 降级 reason code 封闭枚举 + 零静默 | 实现（**15 档**） | `test_constants_match_data_readme` 逐行比对；`test_every_reason_code_has_a_triggering_case` 全集差集 |
| `SELECT *` 未知 schema 不猜列名 | 实现 | golden g2 |
| `INSERT` 列清单位置映射 | 实现 | golden g3 |
| 写入者普查五节 | 实现 | census + g4；`docs/census-sample.md` 真输出 |
| lineage diff 闸门 | 实现 | `diff --base` 双模式；g5；退出码 0/1/2 |
| `impact` 穿透两层 | 实现 | g5 + 实测 2 层 |
| 零网络 / 无数据库连接 | 实现 | `test_no_network_imports` 静态扫描 |
| 同输入两次运行字节级一致 | 实现（Windows + Linux CI） | 双跑 sha256 相同（逻辑层）+ 真流 LF（`test_output_stream.py`）；**macOS 未验** |
| 五条 golden 回归 | 实现 | `sqltrace golden data/golden` → 5/5，rc=0 |
| 三个切口检索为 0 | 不适用（软论据） | 已在 `plan/00` §三标注，不在发布面宣称 |
| CI 实跑 | 实现 | 见 §二 run id（三 job 全绿 + annotations 0） |
| 发布三件套 | 实现（本文件 + tag + Release） | 见 §二 |

### 8. CI 接线（v0.1.1）

`.github/workflows/ci.yml` 三个 job，全部 `runs-on: ubuntu-24.04`、`actions/checkout@v7` + `actions/setup-python@v7`：

1. `layout` — `python -X utf8 tools/check_sprint_layout.py`；
2. `test` — `pip install -e ".[dev]"` → `pytest tests -q` → `sqltrace golden data/golden`；
3. `py39-min` — **真装真跑**（`pip install -e ".[dev]"` + 全量 pytest），替代旧的 `py38-syntax`。

> 这条腿立刻兑现了价值：首推 run `39900957482` 上它红了——
> `Path.write_text(newline=...)` 是 **3.10+** 才有的参数，3.9 抛 `TypeError`。改成 `open(..., newline=...)`
> 后 run `39901086436` 三 job 全绿。**旧的 `ast.parse` 腿永远看不见这类运行期 API 差异。**

### 9. tag 前状态

- 交付面（`src/`、`data/`、`tests/`、`docs/`、`pyproject.toml`、`README.md`、`LICENSE`、`.github/workflows/`、`.gitattributes`）已冻结。
- tag 之后**只允许非交付面提交**（`plan/`、`update/`、状态回写）；两条判据：POST_TAG_SCOPE + DELIVERABLE_UNCHANGED。

## 二、tag 后追加（tag 之后写，tag 树内为占位）

> 本节在 tag 提交里是"待追加"状态——tag 树内不自指写哈希与 URL。

| 项 | 值 |
| --- | --- |
| tag 名 | `v0.1.1`（annotated，`git cat-file -t` = `tag`） |
| tag 对象 SHA | `dec1ed1bae3be74a935c618c6b7c8e138f68e03b` |
| tag 指向的 commit | `b29e758e2f294e92209afa5dced5ba1a14eb98b3` |
| 远端仓库 | `https://github.com/yuluo554/sqltrace`（public） |
| Release URL | `https://github.com/yuluo554/sqltrace/releases/tag/v0.1.1` |
| 上传产物 | `sqltrace-0.1.1-py3-none-any.whl`（45,094 B）、`sqltrace-0.1.1.tar.gz`（62,487 B）、`SHA256SUMS`（186 B），三件均 `uploaded`；Release 为 `draft=false` / `prerelease=false` / `latest` |
| GitHub asset digest | wheel `sha256:3e1730c87e6cc9d5186713883c38caf41c7c95744135d8d4181b7509336ccd0e`；sdist `sha256:d307dcce85f245bc1a8b74fef5a5d9835254b52d67adcd5d0f28c856b24b942c`；`SHA256SUMS` `sha256:9b8eccffb9a72e3086f16c008eae22dc83b60247ef39302e64bbfb705d6f7f87` |
| **三方 sha256 对撞** | 本地构建值 / `SHA256SUMS` 内容 / GitHub asset digest **逐字符相同**；匿名 `sha256sum -c SHA256SUMS` → 两件 `OK`，rc=0 |
| 匿名可达性（**不带 token**） | `curl https://api.github.com/repos/yuluo554/sqltrace/releases/latest` → `tag_name = v0.1.1`；三个附件 `curl -L -o` 均 `200`（首次出现过一次 `000` 瞬时失败，重试即 `200`——github.com:443 间歇不稳是本批已知网络坑） |
| 下载产物安装验证 | 匿名 `curl` 取回的 wheel → 全新 venv → `sqltrace 0.1.1`；`golden` 5/5、rc=0；`lineage data/corpus --json` = **54 文件 / 61 语句 / 232 边 / 10 诊断 / passed=true**；三条真实 DML 落 3 条 `unsupported_write_statement` 且 `passed=true` |
| tag 树自足复验 | 浅克隆 tag 树 → 自建 venv `-e ".[dev]"` → **129 passed**、布局门**全绿**、`golden` **5/5**；`git status --porcelain` 空 |
| 从 tag 树归档的换行 | `git archive v0.1.1 src/sqltrace/__init__.py \| tar xO \| od -c \| grep -c '\r'` → **0**（2C 的 `.gitattributes` 生效，v0.1.0 时这里是 CRLF） |
| CI run id（tag 树之前的发布提交） | `39901466384`（`ci` / `main` / push，**success**，23s）：布局门 / 全量测试 + 五条 golden（3.12） / 最低支持版本 3.9 真装真跑，三 job 均 `ubuntu-24.04` |
| CI annotations | 三 job 各 **0** 条（`Node.js 20 is deprecated` 与 ubuntu-latest 迁移 notice 都已消失） |
| CI 结论措辞 | **CI 绿**（真实 run id 已回填；Linux 侧三 job 全绿） |

### tag 后提交范围（POST_TAG_SCOPE + DELIVERABLE_UNCHANGED）

本轮 tag 后的提交只改 `plan/RELEASE-M6.1.md` §二 与 `update/`（后者已在 `.gitignore`，不入库）。
`src/`、`data/`、`tests/`、`docs/`、`pyproject.toml`、`README.md`、`release/SHA256SUMS`、`.github/`、`.gitattributes` **零改动**。

### 未验证项（如实登记）

- **macOS 未跑**（CI 只有 ubuntu 系 runner）。
- **真实 py3.9 本机未验**：本机只有 3.8.8 与 3.12.10；3.9 由 CI 的 `py39-min` job 真装真跑验证（`python 3.9.25 / sqlglot 30.24.0`、129 passed）。该腿首推即抓到 `Path.write_text(newline=)` 是 3.10+ API（run `39900957482` 红），修后转绿。
- PyPI 未发布（D13 定案：只走 GitHub Release 附产物）。
- `UPDATE` / `DELETE` 的**列级血缘**未实现（DEC-1 乙案边界）：只保证"不静默"，不宣称"DML 也有列级血缘"。
- **HTTPS push 通道不稳**：`git push origin main` 与 `git push origin v0.1.1` 本次各失败过一次（`Failed to connect to github.com port 443`），tag 最终走 `ssh://git@ssh.github.com:443/yuluo554/sqltrace.git` 推成功；`gh api` 与匿名 `curl` 全程可用。
