# Inside the Streaming Library — Project Roadmap

**Project owner:** Cyril James Lunzaga

## Research controls

An undated, archived movie membership snapshot. Film release year is not catalogue-entry date. Platform flags overlap, genre and metadata labels can be multi-valued, and the source is not a probability sample. No causal, current-availability, viewer-demand, subscriber or market-share inference is justified. Retain raw checksum and stage fingerprints.

## Verified implementation checkpoints (17 November 2026)

| Milestone | Scope | State |
|---|---|---|
| 00 | Git baseline and source viability | Implemented and reviewed |
| 01 | Historical CSV schema, provenance, SHA-256 | Reviewed |
| 02 | Movie, platform membership, genre grains; QA | Reviewed |
| 03 | EDA and statistical descriptives | Reviewed |
| 04 | Overlap asymmetry, fractional Simpson, metric completeness | Reviewed |
| 05 | Country/language metadata and corrected `None` treatment | Reviewed; patch pushed to feature branch |
| 06 | Integrated notebook, Streamlit dashboard, report | 67-test checkpoint and user execution passed; feature branch commit `fe6d1bd` |
| 07A | Exact Shapley, Shannon weighting, equal-size resampling | 79 tests, output hash and independent table review passed; feature branch commit `fa5dfa7` |
| 07B | Comprehensive source-grounded report and documentation alignment | Implementation candidate; awaiting local execution and review |
| 07C | Clean-room rerun, dashboard/notebook signoff, licensing/security, Git release | Pending |

## Release gates

1. Run the full pipeline on the exact fingerprinted raw CSV and inspect hashes, outputs and the final generated report.
2. Verify the notebook's **Run All** after the Phase 07 extensions and interact with the dashboard's full-snapshot panel and prior filters.
3. Inspect README, data provenance and redistribution rights; the source must not be committed or included in public release bundles without authorization.
4. Review file inventory for secrets, caches, generated raw data and archival extracts; verify ownership credit **Cyril James Lunzaga**.
5. Stage and review intentional source/docs only; commit/push the feature branch, then merge to `main` only after release signoff.

## Design decisions

Exact Shapley accounts for overlapping source coverage; leave-one-out exclusivity remains distinct. Shannon effective diversity under fractional and full-tag weights and deterministic equal-size draws are implemented. Proposed title-bootstrap confidence intervals and predictive membership modelling are deliberately excluded from the final study because sampling and target validity do not support the intended external interpretations. Release-year matching remains a potential descriptive extension but not a mandatory claim; genre sensitivity is explicitly shown instead. Do not represent omitted methods as completed.
