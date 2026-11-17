"""Prepare auditable historical movie catalogue tables from the Phase 01 source."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS = ("Netflix", "Hulu", "Prime Video", "Disney+")
REQUIRED = (
    "ID", "Title", "Year", "Age", "IMDb", "Rotten Tomatoes",
    *PLATFORMS, "Type", "Directors", "Genres", "Country", "Language", "Runtime",
)
MOVIE_COLUMNS = (
    "source_id", "title", "release_year", "normalized_title_year_key", "age_classification",
    "imdb_rating", "rotten_tomatoes_percent", "runtime_minutes", "directors", "genres_raw",
    "country_raw", "language_raw", "platform_count", "has_multiple_platforms",
    "has_imdb_rating", "has_rotten_tomatoes_rating", "has_runtime",
)
MEMBERSHIP_COLUMNS = ("source_id", "platform")
GENRE_COLUMNS = ("source_id", "genre")


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_identity(title: str, year: str) -> tuple[str, str]:
    return (" ".join(title.split()).casefold(), year.strip())


def parse_optional_number(raw: str, *, denominator: int | None = None, maximum: int = 100) -> tuple[str, str]:
    """Return (canonical numeric string, status) without imputing bad values."""
    value = raw.strip()
    if not value:
        return "", "missing"
    suffix = r"(?:\s*/\s*" + str(denominator) + r")?" if denominator else r"(?:\s*(?:%|/\s*100))?"
    match = re.fullmatch(r"(\d+(?:\.\d+)?)" + suffix, value)
    if not match:
        return "", "invalid"
    number = float(match.group(1))
    if not 0 <= number <= maximum:
        return "", "invalid"
    return format(number, "g"), "valid"


def parse_runtime(raw: str) -> tuple[str, str]:
    value = raw.strip()
    if not value:
        return "", "missing"
    match = re.fullmatch(r"(\d{1,4})(?:\s*(?:min|mins|minutes))?", value, re.IGNORECASE)
    if not match:
        return "", "invalid"
    minutes = int(match.group(1))
    if not 1 <= minutes <= 1000:
        return "", "invalid"
    return str(minutes), "valid"


def split_genres(raw: str) -> tuple[list[str], bool]:
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    seen: set[str] = set()
    unique: list[str] = []
    had_duplicate = False
    for token in tokens:
        key = token.casefold()
        if key in seen:
            had_duplicate = True
            continue
        seen.add(key)
        unique.append(token)
    return unique, had_duplicate


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare(source: Path, manifest_path: Path, destination: Path) -> dict:
    if destination.exists():
        raise ValueError(f"Output directory already exists; refuse to overwrite: {destination}")
    if not source.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("Phase 01 dataset or audit manifest is missing")

    audit = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hash = fingerprint(source)
    if audit.get("status") != "viable_with_historical_source_limitations":
        raise ValueError("Unexpected Phase 01 viability status")
    if source_hash != audit.get("source_sha256"):
        raise ValueError("Source hash differs from the Phase 01 manifest")

    qa = audit["qa"]
    movie_rows: list[dict[str, object]] = []
    membership_rows: list[dict[str, object]] = []
    genre_rows: list[dict[str, object]] = []
    missing = Counter()
    optional_status = {key: Counter() for key in ("IMDb", "Rotten Tomatoes", "Runtime")}
    patterns = Counter()
    platform_counts = Counter()
    duplicate_genre_rows = 0
    seen_ids: set[str] = set()
    seen_title_year: set[tuple[str, str]] = set()

    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)) or not set(REQUIRED).issubset(columns):
            raise ValueError(f"Missing or duplicate source columns: {sorted(set(REQUIRED) - set(columns))}")
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(field) is None for field in REQUIRED):
                raise ValueError(f"Malformed CSV row at source line {line_number}")
            for field in REQUIRED:
                if not row[field].strip():
                    missing[field] += 1
            identifier = row["ID"].strip()
            title = row["Title"].strip()
            raw_year = row["Year"].strip()
            if not identifier or not title or not re.fullmatch(r"\d{4}", raw_year):
                raise ValueError(f"Invalid required identity fields at line {line_number}")
            year = int(raw_year)
            if not 1880 <= year <= 2026:
                raise ValueError(f"Release year outside basic validation range at line {line_number}")
            if identifier in seen_ids:
                raise ValueError(f"Repeated source ID {identifier!r} at line {line_number}; review needed")
            identity = normalized_identity(title, raw_year)
            if identity in seen_title_year:
                raise ValueError(f"Repeated normalized title/year {identity!r}; review needed")
            seen_ids.add(identifier)
            seen_title_year.add(identity)
            if row["Type"].strip() != "0":
                raise ValueError(f"Unexpected non-movie Type at line {line_number}")

            flags = []
            for platform in PLATFORMS:
                flag = row[platform].strip()
                if flag not in {"0", "1"}:
                    raise ValueError(f"Non-binary platform flag at line {line_number}: {platform}")
                flags.append(flag)
                if flag == "1":
                    membership_rows.append({"source_id": identifier, "platform": platform})
                    platform_counts[platform] += 1
            if not any(flag == "1" for flag in flags):
                raise ValueError(f"Movie with no platform flags at line {line_number}")
            patterns["".join(flags)] += 1

            imdb, imdb_status = parse_optional_number(row["IMDb"], denominator=10, maximum=10)
            rt, rt_status = parse_optional_number(row["Rotten Tomatoes"], maximum=100)
            runtime, runtime_status = parse_runtime(row["Runtime"])
            optional_status["IMDb"][imdb_status] += 1
            optional_status["Rotten Tomatoes"][rt_status] += 1
            optional_status["Runtime"][runtime_status] += 1
            genres, had_duplicate = split_genres(row["Genres"])
            duplicate_genre_rows += int(had_duplicate)
            for genre in genres:
                genre_rows.append({"source_id": identifier, "genre": genre})

            movie_rows.append({
                "source_id": identifier,
                "title": title,
                "release_year": year,
                "normalized_title_year_key": f"{identity[0]}|{identity[1]}",
                "age_classification": row["Age"].strip(),
                "imdb_rating": imdb,
                "rotten_tomatoes_percent": rt,
                "runtime_minutes": runtime,
                "directors": row["Directors"].strip(),
                "genres_raw": row["Genres"].strip(),
                "country_raw": row["Country"].strip(),
                "language_raw": row["Language"].strip(),
                "platform_count": sum(flag == "1" for flag in flags),
                "has_multiple_platforms": int(sum(flag == "1" for flag in flags) > 1),
                "has_imdb_rating": int(imdb_status == "valid"),
                "has_rotten_tomatoes_rating": int(rt_status == "valid"),
                "has_runtime": int(runtime_status == "valid"),
            })

    n = len(movie_rows)
    if n != qa["source_rows"]:
        raise ValueError(f"Row-count mismatch with Phase 01: {n} != {qa['source_rows']}")
    if len(seen_title_year) != qa["unique_title_year_keys"] or qa["duplicate_title_year_groups"] != 0:
        raise ValueError("Identity-key reconciliation failed")
    if len(membership_rows) != qa["platform_flags_total"]:
        raise ValueError("Platform membership reconciliation failed")
    if {platform: platform_counts[platform] for platform in PLATFORMS} != qa["platform_counts"]:
        raise ValueError("Per-platform reconciliation failed")
    if dict(patterns) != qa["membership_patterns"]:
        raise ValueError("Membership-pattern reconciliation failed")
    if sum(row["has_multiple_platforms"] for row in movie_rows) != qa["multi_platform_source_rows"]:
        raise ValueError("Multi-platform reconciliation failed")
    for field, count in qa["missing_fields"].items():
        if missing[field] != count:
            raise ValueError(f"Missingness mismatch for {field}: {missing[field]} != {count}")

    report = {
        "status": "prepared_with_historical_source_limitations",
        "source_sha256": source_hash,
        "phase01_manifest_sha256": fingerprint(manifest_path),
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_rows": n,
        "movie_rows": len(movie_rows),
        "platform_membership_rows": len(membership_rows),
        "genre_assignment_rows": len(genre_rows),
        "platform_counts": {p: platform_counts[p] for p in PLATFORMS},
        "multi_platform_movies": sum(row["has_multiple_platforms"] for row in movie_rows),
        "source_missing_fields": dict(missing),
        "optional_parsing": {field: dict(status) for field, status in optional_status.items()},
        "rows_with_duplicate_genre_labels_deduplicated": duplicate_genre_rows,
        "denominator_rules": {
            "movie_count": "Rows in movies_clean.csv, one per unique source ID; historical source only",
            "platform_count": "Rows in platform_memberships.csv; one movie can appear on multiple platforms",
            "genre_count": "Distinct movie/genre assignments in movie_genres.csv; not mutually exclusive",
            "rating_count": "Only valid observed values, with explicit valid-value denominators",
        },
        "limitations": [
            "Snapshot date not independently verified; do not claim current streaming availability",
            "Release year does not indicate when a movie entered or left a platform",
            "Source identity is not independently matched to an external film registry",
            "Multi-label genres and platform memberships are non-exclusive",
            "Ratings can be missing non-randomly; no imputation applied",
            "Country and language retained as raw multi-value fields; not analyzed as exclusive labels",
        ],
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="_phase02_stage_", dir=destination.parent))
    try:
        _write_csv(staging / "movies_clean.csv", MOVIE_COLUMNS, movie_rows)
        _write_csv(staging / "platform_memberships.csv", MEMBERSHIP_COLUMNS, membership_rows)
        _write_csv(staging / "movie_genres.csv", GENRE_COLUMNS, genre_rows)
        (staging / "preparation_qa.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        for filename in ("movies_clean.csv", "platform_memberships.csv", "movie_genres.csv"):
            report.setdefault("output_sha256", {})[filename] = fingerprint(staging / filename)
        (staging / "preparation_qa.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/historical_streaming_movies.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("outputs/source_viability/source_audit.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/phase02_preparation"))
    args = parser.parse_args()
    try:
        report = prepare(args.source, args.manifest, args.output)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"STOP - Phase 02 preparation: {error}\n")
    print("PASS - Phase 02 table preparation and Phase 01 reconciliation")
    print(f"Movies: {report['movie_rows']:,}")
    print(f"Platform memberships: {report['platform_membership_rows']:,}")
    print(f"Genre assignments: {report['genre_assignment_rows']:,}")
    print(f"Outputs: {args.output}")
    print("Historical descriptive scope only; no current-availability or viewership claims.")


if __name__ == "__main__":
    main()
