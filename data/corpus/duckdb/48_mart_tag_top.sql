CREATE TABLE mart_tag_top AS
SELECT tag, dt, tot_likes
FROM mart_tag_qualify
WHERE tag IN ('x', 'y');
