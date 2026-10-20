-- CTE 两层：内层聚合 + 外层窗口
CREATE TABLE stage_sns_cte AS
WITH agg AS (
    SELECT dt, SUM(likes) AS tot_likes
    FROM stage_sns_clean
    GROUP BY dt
)
SELECT dt, tot_likes,
       SUM(tot_likes) OVER (ORDER BY dt) AS cum
FROM agg;
