CREATE TABLE stage_pay (
    id number,
    ord_id number,
    pay_amt number(38,2),
    pay_dt date
);
CREATE TABLE stage_ref (
    ord_id number,
    ref_amt number(38,2)
);
