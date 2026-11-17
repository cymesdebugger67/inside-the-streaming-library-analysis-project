# Phase 03 — Historical catalogue composition and exploratory analysis

**Project owner:** Cyril James Lunzaga

## Research contract

This phase answers how the **historical archived movie memberships** differ by platform, release-year composition, genre labels, numeric field completeness and observed ratings. This is a **single undated historical snapshot**; release year is not availability history. No claims about present catalogues, viewership, subscription behaviors, consumer demand, revenue, causal effects or trends in platform entry/exit are justified.

## Inputs and guardrails

Execute `python -m streaming_library.eda` at the repository root after Phase 02. All three prepared CSV files must match the SHA-256 entries in `outputs/phase02_preparation/preparation_qa.json`. IDs must be unique in the movie table, membership and genre pairs must be unique, all memberships and genre assignments must reference an existing movie, and platform totals must reconcile against Phase 02. An existing `outputs/phase03_eda` directory is never overwritten.

Matplotlib is required for the five PNG figures. Install via `python -m pip install matplotlib` only if absent; or use `--no-figures` for QA-only diagnostic output. Phase 03 requires no new external dataset and no model training.

## Purpose-built tables

- `movie_features.csv`: derived **release decade**, broad release era, runtime band, count of distinct genre tags, number of platform memberships, multi-platform indicator and rating availability class. Raw movie identity stays in Phase 02. The features are descriptive, not predictors in a trained model.
- `platform_summary.csv`: platform-specific movie counts, share of distinct source movies, release-year median, runtime median with n, observed IMDb and Rotten Tomatoes means with n and completeness %. **Shares of all platform memberships can exceed 100% combined**; individual platforms are non-exclusive.
- `overlap.csv`: pairwise intersections and unions, Jaccard percentage, and asymmetric share of each platform's catalogue. A shared movie is the same **source ID**, not an external identity-resolution claim.
- `genre_platform.csv`: count of unique movie/genre assignments per platform; denominator is all movies on that platform, even if a genre is missing. Multiple genres per movie mean the percentages do not total 100%.
- `decade_platform.csv`: share of each platform's historical movies released in each decade, **not** platform growth over time.
- `rating_coverage.csv`: observed count, missing/invalid count, and valid share by platform for IMDb, Rotten Tomatoes and runtime.
- `runtime_distribution.csv`: mutually exclusive runtime bands with missing/invalid bucket. All platform memberships reconcile.

The five charts show catalogue memberships, Jaccard overlaps, release-decade distributions, numeric field coverage and non-exclusive genre prevalence. They are descriptive comparisons, **not inferential statistical evidence**. Distinct source IDs are retained throughout, and overlap means group samples are not independent.

## Required review before findings or publication

Review `eda_qa.json` and all PNGs; verify denominators and any visually misleading labels. Read the exact tabular outputs before drafting numerical insights. Assess rating missingness before interpreting means. Keep published figures attributable, include source provenance and original dataset/mirror distinctions, and never publish the ignored raw or generated data unless reuse terms have been separately cleared. Phase 04 may add defensible stratified comparisons, uncertainty estimates and expanded multi-label country/language features if the actual EDA justifies them; **feature selection and machine learning are not mandatory analytics steps** and require a specific prediction target and leakage controls.
