# g3

INSERT 列清单位置映射：INSERT (c1,c2) SELECT 顺序与列名不对应时按清单映射

输入语料：`corpus/`（M1 冻结）。期望：`expected.json`（M5 冻结，按 `data/README.md` §4.1 人工推导）。
验收：`sqltrace golden data/golden`；`c1<-b`、`c2<-a`（按**位置**），按名字对齐的两条是 `forbid`。
