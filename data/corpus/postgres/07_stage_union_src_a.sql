CREATE TABLE stage_union_src_a AS
SELECT id, nm FROM raw_cust WHERE dt > '2020-01-01';
