# Research Design — The Catalogue Differentiation Problem

**Project owner:** Cyril James Lunzaga

## Core question

Does a larger historical streaming movie catalogue yield proportionally broader choices, or mainly additional overlap and genre concentration?

## Units of analysis

A movie title-year key is the initial candidate identity, not a guaranteed global film identifier. Duplicate titles, alternate cuts and conflicting rows will be audited before choosing reconciliation rules. Historical platform flags are membership indicators, not observed viewing.

## Intended analyses

1. **Coverage and overlap:** Four-platform binary incidence matrix; intersections, unions and Jaccard similarity. Check computational equivalence between set operations and the binary matrix.
2. **Marginal catalogue contribution:** Exhaustively enumerate all 16 platform subsets, measure unique title coverage, calculate marginal gains and exact Shapley allocations. With only four platforms, exact enumeration is more transparent than approximating contributions using machine learning.
3. **Genre variety:** Split multi-label genre strings; use an explicit fractional-assignment denominator to compute Shannon entropy, effective genre count and concentration. Report a sensitivity calculation using an alternative genre allocation rule.
4. **Fair platform comparison:** Equal-size title resampling and calendar or stratified matching where feasible; do not equate raw catalogue size with variety.
5. **Uncertainty:** Bootstrap at the title level while preserving overlapping membership vectors. State that intervals describe source-snapshot sampling sensitivity, not a random sample of all platforms or all dates.
6. **Predictive model gate:** Optionally benchmark a regularized multilabel classifier only if reliable title-level labels and held-out group splits make model evaluation meaningful. Explicitly compare against label-prevalence baselines and avoid treating membership prediction as demand or personalized recommendation.

## Caveats before analysis

- Validate raw header and source-record count instead of assuming 16,744.
- Resolve or transparently flag duplicate title-year identities.
- Audit genre and score missingness, including by platform.
- Never treat missing scores as zero or compare only complete cases without a selection-bias warning.
- Do not attempt any causal claims.

## Portfolio differentiator

Exact Shapley decomposition provides a principled explanation of catalogue contribution across overlapping platform sets. The project is an analytical study, not a large deployed application. A notebook is a mandatory narrative companion to modular code and tests.

## Execution plan

Source audit -> cleaning/identity resolution -> exact matrix analysis -> genre diversity and sensitivity -> optional justified ML -> notebook and figures -> final Git/security review.
