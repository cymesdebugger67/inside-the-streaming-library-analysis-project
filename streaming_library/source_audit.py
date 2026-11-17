from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import csv
import json
import math
import re
import unicodedata

PLATFORMS = ("Netflix", "Hulu", "Prime Video", "Disney+")
REQUIRED_COLUMNS = (
    "ID", "Title", "Year", "Age", "IMDb", "Rotten Tomatoes",
    "Netflix", "Hulu", "Prime Video", "Disney+", "Type",
    "Directors", "Genres", "Country", "Language", "Runtime"
)
SOURCE_ORIGIN = "https://www.kaggle.com/datasets/ruchi798/movies-on-netflix-prime-video-hulu-and-disney"
SOURCE_MIRROR = "https://raw.githubusercontent.com/SalimAmarti/OTT_movies_Project/master/MoviesOnStreamingPlatforms_updated.csv"


def normalized_key(title, year):
    normalized = unicodedata.normalize("NFKC", title).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return (" ".join(normalized.split()), year.strip())


def file_fingerprint(path):
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_optional_numeric(text, lower, upper, suffix=""):
    value = text.strip()
    if not value:
        return None
    if suffix:
        if not value.endswith(suffix):
            return None
        value = value[:-len(suffix)]
    try:
        result = float(value)
    except ValueError:
        return None
    if not math.isfinite(result) or not lower <= result <= upper:
        return None
    return result


def audit_csv(path, min_rows=1000):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Source CSV not found: {path}")
    byte_count = path.stat().st_size
    if byte_count < 100:
        raise ValueError("Source CSV is unexpectedly small")

    platform_count = Counter({name: 0 for name in PLATFORMS})
    membership = Counter()
    missing = Counter()
    invalid_fields = Counter()
    genre_terms = Counter()
    duplicate_keys = Counter()
    identifiers = Counter()
    release_years = []
    age_groups = Counter()
    content_types = Counter()
    membership_total = 0
    multi_platform_titles = 0
    row_count = 0
    genre_observations = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields:
            raise ValueError("Missing CSV header")
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate CSV header columns")
        absent = sorted(set(REQUIRED_COLUMNS) - set(fields))
        if absent:
            raise ValueError("Historical 16-column data contract not satisfied; missing: " + ", ".join(absent))

        for row_count, row in enumerate(reader, start=1):
            if None in row:
                raise ValueError(f"Unexpected extra CSV fields at record {row_count}")
            if any(row[field] is None for field in REQUIRED_COLUMNS):
                raise ValueError(f"Missing structural fields at record {row_count}")
            for name in REQUIRED_COLUMNS:
                if not row[name].strip():
                    missing[name] += 1

            title = row["Title"].strip()
            year = row["Year"].strip()
            if not title:
                invalid_fields["empty_title"] += 1
            try:
                parsed_year = int(year)
                if parsed_year < 1888 or parsed_year > 2026:
                    invalid_fields["unreasonable_year"] += 1
                else:
                    release_years.append(parsed_year)
            except ValueError:
                invalid_fields["invalid_year"] += 1

            if title and year:
                duplicate_keys[normalized_key(title, year)] += 1
            identifier = row["ID"].strip()
            if identifier:
                identifiers[identifier] += 1

            flags = []
            for platform in PLATFORMS:
                flag = row[platform].strip()
                if flag not in ("0", "1"):
                    raise ValueError(f"Nonbinary {platform} flag at record {row_count}: {flag!r}")
                value = int(flag)
                platform_count[platform] += value
                flags.append(value)
            membership["".join(map(str, flags))] += 1
            membership_total += sum(flags)
            multi_platform_titles += sum(flags) > 1

            if row["IMDb"].strip() and parse_optional_numeric(row["IMDb"], 0, 10) is None:
                invalid_fields["imdb_format"] += 1
            if row["Rotten Tomatoes"].strip() and parse_optional_numeric(row["Rotten Tomatoes"], 0, 100, "%") is None:
                invalid_fields["rotten_tomatoes_format"] += 1
            if row["Runtime"].strip() and parse_optional_numeric(row["Runtime"], 0, 1000) is None:
                invalid_fields["runtime_format"] += 1
            content_types[row["Type"].strip()] += 1
            if row["Age"].strip():
                age_groups[row["Age"].strip()] += 1
            if row["Genres"].strip():
                parts = sorted(set(part.strip() for part in row["Genres"].split(",") if part.strip()))
                genre_observations += len(parts)
                genre_terms.update(parts)

    if row_count < min_rows:
        raise ValueError(f"Only {row_count} rows, below required {min_rows}")
    if invalid_fields["empty_title"] or invalid_fields["invalid_year"] or invalid_fields["unreasonable_year"]:
        raise ValueError(f"Essential title/year validation failed: {dict(invalid_fields)}")
    if sum(platform_count.values()) != membership_total:
        raise ValueError("Platform total reconciliation failed")
    if any(value != "0" for value in content_types):
        raise ValueError(f"Expected movies-only historical dataset, found Type values: {dict(content_types)}")
    if membership["0000"]:
        raise ValueError(f"Found {membership['0000']} titles on no named platform")

    row_stats = {
        "source_rows": row_count,
        "unique_title_year_keys": len(duplicate_keys),
        "duplicate_title_year_groups": sum(count > 1 for count in duplicate_keys.values()),
        "duplicate_title_year_excess_rows": sum(count - 1 for count in duplicate_keys.values()),
        "duplicate_id_groups": sum(count > 1 for count in identifiers.values()),
        "platform_flags_total": membership_total,
        "multi_platform_source_rows": multi_platform_titles,
        "platform_counts": dict(platform_count),
        "membership_patterns": dict(sorted(membership.items())),
        "release_year_min": min(release_years),
        "release_year_max": max(release_years),
        "missing_fields": {column: missing[column] for column in REQUIRED_COLUMNS},
        "invalid_optional_fields": dict(invalid_fields),
        "age_values": dict(age_groups.most_common(12)),
        "top_genre_tags": dict(genre_terms.most_common(20)),
        "genre_tag_assignments": genre_observations,
        "type_values": dict(content_types),
    }
    return {
        "status": "viable_with_historical_source_limitations",
        "study": "Inside the Streaming Library",
        "source_origin": SOURCE_ORIGIN,
        "source_retrieval_mirror": SOURCE_MIRROR,
        "snapshot_claim": "Historical archival catalogue; snapshot date not independently verified",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(path.as_posix()),
        "source_bytes": byte_count,
        "source_sha256": file_fingerprint(path),
        "source_fields": fields,
        "required_fields": list(REQUIRED_COLUMNS),
        "qa": row_stats,
        "methodology_gates": {
            "do_not_claim_current_availability": True,
            "do_not_infer_viewership_or_subscriptions": True,
            "deduplicate_before_catalogue_set_analysis": True,
            "treat_multi_label_genres_with_explicit_denominator": True,
            "avoid_rating_selection_bias": True,
        },
    }


def create_report(audit):
    quality = audit["qa"]
    platforms = "\n".join(f"| {name} | {value:,} |" for name, value in quality["platform_counts"].items())
    missing = "\n".join(f"| {name} | {value:,} |" for name, value in quality["missing_fields"].items())
    return "\n".join([
        "# Phase 01 — Streaming Source Review",
        "",
        "**Project owner:** Cyril James Lunzaga",
        "",
        "## Scope and provenance",
        "",
        "Historical archived movies-on-streaming-platforms dataset; no claims about present-day availability.",
        "",
        f"- Original publisher: {audit['source_origin']}",
        f"- Retrieval mirror: {audit['source_retrieval_mirror']}",
        f"- SHA-256: `{audit['source_sha256']}`",
        f"- File bytes: {audit['source_bytes']:,}",
        f"- Audited records: {quality['source_rows']:,}",
        f"- Unique normalized title/year keys: {quality['unique_title_year_keys']:,}",
        f"- Duplicate-key groups: {quality['duplicate_title_year_groups']:,}",
        f"- Duplicate-key excess rows: {quality['duplicate_title_year_excess_rows']:,}",
        f"- Rows with multiple platform flags: {quality['multi_platform_source_rows']:,}",
        "",
        "## Platform-flag coverage (source rows)",
        "",
        "| Platform | Positive flags |",
        "|---|---:|",
        platforms,
        "",
        "These counts are not de-duplicated title counts. They must not be interpreted as current platform library sizes.",
        "",
        "## Missingness by field",
        "",
        "| Field | Missing rows |",
        "|---|---:|",
        missing,
        "",
        "## Research controls",
        "",
        "- Verify duplicate title/year groups and conflicting flags before selecting title-level rules.",
        "- Do not sum multi-label genre tags as though each film belongs to one genre.",
        "- Rate-quality comparisons are secondary because rating missingness is selective.",
        "- Limit conclusions to this dataset's historical coverage; do not infer viewership, demand, or platform strategies.",
        "- Reconfirm data licensing and cite the original source and archival mirror before publication.",
        "",
        "## Decision",
        "",
        "Data are structurally viable for controlled analysis, subject to Phase 02 duplicate-resolution review.",
        "",
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/raw/historical_streaming_movies.csv")
    parser.add_argument("--output", default="outputs/source_viability/source_audit.json")
    parser.add_argument("--report", default="docs/phase01_source_review.md")
    args = parser.parse_args()
    audit = audit_csv(Path(args.csv))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(create_report(audit), encoding="utf-8")
    quality = audit["qa"]
    print("PASS - Historical streaming dataset structural audit")
    print(f"Rows: {quality['source_rows']:,}")
    print(f"Columns: {len(audit['source_fields'])}")
    print(f"SHA256: {audit['source_sha256']}")
    print(f"Unique title/year keys: {quality['unique_title_year_keys']:,}")
    print(f"Duplicate title/year groups: {quality['duplicate_title_year_groups']:,}")
    print(f"Multi-platform source rows: {quality['multi_platform_source_rows']:,}")
    print(f"Platform positive flags: {quality['platform_counts']}")
    print("NEXT - Independent Phase 01 source review; no full analysis or publication approved")


if __name__ == "__main__":
    main()
