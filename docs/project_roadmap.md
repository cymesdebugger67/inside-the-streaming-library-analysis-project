# Inside the Streaming Library — Project Roadmap

**Project owner:** Cyril James Lunzaga

## Research direction

Understand historical streaming movie catalogue composition, overlap, marginal coverage, genre diversity, and metadata completeness. Preserve the unverified historical snapshot-date limitation and distinguish descriptive source-level comparisons from external inference.

## Progress as of 2026-11-17

| Milestone | Scope | State |
|---|---|---|
| 00 | Repository and Git baseline | Local baseline verified; release not finalized |
| 01 | Acquisition, source fingerprint and provenance | Completed; independently reviewed |
| 02 | Three-grain preparation, parsing and data QA | Completed; independently reviewed |
| 03 | Descriptive feature engineering, EDA and five figures | Completed; reviewed, final visual polish pending |
| 04 | Directional overlap, genre diversity and stratified comparisons | Completed; reviewed, final visual polish pending |
| 05 | Country/language quality and feature extraction, advanced analyses | Planned |
| 06 | Research notebook, interactive exploration and report | Planned |
| 07 | Full rerun, tests, security, licensing and controlled Git publication | Pending |

The 38-test suite passed during the Phase 04 local execution and separately from the uploaded source review. This is not yet a final code, visualization or publication sign-off.

## Non-negotiable research controls

- One row per source ID for movies, distinct platform-membership and genre-assignment tables
- Explicit denominators for overlapping platforms and multi-label tags
- Missing rating and runtime observations are not imputed or interpreted as zero
- Release year is not the platform-listing or catalogue-entry date
- No statements about present-day availability, viewing behavior, subscriptions, causal effects or market share
- Statistical comparisons and feature selection only when there is a defensible question, sampling caveat and evaluation design
- Preserve original input fingerprints and stage-level output hashes
- Public authorship credits Cyril James Lunzaga

## Next checkpoints

1. Repair the inherited README, stale Netflix-specific entry point, dependency specification, source field count and starter notebook.
2. Review the repository diff and ensure raw data, caches and generated outputs remain Git-ignored.
3. Create a controlled milestone commit **only after** these repairs pass review; separately decide when to push.
4. Design Phase 05 based on documented country/language tokenization and a specific analytic question, rather than on folder count.
5. Consolidate reviewed visuals, analytical findings, notebook, data dictionary and end-to-end reproducibility instructions before final publication.
