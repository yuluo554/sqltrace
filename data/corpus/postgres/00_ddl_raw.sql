CREATE TABLE raw_cust (
    id bigint,
    nm text,
    ct text,
    dt date
);
CREATE TABLE raw_ord (
    id bigint,
    cust_id bigint,
    amt numeric,
    qty int,
    dt date
);
CREATE TABLE raw_itm (
    ord_id bigint,
    sku text,
    qty int
);
