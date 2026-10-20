INSERT INTO stage_sns_clean (post_id, usr, dt, likes)
SELECT p.post_id, p.usr, p.dt, p.likes
FROM raw_sns p;
