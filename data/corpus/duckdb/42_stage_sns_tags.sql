CREATE TABLE stage_sns_tags AS
SELECT p.post_id, t.tag
FROM raw_sns p
JOIN raw_tag t ON t.post_id = p.post_id;
