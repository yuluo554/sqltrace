CREATE TABLE raw_src (nm text, cd text);
CREATE TABLE raw_src2 (nm text, cd text);
CREATE TABLE mid1 AS SELECT nm, cd FROM raw_src2;
CREATE TABLE mid2 AS SELECT nm, cd FROM mid1;