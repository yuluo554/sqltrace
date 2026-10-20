# g2

未知 schema 的 SELECT *：零猜测，只产出 unknown_wildcard

输入语料：`corpus/`（M1 冻结）。期望：`expected.json`（M5 冻结，按 `data/README.md` §4.2 人工推导）。
验收：`sqltrace golden data/golden`；边集只有一条 `unknown` 边，目标列用占位 `*`，**一个列名都不猜**。
