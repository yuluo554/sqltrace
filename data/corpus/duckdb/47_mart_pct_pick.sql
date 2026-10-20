INSERT INTO mart_pct_pick (post_id, likes_pct)
SELECT post_id, likes_pct FROM mart_sns_pct WHERE likes_pct > 1;
