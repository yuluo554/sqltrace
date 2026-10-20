-- CASE：THEN/ELSE 为 value，WHEN 谓词为 control
CREATE TABLE stage_cust_enrich AS
SELECT c.id,
       CASE WHEN c.ct = 'x' THEN c.nm ELSE 'foo' END AS nm,
       c.ct,
       c.dt
FROM raw_cust c;
