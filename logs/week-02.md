# Week 2

**Dates:** 08-03 to 08-07

## Goals

- Resolve the four open design decisions from Week 1 and incorporate a separate instructions doc Hanu shared, "Merging the 341 NHANES Tables Into One Clean Dataset"
- Build duplicate-variable detection so that the same CDC concept exported under the same name in multiple tables gets collapsed into one canonical column instead of staying duplicated
- Get the wide-table writes to actually complete, they were repeatedly running out of memory and disk

## Approach and Implementation

Hanu shared a separate instructions doc partway through the week, and I confirmed with him that it should win wherever it conflicts with the original merge plan rather than being reconciled or ignored. Two concrete conflicts came up: the plan treats reused variable names across tables as fine as long as they're prefixed, but the instructions doc wants true duplicates (same value, same CDC-described concept) detected and collapsed to one canonical column, and the plan's dictionary is meant to be fully detailed while the doc wants a much lighter one scoped for an LLM to generate synthetic records from.

I also checked one of the plan's stated facts directly against the live CDC pages: the claim that the "Data File Name" cell links out to a codebook page. It doesn't, I confirmed zero `<a>` tags anywhere in the results table across all five component pages, both with a raw grep on the saved HTML and a full tag scan. Every other field the plan describes from that page was still captured normally, but the codebook URL field is genuinely unavailable this way rather than a scraping miss, so I left it null instead of guessing a URL pattern.

For duplicate detection, I built it as a three-stage pipeline rather than one script, since each stage answers a different question and I wanted to be able to inspect the output at each step before acting on it. First, a scan over every variable name that appears in more than one of the 322 eligible tables (2,197 of them), checking value agreement across tables per participant-cycle: 456 candidates passed with high agreement, the other 1,741 mostly turned out to have zero row overlap at all, which confirmed the instructions doc's own caution that name-matching alone would produce false positives. Second, for those 456 candidates, I cross-checked CDC's own variable descriptions across each variable's tables, which meant mapping our lowercase table names to CDC's cycle-suffixed Data File Names by stripping cycle suffixes without assuming a fixed pattern, since real table names contain underscores too. Third, for the confirmed duplicates, I resolved each one by keeping the copy with the most non-null coverage in the merged table, a data-driven choice rather than guessing which table a variable semantically belongs to, and flagged the cases where coverage tied instead of resolving them silently.

The wide-table writes turned out to be the hardest part of the week, not the logic. Writing 14,000+ columns repeatedly exhausted memory or disk on my machine, and I had to work through several rounds of tuning: switching the per-table merge step from a rewrite that recopies every already-merged column on each step to one that only touches the new table's own columns, moving the working database from in-memory to disk-backed, and reducing row group size and thread count for the final write to cut peak temp-spill. The same issue came back for the dedup step specifically because re-selecting columns out of the parquet file forces DuckDB to decode every retained column during the scan, so I switched that step to drop columns directly on the native table instead.

I also decided what to do with the 18 confirmed multi-row tables. Rather than invent a per-table summarization rule for each one, which needs real analytic judgment nobody had given me, I kept all 18 in their original per-item row shape as separate files linked back to the main dataset by participant-cycle, with a manifest explaining each one. This is lossless and reversible, summarizing them later from the originals is still possible, but a guessed summarization rule applied now would not be undoable.

## Results

- 307 confirmed duplicate variables collapsed to one canonical column each
- 149 name-matched candidates left as separate, still-prefixed columns pending manual review: 75 where values agree but CDC's descriptions differ, 61 where a table's own description changed across its cycles, and 13 with no CDC description at all
- 71 ties on coverage broken alphabetically and flagged rather than resolved silently, mostly one repeating pattern of near-identical survey-weight variables copied across the anxiety and depression module tables
- `data/merged_deduped.parquet` written at 113,386 rows by 14,066 columns, down from 14,467, with the original pre-dedup `merged.parquet` kept untouched
- All 18 multi-row tables preserved losslessly in `data/multi_row/` with a manifest, none summarized or dropped
- Wide-table writes now complete reliably on a memory- and disk-constrained machine after the tuning changes above

## Notes

- Remaining open items I still need input on: how to handle `rxq_rx`'s encoding defect, whether a table of 137 participants present in other tables but missing from the demographics file for the 1999 cycle is expected or a data problem, and manual review of the 149 flagged duplicate-variable cases
- Confirmed with Hanu before building the dedup pipeline on top of the already-verified merge rather than redoing the merge itself with dedup built in from the start, since the merge was already the riskiest and most disk-constrained part of the pipeline and redoing it had no correctness benefit
