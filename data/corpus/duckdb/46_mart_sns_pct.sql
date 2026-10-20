-- 表达式混合字面量：likes 为 value
CREATE TABLE mart_sns_pct AS
SELECT post_id, likes * 100 AS likes_pct
FROM stage_sns_clean;
