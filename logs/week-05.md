# Week 5

**Dates:** 08-24 to 08-28

## Goals

- Get a definitive answer on which of the two merged files — `merged.parquet` or `merged_deduped.parquet` — is the one to build all future work on, since both now exist and only one should be treated as canonical

## Approach and Implementation

This was a lighter week, mostly a follow-up consultation rather than new pipeline work. I walked back through the reasoning for the current file layout: why Parquet plus DuckDB was the right combination for this scale, why the pipeline keeps one file per table rather than a single monolithic source, and specifically why `merged.parquet` (14,467 columns, pre-dedup) was kept on disk at all instead of being deleted once `merged_deduped.parquet` existed.

## Results

- Confirmed `data/merged_deduped.parquet` (113,386 rows × 14,066 columns) is the file to build on going forward
- `data/merged.parquet` (14,467 columns) is retained only as a historical pre-dedup record, not for active use

## Notes

- No changes to the open items list from Week 3: `rxq_rx` exclusion, the 137-participant gap, the 149 flagged duplicate-variable cases, and the 71 coverage ties are all still open
