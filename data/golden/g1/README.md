# g1

窗口分型：SUM(x) OVER (PARTITION BY k) 产出 w<-x(value) + w<-k(control)，禁止 w<-k 的 value 边

输入语料：`corpus/`（M1 冻结）。期望：`expected.json`（M5 冻结，按 `data/README.md` §4.1 人工推导）。
验收：`sqltrace golden data/golden`；`forbid` 里的 `w<-k(value)` 必须**不**出现。
