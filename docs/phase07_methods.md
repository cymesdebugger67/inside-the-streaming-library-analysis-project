# Phase 07 — Exact Catalogue Attribution and Genre Sensitivity

**Project owner:** Cyril James Lunzaga

## Scope and estimands

The unit is a source movie record, not a verified global work ID or a contemporary listing. Platform memberships are non-exclusive. The source's observation date is unknown. These statistics describe this one archived four-platform dataset.

### Coalition coverage and exact Shapley contribution

For each of 16 subsets of the four platforms, the characteristic function is the number of unique source IDs in their union. The empty subset contributes zero. The Shapley attribution of a platform is the average increment to union coverage across all permutations of platform entry (equivalently, the factorial-weighted marginal increments across the 8 coalitions not containing that platform). This allocation divides each title equally among the represented platforms on which it appears: a film on k platforms contributes 1/k to each. Hence all platform allocations sum to 16,744 unique records. Exclusivity (the leave-one-out union difference) remains a **separate** measure and must not be described as Shapley attribution. Shapley allocation is an attribution convention, not evidence of causality or customer value.

### Genre diversity and allocation sensitivity

`fractional_movie` assigns total weight 1 to each genre-classified film, divided equally among that film's reported genre tags. `full_tag` assigns weight 1 to each tag, so multi-tagged films contribute more total weight. Within each platform and rule, normalized genre weights give Shannon entropy H = -sum(p log(p)), exp(H) effective Shannon genres, and 1/sum(p²) effective Simpson genres. Missing genre tags are excluded from both numerator and diversity denominator, and coverage is reported. **These are two differently defined compositions, not alternative estimates of one population parameter.** Existing Phase 04 Simpson figures remain unchanged.

### Equal-size catalogue sensitivity

For each platform, draw without replacement a simple random sample of exactly the smallest represented platform size, using a fixed local PRNG seed, separately per draw. Repeat 200 times by default; report effective Shannon and Simpson diversity for each draw. This addresses the descriptive dependence of observed genre variety on catalogue size, **not** whether platforms differ significantly: the archived source is neither a random sample of titles nor of dates; within-platform resampling retains dependence across platforms and is not a confidence interval. Avoid interpreting resampling ranges as external uncertainty bounds. Missing genre coverage changes across draws and is explicitly retained.

### Scope gate for originally proposed methods

No title-level bootstrap confidence intervals are included: sampling assumptions cannot justify uncertainty estimates about current service catalogues or time periods. No predictive model is built: the source contains platform flags but no validated usage/demand outcome, so membership prediction would not establish viewer preference. Release-year matching remains a candidate descriptive extension only if unequal-era composition materially affects the interpretation of equal-size genre comparisons. These decisions are documented, not silently treated as completed analyses.

## Run and audit

Run `python -m streaming_library.phase07_methods` after Phases 02–05 are prepared and hash-verified. It refuses to overwrite existing `outputs/phase07_methods/`, writes four CSV tables and `phase07_methods_qa.json`, and validates its input manifests using `integrated.verify_stages`. Run `python -m unittest discover -s tests -p "test_*.py" -q` for the full unit suite. Outputs are ignored by Git and remain pending analytical review until actual tables and plots are inspected.
