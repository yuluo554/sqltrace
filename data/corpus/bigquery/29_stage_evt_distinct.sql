CREATE TABLE stage_evt_distinct AS
SELECT DISTINCT usr, ev FROM stage_evt_clean;
