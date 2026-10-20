CREATE TABLE raw_sns (
    post_id bigint,
    usr text,
    dt date,
    likes int
);
CREATE TABLE raw_tag (
    post_id bigint,
    tag text
);
