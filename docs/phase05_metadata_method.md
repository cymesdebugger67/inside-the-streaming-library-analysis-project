# Phase 05 — Metadata and marginal contribution analysis

**Project owner:** Cyril James Lunzaga

## Research question and scope

What do recorded country and language labels, platform-exclusive membership, and completeness differences reveal about the **historical, undated** four-platform movie listing? These records are not current streaming-availability data. Country and language text are metadata fields, **not verified production nationality, streaming territory, or audio-track availability**.

## Data lineage

Inputs are the Phase 02 movie, membership, and genre tables. Their QA fingerprints are verified together with all Phase 03 and Phase 04 output hashes before Phase 05 starts. Existing outputs and raw inputs are not rewritten. Phase 05 writes a separate destination and refuses to overwrite one that exists.

## Grains and methods

- `metadata_assignments.csv`: one `source_id` × `dimension` × case-insensitive label; retains movie association, not a mutually exclusive breakdown
- `metadata_source_quality.csv`: one row per metadata dimension; source-level known, missing, duplicated-label, capitalization-variant and assignment counts
- `metadata_platform_coverage.csv`: one platform × dimension, with full membership denominator and known-value numerator
- `metadata_label_prevalence.csv`: one platform × dimension × label; prevalence divides by *all* movies on that platform; `known_base_pct` uses only movies with that metadata field
- `catalogue_contributions.csv`: one platform; counts movies unique to that platform **within these four listed platforms** and movies shared with at least one other. The leave-one-out loss in union size equals the exclusive count by definition.

Comma-delimited labels are trimmed, whitespace-collapsed, and casefolded for same-label deduplication. **Language-only exception:** a literal `None` token (case-insensitive) is excluded from *named-language* assignments and prevalence. For records containing `None` plus a named label (such as `None,French`), the named label remains included. For `None`-only records, named-language coverage is false; both cases are separately counted in `metadata_source_quality.csv` and `metadata_platform_coverage.csv`. The original strings remain intact in the upstream prepared movie table. `None` may denote no spoken language, an unspecified value, or another source convention; this policy does not equate it with a verified missing field or verified silent film. We deliberately do **not** guess country or language synonym equivalences, split compound geopolitical names, or interpret country names as market geography. Unexpected interior empty tokens fail the extraction, prompting inspection rather than silent deletion.

## Reporting constraints

Genre and country/language tags are multi-label. Platform catalogues also overlap. Their raw totals must not be interpreted as mutually exclusive movie populations. Metadata prevalence shows recorded label frequency, not underlying global film representation. No statistical significance, causal, temporal-growth, geographic-market-share or viewership inference is warranted. Labels are unverified strings and may contain inconsistent synonyms; these require review rather than automatic recoding.

## Quality gate

Run the full existing unit suite, Phase 05 analysis, source-level reconciliation and generated-figure review. Verify all declared output SHA-256 hashes and independently review the actual CSV and PNG files before approval or a feature-branch commit. Keep generated tables and figures under ignored `outputs/` until final publication decisions.

## Phase 05 metadata sentinel correction

The local source audit identified 20 movie records containing a literal language `None`, including mixed labels. The correction refines named-language metrics, retaining the raw source values and segregating ambiguous sentinel cases. Prior Phase 05 results must remain available for comparison; regenerate into a **new output directory**, without overwriting `outputs/phase05_metadata`. A changed metric is expected and should be independently reviewed before committing.
