# Research Design — Historical Streaming Catalogue Differentiation

**Project owner:** Cyril James Lunzaga

## Question and scope

How do historically represented catalogue size, unique coverage, overlap and recorded genre variety compare among four platform flags? The source is an undated, third-party historical CSV mirror. The unit is its source movie ID, not a globally verified work identifier. Release year is the film release year, **not** the platform catalogue listing date. This dataset is not a probability sample, usage study, or contemporaneous market survey.

## Implemented estimands and validation

1. **Source and identity controls:** preserve 16,744 source movie rows and unique title-year keys as recorded; validate 17,381 non-exclusive memberships and missing/invalid metadata without imputing ratings or runtime.
2. **Union and overlap:** calculate pairwise Jaccard and directional overlaps; report denominators for each overlap and all 16 possible four-platform coalitions.
3. **Marginal coverage:** distinguish leave-one-out union loss (exclusive records) from exact factorial-weighted **Shapley movie-equivalent allocation** across all coalitions. Each movie shared across k platforms contributes 1/k to each.
4. **Genre variety:** use multi-label genre tags, fractional per-movie weighting and full-tag weighting, Shannon entropy, exp(Shannon) effective genres and inverse-Simpson diversity; report genre-known coverage.
5. **Size sensitivity:** draw equal-size 564-movie subsamples without replacement from each platform's recorded source IDs (200 draws/platform; fixed seed 20261117). This is within-source descriptive sensitivity, not inferential evidence or a confidence interval. Disney+ draws always include its entire 564-movie source set.
6. **Historical metadata:** describe corrected country and named-language label coverage. Literal `None` language tokens do not count as named languages; original source strings remain available.
7. **Observed scores:** compare descriptive coverage and observed means only with explicit missingness and selection-bias caveats. No platform-quality ranking.

## Proposed methods intentionally not used

The original proposal discussed title-level bootstrap intervals, calendar matching and a regularized multi-label classifier. Bootstrapping would quantify resampling variation inside this historical non-probability source, **not** confidence about service populations, and is omitted in favor of clearly identified equal-size sensitivity. Platform membership labels are not demand or user-preference outcomes, so the predictive-model gate is not met. Release-year matching is not pursued as a separate inferential analysis; release-era composition and metadata coverage are already reported as descriptive confounders. These are explicit scope choices, not claims that the methods were performed.

## Reporting and quality policy

Retain dataset fingerprint, stage QA hashes, tests, reproducibility instructions and author attribution. Do not interpret membership flags as present-day platform availability, streaming market share, subscriber behavior, rights exclusivity, demand, causal effect or catalogue growth. Missing genre, country, language, IMDb, Rotten Tomatoes and runtime fields must be reported with clear denominators. Public release requires separate licensing, visual inspection, reproducibility and security gates.
