from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS = ('Netflix', 'Hulu', 'Prime Video', 'Disney+')
STAGES = (
    ('phase02_preparation', 'preparation_qa.json', 'output_sha256'),
    ('phase03_eda', 'eda_qa.json', 'output_hashes'),
    ('phase04_comparative', 'comparative_qa.json', 'output_hashes'),
    ('phase05_metadata_reviewed', 'metadata_qa.json', 'output_hashes'),
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def csv_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f'Invalid schema: {path}')
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f'Malformed CSV: {path}')
    return rows


def verify_stages(root: Path, phase05: str = 'phase05_metadata_reviewed') -> dict:
    manifests = {}
    for directory, filename, hash_field in STAGES:
        if directory == 'phase05_metadata_reviewed':
            directory = phase05
        folder = root / 'outputs' / directory
        manifest_path = folder / filename
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        files = manifest[hash_field]
        if not isinstance(files, dict) or not files:
            raise ValueError(f'Invalid output manifest: {manifest_path}')
        for name, expected in files.items():
            target = (folder / name).resolve()
            if not target.is_relative_to(folder.resolve()):
                raise ValueError(f'Invalid relative path in manifest: {name}')
            if not target.is_file() or sha256(target) != expected:
                raise ValueError(f'Output fingerprint failed: {target}')
        manifests[directory] = manifest
    p = manifests['phase02_preparation']
    e = manifests['phase03_eda']
    c = manifests['phase04_comparative']
    m = manifests[phase05]
    baseline = (p['movie_rows'], p['platform_membership_rows'], p['genre_assignment_rows'])
    if baseline != (16744, 17381, 39098):
        raise ValueError('Unexpected source population')
    if baseline != (e['records'], e['platform_memberships'], e['genre_assignments']):
        raise ValueError('Phase 03 population mismatch')
    if baseline != (m['counts']['movies'], m['counts']['memberships'], m['counts']['genres']):
        raise ValueError('Phase 05 population mismatch')
    if c['status'] != 'comparative_outputs_pending_review':
        raise ValueError('Unexpected comparative stage status')
    return manifests


def build_index(movies, memberships, genres, assignments):
    by_id = {}
    for r in movies:
        mid = r['source_id']
        if not mid or mid in by_id:
            raise ValueError('Duplicate or blank movie ID')
        by_id[mid] = r
    platforms = defaultdict(set)
    genres_by_id = defaultdict(set)
    metadata = {dim: {mid: set() for mid in by_id} for dim in ('country', 'language')}
    membership_pairs = set()
    for r in memberships:
        mid, platform = r['source_id'], r['platform']
        if mid not in by_id or platform not in PLATFORMS or (mid, platform) in membership_pairs:
            raise ValueError('Invalid platform membership')
        membership_pairs.add((mid, platform))
        platforms[mid].add(platform)
    if set(platforms) != set(by_id):
        raise ValueError('Movie missing platform')
    for mid, r in by_id.items():
        if int(r['platform_count']) != len(platforms[mid]):
            raise ValueError('Incorrect movie membership count')
    seen = set()
    for r in genres:
        pair = (r['source_id'], r['genre'])
        if pair[0] not in by_id or not pair[1] or pair in seen:
            raise ValueError('Invalid genre assignment')
        seen.add(pair)
        genres_by_id[pair[0]].add(pair[1])
    seen.clear()
    for r in assignments:
        mid, dim, label = r['source_id'], r['dimension'], r['label']
        pair = (mid, dim, label)
        if mid not in by_id or dim not in ('country', 'language') or not label or pair in seen:
            raise ValueError('Invalid metadata assignment')
        if dim == 'language' and label.casefold() == 'none':
            raise ValueError('Sentinel None in named languages')
        seen.add(pair)
        metadata[dim][mid].add(label)
    return by_id, platforms, genres_by_id, metadata


def filter_ids(by_id, platforms, genres, metadata, *, platform='All', era='All', genre='All', metadata_dimension='All', metadata_label='All'):
    if platform != 'All' and platform not in PLATFORMS:
        raise ValueError('Unknown platform')
    if metadata_dimension not in ('All', 'country', 'language'):
        raise ValueError('Unknown metadata dimension')
    if metadata_label != 'All' and metadata_dimension == 'All':
        raise ValueError('Select metadata dimension for label filter')
    result = []
    for mid, movie in by_id.items():
        year = int(movie['release_year'])
        band = ('before_1950' if year < 1950 else '1950_1979' if year < 1980 else
                '1980_1999' if year < 2000 else '2000_2009' if year < 2010 else '2010_plus')
        if platform != 'All' and platform not in platforms[mid]:
            continue
        if era != 'All' and era != band:
            continue
        if genre != 'All' and genre not in genres[mid]:
            continue
        if metadata_label != 'All' and metadata_label not in metadata[metadata_dimension][mid]:
            continue
        result.append(mid)
    return result


def describe_selection(ids, by_id, platforms, genres):
    chosen = set(ids)
    if len(chosen) != len(ids) or not chosen.issubset(by_id):
        raise ValueError('Invalid selected IDs')
    platform_counts = {p: sum(p in platforms[mid] for mid in ids) for p in PLATFORMS}
    genre_counts = Counter(tag for mid in ids for tag in genres[mid])
    imdb = [float(by_id[mid]['imdb_rating']) for mid in ids if by_id[mid]['imdb_rating']]
    rt = [float(by_id[mid]['rotten_tomatoes_percent']) for mid in ids if by_id[mid]['rotten_tomatoes_percent']]
    runtime = [float(by_id[mid]['runtime_minutes']) for mid in ids if by_id[mid]['runtime_minutes']]
    return {
        'unique_movie_records': len(ids),
        'platform_memberships': sum(platform_counts.values()),
        'multi_platform_movies': sum(len(platforms[mid]) > 1 for mid in ids),
        'platform_movie_counts': platform_counts,
        'top_genres': [{'genre': g, 'movie_count': n} for g, n in genre_counts.most_common(15)],
        'imdb_observed_n': len(imdb), 'imdb_mean_observed': sum(imdb)/len(imdb) if imdb else None,
        'rt_observed_n': len(rt), 'rt_mean_observed': sum(rt)/len(rt) if rt else None,
        'runtime_observed_n': len(runtime), 'runtime_mean_observed': sum(runtime)/len(runtime) if runtime else None,
    }


def load_project(root: Path, phase05='phase05_metadata_reviewed'):
    manifests = verify_stages(root, phase05)
    prep = root/'outputs/phase02_preparation'
    meta = root/'outputs'/phase05
    movies = csv_rows(prep/'movies_clean.csv', {'source_id','release_year','platform_count','imdb_rating','rotten_tomatoes_percent','runtime_minutes'})
    members = csv_rows(prep/'platform_memberships.csv', {'source_id','platform'})
    genres = csv_rows(prep/'movie_genres.csv', {'source_id','genre'})
    assignments = csv_rows(meta/'metadata_assignments.csv', {'source_id','dimension','label'})
    p = manifests['phase02_preparation']
    m = manifests[phase05]
    if (len(movies), len(members), len(genres), len(assignments)) != (
        p['movie_rows'],p['platform_membership_rows'],p['genre_assignment_rows'],m['table_rows']['metadata_assignments']
    ):
        raise ValueError('Loaded row counts do not reconcile with manifests')
    return build_index(movies,members,genres,assignments)


def report(root: Path, destination: Path, phase05='phase05_metadata_reviewed'):
    if destination.exists():
        raise ValueError('Output folder exists; refusing overwrite')
    by_id, platforms, genres, metadata = load_project(root, phase05)
    selected = list(by_id)
    metrics = describe_selection(selected,by_id,platforms,genres)
    expected = {'Netflix':3560,'Hulu':903,'Prime Video':12354,'Disney+':564}
    if metrics['unique_movie_records'] != 16744 or metrics['platform_movie_counts'] != expected or metrics['multi_platform_movies'] != 627:
        raise ValueError('Integrated summary fails source reconciliation')
    manifest = {
        'status':'integrated_report_pending_review',
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Historical undated source movie membership snapshot; not current availability or viewer behavior',
        'phase05_output_directory':phase05,
        'metrics':metrics,
        'source_population':len(by_id),
        'known_country_movie_records':sum(bool(metadata['country'][mid]) for mid in by_id),
        'known_named_language_movie_records':sum(bool(metadata['language'][mid]) for mid in by_id),
    }
    content = [
        '# Integrated Historical Streaming Library Summary', '',
        '**Project owner:** Cyril James Lunzaga', '',
        'This report covers records in an undated historical four-platform source; it is not a contemporary market or viewing study.', '',
        f"- Unique source movie records: {metrics['unique_movie_records']:,}",
        f"- Platform memberships (overlapping): {metrics['platform_memberships']:,}",
        f"- Movies on multiple represented platforms: {metrics['multi_platform_movies']:,}",
        f"- Movies with a country label: {manifest['known_country_movie_records']:,}",
        f"- Movies with at least one named language: {manifest['known_named_language_movie_records']:,}", '',
        '## Platform membership totals', '',
        '| Platform | Movies |', '|---|---:|',
        *[f'| {p} | {metrics["platform_movie_counts"][p]:,} |' for p in PLATFORMS], '',
        '## Observed numeric metadata', '',
        '| Metric | Observed n | Mean among observed |', '|---|---:|---:|',
        *[f'| {label} | {metrics[key+"_observed_n"]:,} | {metrics[key+"_mean_observed"]:.2f} |' for label,key in [('IMDb','imdb'),('Rotten Tomatoes','rt'),('Runtime (minutes)','runtime')]], '',
        'Rating and runtime means condition on observed values only and are not comparable estimates of platform quality.', '',
        '## Interpretation boundaries', '',
        'Counts are source records and non-exclusive memberships. Genre, country, and language values are multi-label metadata. The literal `None` language sentinel is excluded from named-language calculations while the raw source is preserved. The source date is unknown; release year is not an entry date. No causal, trend, viewership, or market-share inference is justified.',
    ]
    destination.mkdir(parents=True, exist_ok=False)
    (destination/'integrated_summary.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (destination/'integrated_report.md').write_text('\n'.join(content)+'\n',encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path('.'))
    parser.add_argument('--phase05-dir', choices=['phase05_metadata_reviewed','phase05_metadata'], default='phase05_metadata_reviewed')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs/phase06_integrated'))
    args = parser.parse_args()
    result = report(args.project_root,args.output_dir,args.phase05_dir)
    print('PASS - Phase 06 integrated report generated')
    print('Movie records:',result['source_population'])
    print('Output:',args.output_dir)


if __name__ == '__main__':
    main()
