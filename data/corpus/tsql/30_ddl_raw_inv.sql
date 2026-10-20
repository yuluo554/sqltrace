CREATE TABLE raw_inv (
    inv_id bigint,
    loc nvarchar(50),
    qty int,
    dt date
);
CREATE TABLE raw_wh (
    loc nvarchar(50),
    wh nvarchar(50)
);
