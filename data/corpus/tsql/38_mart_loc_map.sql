INSERT INTO mart_loc_map (loc, wh)
SELECT loc, wh FROM raw_wh WHERE wh IS NOT NULL;
