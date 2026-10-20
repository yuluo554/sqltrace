# g1

窗口分型：SUM(x) OVER (PARTITION BY k) 产出 w<-x(value) + w<-k(control)，禁止 w<-k 的 value 边

输入语料：`corpus/`（M1 冻结）；期望输出：M5 冻结。
