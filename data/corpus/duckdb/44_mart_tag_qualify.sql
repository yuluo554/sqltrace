-- DuckDB 支持 QUALIFY：谓词 control
CREATE TABLE mart_tag_qualify AS
SELECT dt, tag, tot_likes
FROM mart_tag_daily
QUALIFY tot_likes >= 1;
