# Phase 04 — Comparative catalogue structure and observability

**Project owner:** Cyril James Lunzaga

This phase uses the exact hash-verified Phase 02 prepared data and re-verifies all Phase 03 output hashes, including the locally excluded `movie_features.csv`. The output is a historical descriptive comparison, not sampling-based inference. Unknown capture date and source-selection procedures, overlapping platform memberships, and non-random missingness preclude credible population tests and causal assertions. No p-values or confidence intervals are fabricated.

## New analytical dimensions

- **Overlap asymmetry:** shared movies, unique-to-each-pair counts, platform-specific overlap shares, and Jaccard. Shared identities use the archived source ID only.
- **Genre diversity:** movie-level genre prevalence is multi-label and non-additive. Fractional weighting gives each genre-tagged movie total weight one, allocating 1/k across its k genre tags. The inverse-Simpson effective genre count is computed from fractional genre shares. Genre-unknown titles are excluded from the diversity distribution and shown separately as a denominator qualification. More effective genres is not evidence of higher content quality.
- **Release-era composition:** five mutually exclusive release-year cohorts, culminating in 2010–2020. These are release dates, not dates of platform entry; categories must not be plotted as a time-series of service catalogues.
- **Stratified observation coverage:** observed N, missing N, percentage observed, observed mean and observed median for IMDb, Rotten Tomatoes and runtime, separately for each platform and release era. Means are summaries of available cases, not estimates for all titles and not apples-to-apples measures of platform quality.
- **Field completeness:** explicit platform-level missingness denominators.

## Figures

The new figures correct Phase 03's categorical-line visualization weaknesses using a multi-label genre heatmap and release-era small-multiple bars. Two additional charts display per-platform field completeness and fractional genre diversity. These are supplemental figures; original Phase 03 outputs remain untouched.

## Strict quality gates

The implementation validates the Phase 02 source CSVs and entire Phase 03 output manifest, including `movie_features.csv`. It validates identifiers, platform/genre relationships, observational metric ranges, and reconciliation across release-era strata. All outputs are staged and promoted atomically into a new directory, never overwritten. No source rows are modified. Any failed hash or count stops execution before new results are published. Store generated outputs locally, ignored from Git.

## Phase 05 direction

Investigate country/language tag quality before extracting additional features. Consider standardized descriptive comparisons by release era only if coverage and support are adequate. Avoid unmotivated feature selection and machine learning. Complete a comprehensive code/README, dependency, reproducibility and public release audit before GitHub publication.
