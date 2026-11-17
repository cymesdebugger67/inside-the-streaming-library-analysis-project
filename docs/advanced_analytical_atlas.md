# Advanced Analytical Atlas — Methods and Interpretation

**Project owner:** Cyril James Lunzaga

This purpose-built extension uses the verified historical source IDs and source labels only. It extends rather than supersedes the overlap, Shapley, Shannon and missingness methods in the earlier phases.

## Eight new analytical tables

| Table | Question | Unit / denominator |
|---|---|---|
| `release_era_profile.csv` | How do release-era mixtures differ? | Platform membership; all movies on that platform |
| `metadata_coverage_by_era.csv` | Where do recorded country, language and Rotten Tomatoes labels become sparse? | Platform × era membership |
| `observed_scores_by_era.csv` | How do score/runtime completeness and *observed* means change by era? | Platform × era membership; observed values for means |
| `imdb_era_standardization.csv` | How sensitive are observed IMDb means to differences in film release eras? | Observed score means within each era, weighted by source-union era share |
| `genre_specialization.csv` | Which source labels are more prevalent on each platform than in the unique-record source union? | Fraction of tagged platform records divided by fraction of tagged unique union records |
| `overlap_asymmetry.csv` | How much does each platform's denominator change the interpretation of shared titles? | Shared source IDs divided separately by each platform size |
| `membership_multiplicity.csv` | How many distinct source IDs appear on 1, 2, 3 or 4 represented platforms? | Unique source IDs |
| `age_classification_profile.csv` | How does source age-classification composition vary? | Platform membership; original source label, including missing |

## Six figures

Release-era composition, genre specialization, Rotten Tomatoes coverage-by-era, IMDb release-era standardization, directional overlap and membership multiplicity. Each is regenerated from the eight tables, not from copied values. The static images in `assets/advanced/` were generated from the archived verified source; reproduce locally and compare against their corresponding SHA-256 values before considering them release-ready.

## What the standardization does—and does not do

For platform p, the standardized IMDb mean is `sum_e w_e * observed_mean(p,e)` where `w_e` is the proportion of all **unique source movie records** in release era e. Each within-era mean conditions on a recorded IMDb value. Different metadata missingness, genre composition, and selection persist. A standardized mean is neither a platform quality estimate nor proof of what would happen if platforms changed their libraries.

## Reproduction

After completing and verifying Phases 02–05, run `python -m streaming_library.advanced_analysis`. It refuses to overwrite `outputs/phase08_advanced`, writes eight CSVs, six PNGs, a source-grounded narrative and a hash manifest. Verify with `python -m unittest discover -s tests -p "test_*.py" -q`. Explore with `python -m streamlit run streaming_library/advanced_dashboard.py` or `notebooks/advanced_analytical_atlas.ipynb`.

## Boundaries

This is one undated historical and nonrandom sample. Platform flags overlap. Release year is not a listing timestamp. Source IDs are not independently validated cross-provider film identities. Multilabel genres and source country/language classifications may be incomplete, ambiguous or inconsistent. Comparisons and heatmaps summarize the archive, not a causal process, commercial market, statistical population or contemporary catalogue.
