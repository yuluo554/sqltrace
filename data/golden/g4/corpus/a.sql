CREATE TABLE raw_g4 (id int);
INSERT INTO stage_hot (id) SELECT id FROM raw_g4;
