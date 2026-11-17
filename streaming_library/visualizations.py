"""Static publication-review figures for historical movie catalogues."""
from pathlib import Path


def generate_figures(tables: dict, destination: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Matplotlib is required for Phase 03 figures; install project requirements") from exc

    destination.mkdir(parents=True, exist_ok=False)

    def save(name, title, xlabel=None):
        ax = plt.gca()
        ax.set_title(title, loc="left", weight="bold", pad=14)
        if xlabel:
            ax.set_xlabel(xlabel)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        plt.savefig(destination / name, dpi=170, bbox_inches="tight")
        plt.close()

    summary = tables["platform_summary"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    names = [r["platform"] for r in summary]
    counts = [int(r["movie_count"]) for r in summary]
    ax.barh(list(reversed(names)), list(reversed(counts)))
    save("01_catalogue_sizes.png", "Historical movie memberships by platform", "Movies (non-exclusive memberships)")

    overlaps = tables["overlap"]
    pairs = [r["platform_a"] + " + " + r["platform_b"] for r in overlaps]
    pct = [float(r["jaccard_pct"]) for r in overlaps]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(list(reversed(pairs)), list(reversed(pct)))
    save("02_pairwise_overlap.png", "Pairwise Jaccard overlap of historical catalogues", "Shared / union movies (%)")

    decade_rows = tables["decade_platform"]
    decades = sorted(set(int(r["release_decade"]) for r in decade_rows))
    look = {(r["platform"], int(r["release_decade"])): float(r["percent_of_platform_movies"]) for r in decade_rows}
    fig, ax = plt.subplots(figsize=(10, 5))
    for p in names:
        ax.plot(decades, [look.get((p, d), 0) for d in decades], marker="o", markersize=3, label=p)
    ax.set_ylabel("Share of platform movies (%)")
    ax.legend(frameon=False)
    save("03_release_decade_composition.png", "Distribution of movie release decades by platform", "Release decade (not addition date)")
    # Add vertical-axis caption explicitly because the y-values are percentages.

    coverage = tables["rating_coverage"]
    fig, ax = plt.subplots(figsize=(10, 5))
    metrics = ("imdb", "rt", "runtime")
    width = .23
    centers = list(range(len(names)))
    lookup = {(r["platform"], r["field"]): float(r["valid_pct"]) for r in coverage}
    for index, metric in enumerate(metrics):
        ax.bar([x + (index-1)*width for x in centers], [lookup[(p, metric)] for p in names], width=width, label=metric)
    ax.set_xticks(centers, names)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Valid observations (%)")
    ax.legend(frameon=False)
    save("04_numeric_field_coverage.png", "Observed numeric field completeness by platform")

    genres = tables["genre_platform"]
    aggregate = {}
    for row in genres:
        aggregate[row["genre"]] = aggregate.get(row["genre"], 0) + int(row["movies"])
    top = [g for g, _ in sorted(aggregate.items(), key=lambda x: (-x[1], x[0]))[:12]]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for p in names:
        values = {r["genre"]: float(r["percent_of_platform_movies"]) for r in genres if r["platform"] == p}
        ax.plot(range(len(top)), [values.get(g, 0) for g in top], marker="o", label=p)
    ax.set_xticks(range(len(top)), top, rotation=45, ha="right")
    ax.set_ylabel("Share of platform movies (%) — non-exclusive genres")
    ax.legend(frameon=False)
    save("05_genre_prevalence.png", "Genre tag prevalence by platform")
