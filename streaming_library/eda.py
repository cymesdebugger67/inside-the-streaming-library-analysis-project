"""Auditable descriptive analysis of historical platform movie memberships."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

PLATFORMS = ("Netflix", "Hulu", "Prime Video", "Disney+")
INPUTS = ("movies_clean.csv", "platform_memberships.csv", "movie_genres.csv")
FEATURE_FIELDS = (
    "source_id", "release_decade", "release_era", "runtime_band", "genre_count",
    "platform_count", "has_multiple_platforms", "rating_coverage", "imdb_rating",
    "rotten_tomatoes_percent", "runtime_minutes",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_table(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Required columns absent from {path.name}: {sorted(required)}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"Malformed rows in {path.name}")
    return rows


def parse_float(value: str, minimum: float, maximum: float) -> float | None:
    if value == "":
        return None
    x = float(value)
    if not math.isfinite(x) or not minimum <= x <= maximum:
        raise ValueError(f"Unexpected prepared numeric value: {value}")
    return x


def era(year: int) -> str:
    if year < 1950:
        return "pre_1950"
    if year < 1980:
        return "1950_1979"
    if year < 2000:
        return "1980_1999"
    if year < 2010:
        return "2000_2009"
    return "2010_plus"


def runtime_band(value: float | None) -> str:
    if value is None:
        return "missing_invalid"
    if value < 60:
        return "under_60"
    if value < 90:
        return "60_89"
    if value < 120:
        return "90_119"
    if value < 150:
        return "120_149"
    return "150_plus"


def fmt(x: float | None) -> str:
    return "" if x is None else f"{x:.6f}"


def quantile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    low = math.floor(pos)
    high = math.ceil(pos)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def make_outputs(movies, memberships, genres, qa):
    by_id = {}
    for movie in movies:
        mid = movie["source_id"]
        if not mid or mid in by_id:
            raise ValueError("Blank or duplicate movie source_id")
        by_id[mid] = movie
    if len(by_id) != qa["movie_rows"]:
        raise ValueError("Phase 02 movie row count mismatch")

    by_platform = {p: set() for p in PLATFORMS}
    membership_pairs = set()
    for item in memberships:
        pair = (item["source_id"], item["platform"])
        if pair[0] not in by_id or pair[1] not in by_platform or pair in membership_pairs:
            raise ValueError("Orphan, unknown platform, or duplicate membership")
        membership_pairs.add(pair)
        by_platform[pair[1]].add(pair[0])
    if len(membership_pairs) != qa["platform_membership_rows"]:
        raise ValueError("Phase 02 membership total mismatch")
    for p in PLATFORMS:
        if len(by_platform[p]) != qa["platform_counts"][p]:
            raise ValueError(f"Membership count mismatch for {p}")

    by_genre = defaultdict(set)
    genre_pairs = set()
    for item in genres:
        pair = (item["source_id"], item["genre"])
        if pair[0] not in by_id or not pair[1] or pair in genre_pairs:
            raise ValueError("Orphan, empty genre or duplicate genre assignment")
        genre_pairs.add(pair)
        by_genre[pair[0]].add(pair[1])
    if len(genre_pairs) != qa["genre_assignment_rows"]:
        raise ValueError("Phase 02 genre total mismatch")

    membership_count = Counter(mid for mid, _ in membership_pairs)
    if set(membership_count) != set(by_id):
        raise ValueError("Movie without platform membership")
    if sum(c > 1 for c in membership_count.values()) != qa["multi_platform_movies"]:
        raise ValueError("Phase 02 multi-platform count mismatch")

    features = []
    values = {}
    for mid, movie in by_id.items():
        year = int(movie["release_year"])
        if not 1880 <= year <= 2026:
            raise ValueError("Unexpected release year")
        imdb = parse_float(movie["imdb_rating"], 0, 10)
        rt = parse_float(movie["rotten_tomatoes_percent"], 0, 100)
        runtime = parse_float(movie["runtime_minutes"], 1, 1000)
        count = membership_count[mid]
        if int(movie["platform_count"]) != count or int(movie["has_multiple_platforms"]) != int(count > 1):
            raise ValueError("Prepared movie membership columns disagree with membership table")
        for column, v in (("has_imdb_rating", imdb), ("has_rotten_tomatoes_rating", rt), ("has_runtime", runtime)):
            if int(movie[column]) != int(v is not None):
                raise ValueError(f"Prepared validity indicator disagrees: {column}")
        rating_coverage = "both" if imdb is not None and rt is not None else "imdb_only" if imdb is not None else "rt_only" if rt is not None else "neither"
        feature = dict(source_id=mid, release_decade=(year // 10) * 10, release_era=era(year),
                       runtime_band=runtime_band(runtime), genre_count=len(by_genre[mid]),
                       platform_count=count, has_multiple_platforms=int(count > 1),
                       rating_coverage=rating_coverage, imdb_rating=fmt(imdb),
                       rotten_tomatoes_percent=fmt(rt), runtime_minutes=fmt(runtime))
        features.append(feature)
        values[mid] = dict(year=year, imdb=imdb, rt=rt, runtime=runtime, genre_count=len(by_genre[mid]))

    platform_summary = []
    for p in PLATFORMS:
        ids = by_platform[p]
        dates = [values[mid]["year"] for mid in ids]
        runtimes = [values[mid]["runtime"] for mid in ids if values[mid]["runtime"] is not None]
        imdb = [values[mid]["imdb"] for mid in ids if values[mid]["imdb"] is not None]
        rt = [values[mid]["rt"] for mid in ids if values[mid]["rt"] is not None]
        platform_summary.append(dict(platform=p, movie_count=len(ids), source_share=fmt(100 * len(ids)/len(movies)),
            release_year_median=fmt(quantile([float(y) for y in dates], .5)),
            runtime_median=fmt(quantile(runtimes, .5)), runtime_n=len(runtimes),
            imdb_mean=fmt(statistics.mean(imdb) if imdb else None), imdb_n=len(imdb),
            imdb_coverage_pct=fmt(100 * len(imdb)/len(ids) if ids else None),
            rt_mean=fmt(statistics.mean(rt) if rt else None), rt_n=len(rt),
            rt_coverage_pct=fmt(100 * len(rt)/len(ids) if ids else None)))

    overlap = []
    for p, q in combinations(PLATFORMS, 2):
        intersection = len(by_platform[p] & by_platform[q])
        union = len(by_platform[p] | by_platform[q])
        overlap.append(dict(platform_a=p, platform_b=q, shared_movies=intersection, union_movies=union,
            jaccard_pct=fmt(100*intersection/union if union else None),
            share_of_a_pct=fmt(100*intersection/len(by_platform[p]) if by_platform[p] else None),
            share_of_b_pct=fmt(100*intersection/len(by_platform[q]) if by_platform[q] else None)))

    genre_platform = []
    for p in PLATFORMS:
        ids = by_platform[p]
        counts = Counter(genre for mid in ids for genre in by_genre[mid])
        for genre, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            genre_platform.append(dict(platform=p, genre=genre, movies=count,
                percent_of_platform_movies=fmt(100*count/len(ids) if ids else None)))

    decade_platform = []
    for p in PLATFORMS:
        counts = Counter((values[mid]["year"] // 10)*10 for mid in by_platform[p])
        for decade, count in sorted(counts.items()):
            decade_platform.append(dict(platform=p, release_decade=decade, movies=count,
                percent_of_platform_movies=fmt(100*count/len(by_platform[p]) if by_platform[p] else None)))

    rating_coverage = []
    for p in PLATFORMS:
        ids = by_platform[p]
        for field in ("imdb", "rt", "runtime"):
            valid = sum(values[mid][field] is not None for mid in ids)
            rating_coverage.append(dict(platform=p, field=field, valid_n=valid, missing_invalid_n=len(ids)-valid,
                valid_pct=fmt(100*valid/len(ids) if ids else None)))

    runtime_distribution = []
    order = ("under_60", "60_89", "90_119", "120_149", "150_plus", "missing_invalid")
    band_map = {feature["source_id"]: feature["runtime_band"] for feature in features}
    for p in PLATFORMS:
        counts = Counter(band_map[mid] for mid in by_platform[p])
        for band in order:
            runtime_distribution.append(dict(platform=p, runtime_band=band, movies=counts[band],
                percent_of_platform_movies=fmt(100*counts[band]/len(by_platform[p]) if by_platform[p] else None)))

    if sum(int(r["movies"]) for r in decade_platform) != len(memberships):
        raise ValueError("Decade rows do not reconcile")
    if sum(int(r["movies"]) for r in runtime_distribution) != len(memberships):
        raise ValueError("Runtime bands do not reconcile")
    if sum(int(r["movies"]) for r in genre_platform) != sum(len(by_genre[mid]) for p in PLATFORMS for mid in by_platform[p]):
        raise ValueError("Genre-platform counts do not reconcile")
    return dict(movie_features=features, platform_summary=platform_summary, overlap=overlap,
                genre_platform=genre_platform, decade_platform=decade_platform,
                rating_coverage=rating_coverage, runtime_distribution=runtime_distribution)


def write_table(path: Path, rows: list[dict], fields: tuple[str, ...]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def analyze(prepared_dir: Path, destination: Path, *, figures: bool = True) -> dict:
    if destination.exists():
        raise ValueError(f"Refusing to overwrite existing EDA output: {destination}")
    qa_path = prepared_dir / "preparation_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if qa.get("status") != "prepared_with_historical_source_limitations":
        raise ValueError("Unexpected Phase 02 status")
    if set(qa.get("output_sha256", {})) != set(INPUTS):
        raise ValueError("Phase 02 hash contract incomplete")
    for filename in INPUTS:
        if sha256(prepared_dir / filename) != qa["output_sha256"][filename]:
            raise ValueError(f"Prepared input SHA256 mismatch: {filename}")
    movies = load_table(prepared_dir / INPUTS[0], set(("source_id", "release_year", "platform_count", "has_multiple_platforms", "imdb_rating", "rotten_tomatoes_percent", "runtime_minutes", "has_imdb_rating", "has_rotten_tomatoes_rating", "has_runtime")))
    memberships = load_table(prepared_dir / INPUTS[1], {"source_id", "platform"})
    genres = load_table(prepared_dir / INPUTS[2], {"source_id", "genre"})
    outputs = make_outputs(movies, memberships, genres, qa)
    fields = {
        "movie_features": FEATURE_FIELDS,
        "platform_summary": tuple(outputs["platform_summary"][0]),
        "overlap": tuple(outputs["overlap"][0]),
        "genre_platform": tuple(outputs["genre_platform"][0]),
        "decade_platform": tuple(outputs["decade_platform"][0]),
        "rating_coverage": tuple(outputs["rating_coverage"][0]),
        "runtime_distribution": tuple(outputs["runtime_distribution"][0]),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="_phase03_stage_", dir=destination.parent))
    try:
        for name, rows in outputs.items():
            write_table(staging / f"{name}.csv", rows, fields[name])
        if figures:
            from streaming_library.visualizations import generate_figures
            generate_figures(outputs, staging / "figures")
        files = sorted(p for p in staging.rglob("*") if p.is_file())
        report = dict(status="eda_complete_pending_interpretation", generated_at_utc=datetime.now(timezone.utc).isoformat(),
            scope="historical movie snapshot; release years are not platform change dates",
            input_qa_sha256=sha256(qa_path), input_hashes={name: qa["output_sha256"][name] for name in INPUTS},
            records=len(movies), platform_memberships=len(memberships), genre_assignments=len(genres),
            table_rows={name: len(rows) for name, rows in outputs.items()},
            output_hashes={str(p.relative_to(staging)).replace("\\", "/"): sha256(p) for p in files},
            limitations=["Historical snapshot date unverified", "Platform memberships and genres are non-exclusive",
                         "Observed ratings are subject to missingness bias", "No causal, current-availability, or time-series claims",
                         "Descriptive features are not trained model predictors"])
        (staging / "eda_qa.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("outputs/phase02_preparation"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/phase03_eda"))
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    qa = analyze(args.input_dir, args.output_dir, figures=not args.no_figures)
    print("PASS - Phase 03 historical descriptive analysis")
    print(f"Movies: {qa['records']:,}; memberships: {qa['platform_memberships']:,}; genre assignments: {qa['genre_assignments']:,}")
    print(f"Tables: {len(qa['table_rows'])}; output files: {len(qa['output_hashes'])}")
    print(f"Outputs: {args.output_dir}")
    print("No current availability, viewing behavior, time-series trends, or causal claims.")


if __name__ == "__main__":
    main()
