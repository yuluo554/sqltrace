INSERT INTO mart_tag_daily (dt, tag, tot_likes)
SELECT p.dt, t.tag, SUM(p.likes) AS tot_likes
FROM raw_sns p
JOIN raw_tag t ON t.post_id = p.post_id
GROUP BY p.dt, t.tag;
