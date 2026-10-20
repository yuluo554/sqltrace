CREATE TABLE raw_g3 (a int, b int);
INSERT INTO stage_g3 (c2, c1) SELECT a, b FROM raw_g3;
