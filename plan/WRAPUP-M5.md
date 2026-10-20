# WRAPUP-M5 — diff 闸门与输出收尾留档

> M5 非发布里程碑；发布留档在 `plan/RELEASE-M6.md`（tag 前入库）。本份为收尾记录，供布局门 LAYOUT.RELEASE 判据与后续追溯。

## 一、DoD 对账

| DoD 项 | 实现 | 核验 |
| --- | --- | --- |
| `diff --base <git-ref\|dir>` 两模式 | `load_base()`：目录模式 `load_corpus`；git 模式 `git ls-tree -r -z` + `git show <ref>:<path>`（只读，不切工作区）；两模式共用 `loader._assemble_corpus` | `test_git_and_dir_base_produce_identical_edges`、`test_load_corpus_from_texts_matches_dir_mode`、`test_git_mode_does_not_touch_worktree` |
| 边级 diff 三态 | `diff_edges()`：键 `(target, column, kind)`；`ADDED`/`REMOVED`/`CHANGED`（来源集合变化）；`kind` 变化 = 旧键 REMOVED + 新键 ADDED | `test_diff_added_removed_changed_classification`、`test_diff_same_key_multiple_sources_set_change_is_changed`、`test_diff_kind_change_is_removed_plus_added_not_changed` |
| 退出码 §4.4 | `diff_exit_code()`：`REMOVED` 优先 → `1`；仅 `ADDED`/`CHANGED` → `2`；无变化 → `0`；使用错误 → `3`；门红 → `4` | `test_diff_exit_code_matrix`、`test_diff_cli_exit_codes_dir_mode`、`test_diff_cli_usage_error_on_missing_base` |
| `impact` 穿透两层 | `impact()`：正向/反向闭包（上限 §4.7）+ `final_consumers` + `intermediate_tables`（穿透层数的机械判据）+ `reading_statements`（取 `corpus.reads`，K13） | `test_golden_g5_impact_penetrates_two_intermediate_tables`（`intermediate_tables == [mid1, mid2]`、`max_depth == 3`）、`test_impact_cli_reports_readers_from_table_ledger` |
| golden g5 绿 | `data/golden/g5/corpus_v2/v2.sql`（三态齐）+ `expected.json`（人工推导） | `test_golden_g5_diff_all_three_states_and_exit_code`、`test_all_five_golden_green` |
| 五条 golden 一条命令全绿 | `sqltrace golden data/golden` → 5/5，退出码 `0` | `test_golden_cli_exit0_and_shape`；实跑见 §二 |
| `docs/diff-sample.json` 真实输出 | 由 `diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus --json` 直接落盘，1,521 字节 | `test_diff_sample_doc_is_real_output_and_deterministic`（与实时输出逐字节比对） |
| 双跑字节级一致 | `diff` / `golden` 的 `--json` 与 `--md` 两次运行逐字节一致；`\n`、无 CR、无绝对路径、无反斜杠 | `test_diff_json_two_runs_byte_identical`、`test_diff_markdown_two_runs_byte_identical_and_no_crlf`、`test_golden_json_two_runs_byte_identical`、`test_diff_output_has_no_absolute_path` |
| 门复用（§4.9 规则 8） | `gate_check()` = `zero_silence_violations` + `assert_reason_codes`；`diff` 跑基线与当前各一次，`golden` 每份语料一次 | `test_diff_and_golden_reuse_same_gate`、`test_golden_gate_reuse_can_go_red`（两组阳性对照） |

## 二、实跑证据（2026-10-21，本机 Windows）

- 常驻测试 **107 passed**（`PYTHONDONTWRITEBYTECODE=1 py -3.12 -X utf8 -m pytest tests -q`；M5 新增 32 个）。
- `sqltrace golden data/golden`：**5/5 通过**，退出码 `0`（g1–g5 逐条 PASS）。
- `sqltrace diff data/golden/g5/corpus_v2 --base data/golden/g5/corpus`：`REMOVED 1 / ADDED 2 / CHANGED 1`，退出码 `1`（有破坏性变更）。
- `sqltrace diff data/corpus --base HEAD`：`0/0/0`，退出码 `0`（工作区与 HEAD 同源）；`--base HEAD~1` 同为 `0/0/0`。
- git 模式取到 53 个文件 / 59 条语句，与目录模式一致（两模式同内核的直接证据）。
- `sqltrace impact raw_cust.nm data/corpus`：下游 5 列、`max_depth = 2`、`final_consumers = [mart_sales_daily_rd.nm, mart_union_all.nm]`、`intermediate_tables = [stage_cust_enrich, stage_union_src_a, stage_union_src_b]`。
- 双跑确定性：`diff --json` 1,521 字节（`sha256 fe399ddc…` 前缀）、`golden --json` 2,340 字节 —— 两次运行逐字节相同。
- 3.8 语法兼容：`ast.parse(feature_version=(3,8))` 对 `src/sqltrace/*.py` + `tests/*.py` 全绿（未跑 sqlglot）。

## 三、变异验证（门不是空判据）

| 变异 | 预期 | 实测 |
| --- | --- | --- |
| `CHANGED` 判据从"来源集合"改成"语句集合" | 换源漏判 → 红 | **7 failed** |
| 退出码优先级反转（`ADDED/CHANGED` 先于 `REMOVED`） | 破坏性变更被降级成 2 → 红 | **5 failed** |
| `impact` 闭包截断到 1 层 | "穿透两层"承诺落空 → 红 | **3 failed** |
| 目录模式 sha 改回哈希原始字节（与 git 模式口径分裂） | 两模式同源前提失效 → 红 | **2 failed** |
| 去掉 golden 期望 JSON 的顶层键白名单 | 键名拼错静默变绿 → 红 | **1 failed** |

五组均"改坏即红、还原即绿"（还原后 107 passed）。

## 四、实现落点

- `src/sqltrace/diffgate.py`（从 2 行占位骨架变为 643 行 M5 主体）：
  - 基线：`load_base` / `_git` / `_repo_prefix` / `_git_files` / `BaseUsageError`。
  - diff：`_groups` / `diff_edges` / `diff_exit_code` / `_src_name` / `_src_key`。
  - impact：`impact` / `_split_target` / `_graphs` / `_closure` / `_known_tables`。
  - golden：`run_golden` / `GoldenResult` / `_golden_lineage` / `_golden_lineage_forbid` / `_golden_census` / `_golden_diff` / `_golden_impact` / `GOLDEN_SPEC_KEYS`。
  - 门与输出：`gate_check` / `diff_payload` / `render_diff_markdown` / `render_impact_text` / `render_golden_text` / `golden_to_dict` / `_rel_or_none`。
- `src/sqltrace/loader.py`：拆出 `_assemble_corpus`（两模式共用内核）+ 新增 `load_corpus_from_texts`；sha 统一走 `_sha256_text`（删掉哈希原始字节的旧 `_sha256`）。
- `src/sqltrace/cli.py`：`diff` / `impact` / `golden` 三个子命令落地（`--dialect` / `--json` / `--md`）；JSON 一律 `sys.stdout.write(dumps_json(...))`。
- `data/README.md`：新增 **§4.9 diff / impact / golden 口径**（规则 1–9）；§4.4 补"`1`/`2` 是 diff 专属语义"。
- `data/golden/g1..g5/expected.json`：五份期望侧冻结（人工按 §4.1/§4.2/§4.8/§4.9 推导）。
- `data/golden/g5/corpus_v2/v2.sql`：diff 的"当前"版本（三态齐）。
- `docs/diff-sample.json`：真实输出。
- `tests/test_m5_diffgate.py`：**32 个**常驻测试。
- `tests/test_smoke.py`：M0 占位用例改为"骨架在位"检查（`golden` 现在有真实语义，不再恒 `0`）。

## 五、本棒抓到的两个真实缺陷（都写进了测试与风险表）

1. **两模式 sha 口径分裂**：`git rev-parse --show-prefix` 带尾斜杠，直接拼出 `data/corpus//x.sql` → `git show` 退 128；同时目录模式原先哈希原始字节、git 模式哈希解码文本，CRLF 文件下 sha 必然不同。修：`rstrip("/")` + 统一 `_sha256_text`。
2. **`print(dumps_json(...))` 多一个换行**：JSON 尾部出现两个 `\n`，违反 §4.6。修：全部改 `sys.stdout.write`。

两处都是"逐字节比对"这条判据逼出来的，不是靠肉眼。

## 六、遗留（不阻塞 M6）

- `census` / `impact` 的读者口径是**表级**；列级消费者闭包由 `impact` 的边图承担，两者不重复计数（前者进 `reading_statements`，后者进 `downstream_consumers`）。
- `diff` 不做"移动检测"（表改名会被判成一整批 REMOVED + ADDED）——这是口径选择，不是缺陷；如需支持要先改 §4.9。
- `golden` 的 `--dialect` 覆盖对 g5 的 `diff` 子检查同样生效；真实语料与 golden 都不依赖它（方言由目录名判定）。
