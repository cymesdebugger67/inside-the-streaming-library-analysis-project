# Phase 01 — Streaming Source Review

**Project owner:** Cyril James Lunzaga

## Scope and provenance

Historical archived movies-on-streaming-platforms dataset; no claims about present-day availability.

- Original publisher: https://www.kaggle.com/datasets/ruchi798/movies-on-netflix-prime-video-hulu-and-disney
- Retrieval mirror: https://raw.githubusercontent.com/SalimAmarti/OTT_movies_Project/master/MoviesOnStreamingPlatforms_updated.csv
- SHA-256: `c7a1b949495c35879b038c97f92bbe233d1b0b348719f3d4a8020927645c0c27`
- File bytes: 1,942,970
- Audited records: 16,744
- Unique normalized title/year keys: 16,744
- Duplicate-key groups: 0
- Duplicate-key excess rows: 0
- Rows with multiple platform flags: 627

## Platform-flag coverage (source rows)

| Platform | Positive flags |
|---|---:|
| Netflix | 3,560 |
| Hulu | 903 |
| Prime Video | 12,354 |
| Disney+ | 564 |

These counts are not de-duplicated title counts. They must not be interpreted as current platform library sizes.

## Missingness by field

| Field | Missing rows |
|---|---:|
| ID | 0 |
| Title | 0 |
| Year | 0 |
| Age | 9,390 |
| IMDb | 571 |
| Rotten Tomatoes | 11,586 |
| Netflix | 0 |
| Hulu | 0 |
| Prime Video | 0 |
| Disney+ | 0 |
| Type | 0 |
| Directors | 726 |
| Genres | 275 |
| Country | 435 |
| Language | 599 |
| Runtime | 592 |

## Research controls

- Verify duplicate title/year groups and conflicting flags before selecting title-level rules.
- Do not sum multi-label genre tags as though each film belongs to one genre.
- Rate-quality comparisons are secondary because rating missingness is selective.
- Limit conclusions to this dataset's historical coverage; do not infer viewership, demand, or platform strategies.
- Reconfirm data licensing and cite the original source and archival mirror before publication.

## Decision

Data are structurally viable for controlled analysis, subject to Phase 02 duplicate-resolution review.
