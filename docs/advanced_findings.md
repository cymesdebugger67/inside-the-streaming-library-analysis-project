# Advanced Historical Streaming Library Analysis

**Project owner:** Cyril James Lunzaga

This is a descriptive extension of the undated historical source snapshot, not an estimate of modern catalogues, subscribers, causation, or current streaming availability.

## Research extensions

The analyses compare release-era mixtures, observed-score coverage, genre specialization, directional overlap, membership multiplicity, and the descriptive sensitivity of observed IMDb averages to release-era composition.

## Release-era composition

| Platform | Pre-2000 (%) | 2010–2020 (%) |
|---|---:|---:|
| Netflix | 6.43 | 83.48 |
| Hulu | 10.19 | 77.52 |
| Prime Video | 29.33 | 51.47 |
| Disney+ | 37.77 | 29.61 |

Release eras describe film production dates, not acquisition dates or catalogue-growth trajectories.

## Rotten Tomatoes recorded score coverage

| Platform | 2010–2020 score coverage (%) |
|---|---:|
| Netflix | 39.13 |
| Hulu | 70.14 |
| Prime Video | 27.28 |
| Disney+ | 53.29 |

Coverage differences may reflect source completeness, time period and data acquisition; they do not establish the quality of a catalogue.

## Genre specialization

Genre prevalence is defined as the share of each platform’s recorded movies tagged with a genre, allowing multi-tag counts. The specialization ratio divides platform prevalence by prevalence among unique source records. The ratio is descriptive, not a significance test.

| Platform | Most overrepresented genre (at least 100 tagged platform films) | Ratio to union |
|---|---:|---:|
| Netflix | Animation | 1.47 |
| Hulu | Family | 1.29 |
| Prime Video | Western | 1.22 |
| Disney+ | Family | 8.43 |

## Directional overlap

| Platform pair | Shared IDs | % of first platform | % of second platform |
|---|---:|---:|---:|
| Netflix / Hulu | 25 | 0.70 | 2.77 |
| Netflix / Prime Video | 345 | 9.69 | 2.79 |
| Netflix / Disney+ | 10 | 0.28 | 1.77 |
| Hulu / Prime Video | 241 | 26.69 | 1.95 |
| Hulu / Disney+ | 7 | 0.78 | 1.24 |
| Prime Video / Disney+ | 19 | 0.15 | 3.37 |

Asymmetry exists because the two directional percentages use different denominators. Titles may appear on more than two represented services.

## Membership multiplicity

| Represented platforms per movie | Unique movie records |
|---|---:|
| 1 | 16,117 |
| 2 | 617 |
| 3 | 10 |
| 4 | 0 |

## Release-era standardization sensitivity

The standardized observed IMDb mean weights platform-by-era observed score means by the release-era distribution of the pooled unique-movie source IDs. All historical-era strata are represented, but missing score patterns may be selective. This is an observational composition sensitivity, not a causal adjustment or quality comparison.

| Platform | Raw observed IMDb mean | Release-era standardized observed mean | Change |
|---|---:|---:|---:|
| Netflix | 6.253 | 6.380 | +0.127 |
| Hulu | 6.138 | 6.275 | +0.137 |
| Prime Video | 5.771 | 5.759 | -0.012 |
| Disney+ | 6.441 | 6.579 | +0.138 |

## Methodological boundaries

The source was not sampled randomly from all available films or contemporary streaming services. A record ID is a source key and need not represent a globally deduplicated film. A multi-platform flag does not establish territorial rights or simultaneous availability. Release year is not a date of joining a platform. Missing values remain missing; ratings are summarized only where observed. Age classifications and multi-label genres reflect the historical source text.

These analyses are descriptive: no hypothesis-testing p-values, population intervals, market-share estimates, subscriber forecasts, causal claims or recommendation-engine performance are asserted.

## Reproduction

Run `python -m streaming_library.advanced_analysis` after preparing verified Phases 02–05. Inspect the generated CSV tables, six PNG figures and `advanced_qa.json` in `outputs/phase08_advanced/`. This output folder is intentionally Git-ignored. For public figure display, publish the independently generated plots included in `assets/advanced/` after confirming that local output hashes match.
