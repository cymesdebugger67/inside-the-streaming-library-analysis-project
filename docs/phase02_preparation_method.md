# Phase 02 — Historical Movie Catalogue Preparation

**Project owner:** Cyril James Lunzaga

## Purpose

Prepare source-faithful, auditable tables for *Inside the Streaming Library*. All observations describe an archived movie catalogue with an unverified snapshot date. They do not demonstrate current availability, viewership, demand, subscriptions, or changes over calendar time.

## Inputs and reproducibility

- `data/raw/historical_streaming_movies.csv`: exact historical source verified against the Phase 01 source manifest.
- `outputs/source_viability/source_audit.json`: Phase 01 quality contract and SHA-256 reference.
- Run from the repository root: `python -m streaming_library.preparation`.
- The command creates a **new** `outputs/phase02_preparation/` folder. It refuses to overwrite existing results. Review or archive an existing run before intentionally removing it.

## Output grain

| Table | Grain | Interpretation |
|---|---|---|
| `movies_clean.csv` | One row per source ID | The source film record, with validated optional numeric fields and preserved raw descriptive labels |
| `platform_memberships.csv` | One row per source ID and flagged platform | Non-exclusive catalogue memberships; a film can appear on several platforms |
| `movie_genres.csv` | One row per source ID and distinct genre label | Multi-label genre assignments, not mutually exclusive film classes |
| `preparation_qa.json` | One preparation run | Source fingerprints, counts, parse statuses, reconciliations, and limitations |

## Transformations and guards

- Validate the Phase 01 source fingerprint, required header fields, positive binary platform flags, and movie-only `Type=0` status.
- Require unique source IDs and unique case-folded, whitespace-normalized title/year identities. Any unexpected collision stops the run rather than silently selecting a survivor. This is **not** an external identity-resolution claim.
- Preserve title, age, directors, genres, country, and language as recorded after trimming outer whitespace. Do not guess missing labels.
- Accept observed IMDb forms such as `7.8/10` and Rotten Tomatoes forms such as `88/100` or `88%`. Parse within declared ranges; unexpected formats remain null and are counted as invalid. Runtime accepts positive whole minutes (with optional `min` suffix), not guessed durations.
- Treat comma-separated genres as non-exclusive tags; remove repeated tags within the same film only (case-insensitive), and count those events.
- Reconcile records, total membership flags, per-platform counts, flag patterns, multi-platform counts and source missingness against Phase 01 before writing outputs.
- Generate output SHA-256 values and do not overwrite an existing output directory.

## Explicit analytical denominators

- **Catalogue share:** distinct film records in the defined historical source or platform subset. Specify which.
- **Cross-platform overlap:** distinct source IDs in each platform-set intersection; avoid summing memberships as unique films.
- **Genre counts:** distinct film/genre assignments; total genre tags can exceed distinct movies.
- **IMDb, Rotten Tomatoes, runtime:** observed valid values only, with denominators shown and missingness assessed. Rating availability may differ by platform.
- **Release year:** film release, **not** platform joining date or catalogue evolution.

## Phase 02 release gate

Review `preparation_qa.json` for parse errors and source reconciliation; spot-check samples of cleaned numeric columns; confirm the outputs are Git-ignored. Only then proceed to descriptive analysis. Preserve author credit in later README and portfolio materials, and verify reuse/attribution terms before publication.
