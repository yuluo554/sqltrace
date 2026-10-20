# g4

多写冲突 + 孤儿表：同一表两个写入者，另两张表只写不读

输入语料：`corpus/`（M1 冻结）。期望：`expected.json`（M5 冻结，按 `data/README.md` §4.8 人工推导）。

- `multi_writer = [stage_hot]`：`a.sql#1` + `b.sql#0`（严格 `len >= 2`，单写入者零误报）。
- `orphan = [raw_g4]`：有读无写（两张文件都 `SELECT ... FROM raw_g4`，无人产出它）。
- `write_only = [raw_orphan, stage_hot]`：两张表都只写不读。

验收：`sqltrace golden data/golden`。
