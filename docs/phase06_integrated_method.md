# Phase 06 — Integrated analytics interface and narrative

**Project owner:** Cyril James Lunzaga

## Design

This phase consumes local prepared movie records, platform memberships, genre assignments, and the corrected Phase 05 named-language/country assignments. Every upstream file enumerated by the Phase 02–05 QA manifests must pass a SHA-256 comparison before interactive analysis or report creation. No stage data are changed or overwritten. Use `--phase05-dir phase05_metadata_reviewed` (default) for the corrected metadata model.

## Dashboard semantics

The filtering unit is a unique source movie ID. The platform, release era, genre and metadata label controls intersect at the movie-ID level. Selecting a platform finds movies with that membership; the cross-platform chart still displays all recorded platform memberships of those selected movies. This is intentional and avoids silently changing the denominator or treating platform flags as mutually exclusive. Release era is based on release year, not catalogue entry date. Genre and metadata labels are multi-value, and the literal language `None` is excluded from named language assignments.

The displayed means are *observed-only* descriptive summaries; the number of valid values is always displayed. The interface never produces a causal effect, current streaming availability, subscriber interest or market trend estimate. Empty filter selections are supported.

## Workflow

1. Generate the verified Phase 01–05 outputs using the earlier documented stage commands, preserving the corrected Phase 05 directory.
2. Install optional interface dependencies: `python -m pip install -r requirements-dashboard.txt`.
3. Run the read-only dashboard: `python -m streamlit run streaming_library/dashboard.py`.
4. Run `python -m streaming_library.integrated --output-dir outputs/phase06_integrated` for a locally generated narrative and machine-readable summary. This command refuses to overwrite an existing output directory.
5. Open `notebooks/integrated_research.ipynb` in VS Code and choose **Run All** using a compatible Jupyter Python kernel. The notebook reads the same verified files and does not write outputs.
6. Verify generated metrics, interactive filters, legends, screen layout and notebook execution locally. Capture screenshots of the dashboard only after visually reviewing it.

## Limits of evidence

The historical snapshot date is not established; source records are not a probability sample. Country labels are not verified country of production and named-language labels are not evidence of available audio tracks. Observed rating comparisons cannot be read as platform quality rankings. The dashboard is intended for local use; any public deployment requires separate privacy, data rights and hosting review.

## Publication gate

Independent review of the actual Phase 06 report, dashboard interaction, notebook execution, dependency installation, accessibility and source-data licensing remains pending. Report summaries are derived from outputs and should not be presented as external research findings without that review.
