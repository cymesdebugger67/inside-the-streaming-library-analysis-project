# Inside the Streaming Library

Historical streaming movie catalogue analysis | **Cyril James Lunzaga**

## Research purpose

How do the movie catalogues represented in one archived, undated four-platform dataset differ in recorded size, overlap, release-year composition, multi-label genres, observed ratings, runtime, and genre-tag diversity? The unit is a *source movie record*; platforms are overlapping membership flags, not independent viewing samples.

This study **does not** estimate current availability, subscriber behavior, audience preferences, market share, platform catalogue growth, or the causal effects of platform decisions.

## Verified source and scope

- Original attribution: Ruchi Bhatia, [Movies on Netflix, Prime Video, Hulu and Disney+](https://www.kaggle.com/datasets/ruchi798/movies-on-netflix-prime-video-hulu-and-disney).
- Exact retrieval mirror: [SalimAmarti/OTT_movies_Project](https://github.com/SalimAmarti/OTT_movies_Project/blob/master/MoviesOnStreamingPlatforms_updated.csv).
- CSV URL: `https://raw.githubusercontent.com/SalimAmarti/OTT_movies_Project/master/MoviesOnStreamingPlatforms_updated.csv`
- SHA-256: `c7a1b949495c35879b038c97f92bbe233d1b0b348719f3d4a8020927645c0c27`
- The file contains **16,744 movie records and 17 header fields**, one of which is an unnamed index-like field. The snapshot's precise observation date is not independently established.
- Four non-exclusive platform flags: Netflix (3,560), Hulu (903), Prime Video (12,354), Disney+ (564); 627 movies have multiple flags.
- Data are sourced from a third-party historical mirror; do not assume the contemporary Kaggle download has the same schema or contents. Attribution and redistribution terms require separate release review.

Raw CSVs and locally generated outputs are Git-ignored. This repository does not redistribute the input data.

## Methods and deliverables

| Stage | Implementation | Result |
|---|---|---|
| Source audit | `streaming_library/source_audit.py` | Schema, source fingerprint, missingness, historical viability manifest |
| Preparation | `streaming_library/preparation.py` | One-row-per-film table, platform-membership table, genre-assignment table, parsing and integrity checks |
| EDA | `streaming_library/eda.py`, `visualizations.py` | Release-era and runtime features, catalogue overlap, multi-label genre prevalence, descriptive tables and figures |
| Comparative analysis | `streaming_library/comparative.py`, `comparative_figures.py` | Directional overlap, fractional genre diversity, release-era metric coverage, missingness-aware comparisons |
| Quality assurance | `tests/` and stage QA manifests | 38 unit tests passed at the Phase 04 review; hashes and numeric reconciliation checked |

Methods, field definitions, and limitations are described in `docs/phase01_source_review.md`, `docs/phase02_preparation_method.md`, `docs/phase03_eda_method.md`, and `docs/phase04_comparative_method.md`. A narrative notebook is at `notebooks/inside_streaming_library.ipynb`; it currently presents a lightweight walkthrough, not the final report.

## Reproduce from a clean checkout

Run from the project root with Python and Matplotlib installed. Core calculation stages use the Python standard library. Matplotlib is needed for charts. Install dependencies into an appropriate environment with `python -m pip install -r requirements.txt` (availability of wheels depends on the Python version and platform).

Place the exact downloaded mirror at `data/raw/historical_streaming_movies.csv` and independently verify its SHA-256 before running. Then execute in order:

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
python -m streaming_library.source_audit
python -m streaming_library.preparation
python -m streaming_library.eda
python -m streaming_library.comparative
python analysis.py
```

**Important:** each stage creates local outputs; Phase 02–04 deliberately refuse to overwrite existing stage folders. Use a fresh workspace for a full rerun, or inspect and archive the old outputs before intentionally rebuilding a stage. The source audit also writes `docs/phase01_source_review.md`; check `git diff` after a fresh acquisition. `python analysis.py` checks QA manifests and generated-file hashes without changing anything.

Outputs are saved under `outputs/` and are ignored by Git. Do not treat successful unit tests alone as proof of scientific validity. Review every generated visualization, interpretation, provenance claim, and publication artifact separately.

## Selected observations from the reviewed historical snapshot

- 16,744 source records correspond to 17,381 platform memberships; memberships are **not** unique cross-platform film counts.
- 39,098 genre assignments were extracted; genre percentages are non-exclusive and must use stated denominators.
- Only 5,158 source records have Rotten Tomatoes metadata; missingness substantially limits score comparisons. Do not rank platforms by observed ratings without explicitly describing coverage.
- One source runtime (`Colorado`, 1940, source ID `13180`, value `1256`) violates the project's declared runtime validation range and is left missing in numeric calculations rather than silently corrected.

Additional numeric tables and charts are local outputs. They should be promoted to the public report only after their final presentation review and reproducibility check.

## Limitations and release status

The archive is not a probability sample of services, films, or dates; platform memberships overlap; titles are distinguished by source identities; genres may have multiple tags; source metadata and observed ratings have missingness; and release years do not indicate when titles joined streaming services. Statistical significance, current market conclusions, or causal claims are not justified from this source alone.

**Status:** Phases 01–04 have completed technical/analytical review. Final notebook, visualization consolidation, source-code/security review, licensing assessment, reproducibility verification, and controlled Git release remain pending.

**Project owner:** Cyril James Lunzaga
