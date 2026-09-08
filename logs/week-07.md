# Week 7

**Dates:** 09-07 to 09-11

## Goals

- Kick off a new downstream phase on top of the finished merge: test whether different synthetic-data generators, which can score similarly on standard fidelity tests, actually produce different rankings when used to benchmark FIM-RAG systems
- Select an appropriate clinical slice from `merged_deduped.parquet`, harmonize and tier it, generate synthetic versions with several generator families, and evaluate their fidelity against real data

## Approach and Implementation

Partway through this work, the longer-term motivation came into focus: the actual goal is fine-tuning a specialist model to beat frontier LLMs at medication recommendations for multimorbid patients, which rules out using a frontier model itself as one of the generators being compared, since that would bias the benchmark in its own favor. Ground-truth recommendation labels will come from expert clinician annotation rather than model consensus or real prescribing data (which isn't available anyway, since `rxq_rx` is still excluded).

Before building anything, I checked the experiment spec's assumptions against the real files and found several were wrong: `dictionary.parquet` only has `column_name`/`description`/`units`/`value_coding` (no `source_table` or `codebook_url`), and `units`/`value_coding` are 100% null, consistent with them being scoped for synthetic generation rather than real values. I built a per-column non-null coverage profile entirely in DuckDB (never loading all 14k columns into pandas) and used it to select a slice: `dm_ckd_v1`, 107 columns across 16 clinical blocks built around a type-2-diabetes-plus-kidney-function theme. I also reconfirmed two things flagged before: no eGFR column exists anywhere in the merged file, and no usable prescription table exists.

Harmonizing the slice meant fixing three cross-cycle renames (food-security and kidney-related variables that changed names or category counts across survey cycles) and classifying each column's missingness as subsample, ordinary, or structural; the structural cases came with 8 skip-pattern rules I verified at 100% support (e.g., a follow-up question that only fires when a diabetes-diagnosis question was answered yes). From there I built three tiers: a small core tier, a primary tier (65 columns, cycles 2009–2017, 22,293 rows), and a fasting tier held out of the primary run for having too few rows. I chose an exam weight column to resample training rows proportionally, decided to keep survey year as a modeled column rather than restricting to recent cycles, and wrote a CKD-EPI eGFR calculation as a post-hoc consistency check rather than a training input.

I then generated synthetic versions of the primary tier with three generator families: CTGAN, ran cleanly in about 11 minutes with no malformed rows; a custom compact tabular diffusion model that I wrote from scratch (the standard options need CUDA, which isn't available locally), also clean with only minor range violations on a few hard-bounded columns; and a GReaT/distilgpt2 language-model-based generator, which repeatedly failed on local hardware, first an out-of-memory error during fine-tuning, then a context-length bug that crashed sampling. Even after hardening the sampler with smoke tests, checkpointing, and better validation, it only produced 43 valid rows out of a 17,835 target, which I've documented as a hard floor rather than something to keep debugging locally. I prepared a Colab GPU notebook as a follow-up path.

With two working synthetic datasets, I built a generator-agnostic fidelity evaluation harness and ran five metrics across five seeds each. The discriminator metric saturated (both near-100% detectable, not useful for comparison), but the other four told a clear story: the diffusion model preserved the real predictive relationship between the clinical features and diabetes status much better than CTGAN, stayed close to the real data's own held-out baseline rather than drifting off-manifold, and kept deterministic unit-pair correlations intact where CTGAN badly degraded them.

## Results

- Selected and built the `dm_ckd_v1` slice (107 columns, 16 clinical blocks) with a verified coverage profile, harmonized cross-cycle renames, and three completeness tiers
- Generated two working synthetic datasets (diffusion-based and CTGAN) at the full 17,835-row training target; the LLM-based generator capped at 43/17,835 valid rows locally
- Fidelity evaluation across 5 metrics shows the diffusion model is clearly stronger than CTGAN on the metrics that actually differentiate them; decided to use it as the primary benchmark substrate, with CTGAN kept only as a sensitivity check
- Delivered a 12-slide status-update deck summarizing the experiment and findings

## Notes

- New gap surfaced during evaluation: the primary tier ends up with close to zero diagnosed diabetics, because the same skip-pattern logic that defines it excludes the follow-up questions diabetics would answer: a real problem for a medication-recommendation goal, not yet resolved
- The LLM generator arm is still unresolved: a Colab GPU retry with a smaller batch size and gradient accumulation was set up, but I haven't confirmed the outcome yet, and it's still undecided whether to block the next phase on getting it working or proceed with just the two working generators
- Carrying forward all four still-open items from earlier weeks: `rxq_rx` exclusion, the 137-participant gap, the 71 coverage ties, and 147 of the 149 flagged duplicate-variable cases
