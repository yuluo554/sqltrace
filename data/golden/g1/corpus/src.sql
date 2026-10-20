CREATE TABLE raw_w (id int, x int, k int);
INSERT INTO stage_w (id, x, w)
SELECT id, x, SUM(x) OVER (PARTITION BY k) AS w FROM raw_w;
