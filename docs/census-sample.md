# 写入者普查 · sqltrace 0.1.1

> 事实报表，不含风险分/冲突概率。口径：`data/README.md` §4.8。

## 摘要

| 项 | 计数 |
| --- | --- |
| 写入者语句 | 42 |
| 读者语句 | 54 |
| 有读无写（orphan） | 11 |
| 多写冲突（multi_writer） | 1 |
| 只写不读（write_only） | 22 |

## 写入者

| 表 | 语句数 | 写入者 |
| --- | --- | --- |
| `mart_amt_x_sum` | 1 | `bigquery/26_mart_amt_x_sum.sql#0`（bigquery） |
| `mart_flag_count` | 1 | `snowflake/14_mart_flag_count.sql#0`（snowflake） |
| `mart_inv_daily` | 1 | `tsql/33_mart_inv_daily.sql#0`（tsql） |
| `mart_inv_daily_reader` | 1 | `tsql/39_mart_inv_daily_reader.sql#0`（tsql） |
| `mart_inv_var` | 1 | `tsql/34_mart_inv_var.sql#0`（tsql） |
| `mart_item_summary` | 1 | `postgres/05_mart_item_summary.sql#0`（postgres） |
| `mart_loc_map` | 1 | `tsql/38_mart_loc_map.sql#0`（tsql） |
| `mart_pay_daily` | 1 | `snowflake/11_mart_pay_daily.sql#0`（snowflake） |
| `mart_pay_diff` | 1 | `snowflake/12_mart_pay_diff.sql#0`（snowflake） |
| `mart_pay_rn` | 1 | `snowflake/17_mart_pay_rn.sql#0`（snowflake） |
| `mart_pay_view` | 1 | `snowflake/16_mart_pay_view.sql#0`（snowflake） |
| `mart_pct_pick` | 1 | `duckdb/47_mart_pct_pick.sql#0`（duckdb） |
| `mart_rank_pick` | 1 | `bigquery/28_mart_rank_pick.sql#0`（bigquery） |
| `mart_rn_pick` | 1 | `snowflake/18_mart_rn_reader.sql#0`（snowflake） |
| `mart_sales_daily` | 1 | `postgres/03_mart_sales_daily.sql#0`（postgres） |
| `mart_sales_daily_rd` | 1 | `postgres/04_mart_sales_daily_rd.sql#0`（postgres） |
| `mart_sns_pct` | 1 | `duckdb/46_mart_sns_pct.sql#0`（duckdb） |
| `mart_tag_daily` | 1 | `duckdb/43_mart_tag_daily.sql#0`（duckdb） |
| `mart_tag_qualify` | 1 | `duckdb/44_mart_tag_qualify.sql#0`（duckdb） |
| `mart_tag_top` | 1 | `duckdb/48_mart_tag_top.sql#0`（duckdb） |
| `mart_union_all` | 1 | `postgres/09_mart_union_all.sql#0`（postgres） |
| `mart_usr_daily` | 1 | `bigquery/23_mart_usr_daily.sql#0`（bigquery） |
| `mart_usr_daily_rank` | 1 | `bigquery/24_mart_usr_daily_rank.sql#0`（bigquery） |
| `raw_orphan` | 1 | `50_mart_orphan.sql#0`（postgres） |
| `stage_cust_enrich` | 1 | `postgres/02_stage_cust_enrich.sql#0`（postgres） |
| `stage_evt_clean` | 1 | `bigquery/21_stage_evt_clean.sql#0`（bigquery） |
| `stage_evt_distinct` | 1 | `bigquery/29_stage_evt_distinct.sql#0`（bigquery） |
| `stage_evt_join_cfg` | 1 | `bigquery/22_stage_evt_join_cfg.sql#0`（bigquery） |
| `stage_evt_x` | 1 | `bigquery/25_stage_evt_x.sql#0`（bigquery） |
| `stage_hot` | 2 | `51_mart_multi_writer.sql#0`（postgres）<br>`52_stage_hot_w2.sql#0`（postgres） |
| `stage_inv_backup` | 1 | `tsql/37_stage_inv_backup.sql#0`（tsql） |
| `stage_inv_clean` | 1 | `tsql/31_stage_inv_clean.sql#0`（tsql） |
| `stage_inv_wh` | 1 | `tsql/32_stage_inv_wh.sql#0`（tsql） |
| `stage_orders_clean` | 1 | `postgres/01_stage_orders_clean.sql#0`（postgres） |
| `stage_pay_backup` | 1 | `snowflake/19_stage_pay_backup.sql#0`（snowflake） |
| `stage_pay_flag` | 1 | `snowflake/13_stage_pay_flag.sql#0`（snowflake） |
| `stage_sns_clean` | 1 | `duckdb/41_stage_sns_clean.sql#0`（duckdb） |
| `stage_sns_cte` | 1 | `duckdb/49_stage_sns_cte.sql#0`（duckdb） |
| `stage_sns_tags` | 1 | `duckdb/42_stage_sns_tags.sql#0`（duckdb） |
| `stage_union_src_a` | 1 | `postgres/07_stage_union_src_a.sql#0`（postgres） |
| `stage_union_src_b` | 1 | `postgres/08_stage_union_src_b.sql#0`（postgres） |

## 读取者

| 表 | 语句数 | 读取者 |
| --- | --- | --- |
| `mart_inv_daily` | 1 | `tsql/39_mart_inv_daily_reader.sql#0`（tsql） |
| `mart_pay_rn` | 1 | `snowflake/18_mart_rn_reader.sql#0`（snowflake） |
| `mart_sales_daily` | 1 | `postgres/04_mart_sales_daily_rd.sql#0`（postgres） |
| `mart_sns_pct` | 1 | `duckdb/47_mart_pct_pick.sql#0`（duckdb） |
| `mart_tag_daily` | 1 | `duckdb/44_mart_tag_qualify.sql#0`（duckdb） |
| `mart_tag_qualify` | 1 | `duckdb/48_mart_tag_top.sql#0`（duckdb） |
| `mart_usr_daily` | 1 | `bigquery/24_mart_usr_daily_rank.sql#0`（bigquery） |
| `mart_usr_daily_rank` | 1 | `bigquery/28_mart_rank_pick.sql#0`（bigquery） |
| `raw_cfg` | 2 | `bigquery/22_stage_evt_join_cfg.sql#0`（bigquery）<br>`bigquery/27_raw_cfg_reader.sql#0`（bigquery） |
| `raw_cust` | 3 | `postgres/02_stage_cust_enrich.sql#0`（postgres）<br>`postgres/07_stage_union_src_a.sql#0`（postgres）<br>`postgres/08_stage_union_src_b.sql#0`（postgres） |
| `raw_evt` | 1 | `bigquery/21_stage_evt_clean.sql#0`（bigquery） |
| `raw_inv` | 1 | `tsql/31_stage_inv_clean.sql#0`（tsql） |
| `raw_itm` | 2 | `postgres/05_mart_item_summary.sql#0`（postgres）<br>`postgres/06_raw_itm_reader.sql#0`（postgres） |
| `raw_ord` | 2 | `postgres/01_stage_orders_clean.sql#0`（postgres）<br>`postgres/05_mart_item_summary.sql#0`（postgres） |
| `raw_orphan` | 1 | `51_mart_multi_writer.sql#0`（postgres） |
| `raw_sns` | 5 | `52_stage_hot_w2.sql#0`（postgres）<br>`duckdb/41_stage_sns_clean.sql#0`（duckdb）<br>`duckdb/42_stage_sns_tags.sql#0`（duckdb）<br>`duckdb/43_mart_tag_daily.sql#0`（duckdb）<br>`duckdb/45_stage_sns_reader.sql#0`（duckdb） |
| `raw_tag` | 2 | `duckdb/42_stage_sns_tags.sql#0`（duckdb）<br>`duckdb/43_mart_tag_daily.sql#0`（duckdb） |
| `raw_wh` | 2 | `tsql/32_stage_inv_wh.sql#0`（tsql）<br>`tsql/38_mart_loc_map.sql#0`（tsql） |
| `stage_cust_enrich` | 1 | `postgres/04_mart_sales_daily_rd.sql#0`（postgres） |
| `stage_evt_clean` | 4 | `bigquery/22_stage_evt_join_cfg.sql#0`（bigquery）<br>`bigquery/23_mart_usr_daily.sql#0`（bigquery）<br>`bigquery/25_stage_evt_x.sql#0`（bigquery）<br>`bigquery/29_stage_evt_distinct.sql#0`（bigquery） |
| `stage_evt_x` | 1 | `bigquery/26_mart_amt_x_sum.sql#0`（bigquery） |
| `stage_inv_clean` | 4 | `tsql/32_stage_inv_wh.sql#0`（tsql）<br>`tsql/33_mart_inv_daily.sql#0`（tsql）<br>`tsql/35_stage_inv_reader.sql#0`（tsql）<br>`tsql/37_stage_inv_backup.sql#0`（tsql） |
| `stage_inv_wh` | 1 | `tsql/34_mart_inv_var.sql#0`（tsql） |
| `stage_orders_clean` | 1 | `postgres/03_mart_sales_daily.sql#0`（postgres） |
| `stage_pay` | 6 | `snowflake/11_mart_pay_daily.sql#0`（snowflake）<br>`snowflake/12_mart_pay_diff.sql#0`（snowflake）<br>`snowflake/13_stage_pay_flag.sql#0`（snowflake）<br>`snowflake/16_mart_pay_view.sql#0`（snowflake）<br>`snowflake/17_mart_pay_rn.sql#0`（snowflake）<br>`snowflake/19_stage_pay_backup.sql#0`（snowflake） |
| `stage_pay_flag` | 1 | `snowflake/14_mart_flag_count.sql#0`（snowflake） |
| `stage_ref` | 2 | `snowflake/12_mart_pay_diff.sql#0`（snowflake）<br>`snowflake/15_stage_ref_reader.sql#0`（snowflake） |
| `stage_sns_clean` | 2 | `duckdb/46_mart_sns_pct.sql#0`（duckdb）<br>`duckdb/49_stage_sns_cte.sql#0`（duckdb） |
| `stage_union_src_a` | 1 | `postgres/09_mart_union_all.sql#0`（postgres） |
| `stage_union_src_b` | 1 | `postgres/09_mart_union_all.sql#0`（postgres） |

## 有读无写（orphan）

| 表 | 读取者 |
| --- | --- |
| `raw_cfg` | `bigquery/22_stage_evt_join_cfg.sql#0`<br>`bigquery/27_raw_cfg_reader.sql#0` |
| `raw_cust` | `postgres/02_stage_cust_enrich.sql#0`<br>`postgres/07_stage_union_src_a.sql#0`<br>`postgres/08_stage_union_src_b.sql#0` |
| `raw_evt` | `bigquery/21_stage_evt_clean.sql#0` |
| `raw_inv` | `tsql/31_stage_inv_clean.sql#0` |
| `raw_itm` | `postgres/05_mart_item_summary.sql#0`<br>`postgres/06_raw_itm_reader.sql#0` |
| `raw_ord` | `postgres/01_stage_orders_clean.sql#0`<br>`postgres/05_mart_item_summary.sql#0` |
| `raw_sns` | `52_stage_hot_w2.sql#0`<br>`duckdb/41_stage_sns_clean.sql#0`<br>`duckdb/42_stage_sns_tags.sql#0`<br>`duckdb/43_mart_tag_daily.sql#0`<br>`duckdb/45_stage_sns_reader.sql#0` |
| `raw_tag` | `duckdb/42_stage_sns_tags.sql#0`<br>`duckdb/43_mart_tag_daily.sql#0` |
| `raw_wh` | `tsql/32_stage_inv_wh.sql#0`<br>`tsql/38_mart_loc_map.sql#0` |
| `stage_pay` | `snowflake/11_mart_pay_daily.sql#0`<br>`snowflake/12_mart_pay_diff.sql#0`<br>`snowflake/13_stage_pay_flag.sql#0`<br>`snowflake/16_mart_pay_view.sql#0`<br>`snowflake/17_mart_pay_rn.sql#0`<br>`snowflake/19_stage_pay_backup.sql#0` |
| `stage_ref` | `snowflake/12_mart_pay_diff.sql#0`<br>`snowflake/15_stage_ref_reader.sql#0` |

## 多写冲突（multi_writer）

| 表 | 写入者数 | 写入者 |
| --- | --- | --- |
| `stage_hot` | 2 | `51_mart_multi_writer.sql#0`<br>`52_stage_hot_w2.sql#0` |

## 只写不读（write_only）

| 表 | 写入者 |
| --- | --- |
| `mart_amt_x_sum` | `bigquery/26_mart_amt_x_sum.sql#0` |
| `mart_flag_count` | `snowflake/14_mart_flag_count.sql#0` |
| `mart_inv_daily_reader` | `tsql/39_mart_inv_daily_reader.sql#0` |
| `mart_inv_var` | `tsql/34_mart_inv_var.sql#0` |
| `mart_item_summary` | `postgres/05_mart_item_summary.sql#0` |
| `mart_loc_map` | `tsql/38_mart_loc_map.sql#0` |
| `mart_pay_daily` | `snowflake/11_mart_pay_daily.sql#0` |
| `mart_pay_diff` | `snowflake/12_mart_pay_diff.sql#0` |
| `mart_pay_view` | `snowflake/16_mart_pay_view.sql#0` |
| `mart_pct_pick` | `duckdb/47_mart_pct_pick.sql#0` |
| `mart_rank_pick` | `bigquery/28_mart_rank_pick.sql#0` |
| `mart_rn_pick` | `snowflake/18_mart_rn_reader.sql#0` |
| `mart_sales_daily_rd` | `postgres/04_mart_sales_daily_rd.sql#0` |
| `mart_tag_top` | `duckdb/48_mart_tag_top.sql#0` |
| `mart_union_all` | `postgres/09_mart_union_all.sql#0` |
| `stage_evt_distinct` | `bigquery/29_stage_evt_distinct.sql#0` |
| `stage_evt_join_cfg` | `bigquery/22_stage_evt_join_cfg.sql#0` |
| `stage_hot` | `51_mart_multi_writer.sql#0`<br>`52_stage_hot_w2.sql#0` |
| `stage_inv_backup` | `tsql/37_stage_inv_backup.sql#0` |
| `stage_pay_backup` | `snowflake/19_stage_pay_backup.sql#0` |
| `stage_sns_cte` | `duckdb/49_stage_sns_cte.sql#0` |
| `stage_sns_tags` | `duckdb/42_stage_sns_tags.sql#0` |
