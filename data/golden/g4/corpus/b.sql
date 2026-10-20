INSERT INTO stage_hot (id) SELECT id FROM raw_g4;
INSERT INTO raw_orphan (id) SELECT id FROM raw_g4;
