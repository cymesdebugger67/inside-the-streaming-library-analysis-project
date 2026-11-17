"""Historical movie metadata extraction and marginal catalogue contributions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS = ('Netflix', 'Hulu', 'Prime Video', 'Disney+')
INPUTS = ('movies_clean.csv', 'platform_memberships.csv', 'movie_genres.csv')
DIMENSIONS = {'country': 'country_raw', 'language': 'language_raw'}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f'Missing columns in {path.name}')
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f'Malformed records in {path.name}')
    return rows


def extract_tokens(raw: str) -> tuple[list[str], bool]:
    """Conservative comma-token extraction; no unverified geopolitical synonym mapping."""
    if not raw.strip():
        return [], False
    tokens = []
    seen = set()
    duplicated = False
    for item in raw.split(','):
        label = ' '.join(item.split())
        if not label:
            raise ValueError('Empty token within nonempty multi-label field')
        key = label.casefold()
        if key in seen:
            duplicated = True
            continue
        seen.add(key)
        tokens.append(label)
    return tokens, duplicated


def fmt(number: float | None) -> str:
    return '' if number is None else f'{number:.6f}'


def build(movies: list[dict[str, str]], memberships: list[dict[str, str]], genres: list[dict[str, str]]):
    by_id = {}
    for row in movies:
        mid = row['source_id']
        if not mid or mid in by_id:
            raise ValueError('Blank or duplicate movie identifier')
        by_id[mid] = row
    if not by_id:
        raise ValueError('No movies')

    sets = {p: set() for p in PLATFORMS}
    pairs = set()
    for r in memberships:
        key = (r['source_id'], r['platform'])
        if key[0] not in by_id or key[1] not in sets or key in pairs:
            raise ValueError('Orphan, unknown, or duplicate platform membership')
        pairs.add(key)
        sets[key[1]].add(key[0])
    movie_membership = Counter(mid for mid, _ in pairs)
    if set(movie_membership) != set(by_id):
        raise ValueError('Movie without platform membership')
    if any(int(by_id[mid]['platform_count']) != n for mid, n in movie_membership.items()):
        raise ValueError('Platform count does not reconcile')

    genre_pairs = set()
    for r in genres:
        key = (r['source_id'], r['genre'])
        if key[0] not in by_id or not key[1] or key in genre_pairs:
            raise ValueError('Invalid genre assignment')
        genre_pairs.add(key)

    tokens_by_dim = {}
    canonical_by_dim = {}
    token_assignments = []
    token_quality = []
    for dim, field in DIMENSIONS.items():
        by_movie = {}
        sentinel_only = 0
        sentinel_mixed = 0
        sentinel_ids = set()
        duplicates = 0
        canonical = {}
        case_variant_count = 0
        for mid, movie in by_id.items():
            labels, duplicate = extract_tokens(movie[field])
            if dim == 'language':
                sentinel = [label for label in labels if label.casefold() == 'none']
                if sentinel:
                    sentinel_ids.add(mid)
                    named = [label for label in labels if label.casefold() != 'none']
                    sentinel_only += int(not named)
                    sentinel_mixed += int(bool(named))
                    labels = named
            duplicates += int(duplicate)
            normalized = []
            for label in labels:
                key = label.casefold()
                if key in canonical and canonical[key] != label:
                    case_variant_count += 1
                canonical.setdefault(key, label)
                normalized.append(key)
            by_movie[mid] = normalized
            for key in normalized:
                token_assignments.append(dict(source_id=mid, dimension=dim, label=canonical[key]))
        # Stable canonical casing across all records; never infer that synonyms are identical.
        for row in token_assignments:
            if row['dimension'] == dim:
                row['label'] = canonical[row['label'].casefold()]
        known = sum(bool(labels) for labels in by_movie.values())
        token_quality.append(dict(dimension=dim, movie_total=len(movies), known_movies=known,
                                  missing_movies=len(movies)-known, movie_with_duplicate_tokens=duplicates,
                                  case_variant_occurrences=case_variant_count,
                                  distinct_labels=len(canonical), assignments=sum(map(len,by_movie.values())),
                                  none_sentinel_only_movies=sentinel_only,
                                  none_sentinel_with_named_language_movies=sentinel_mixed))
        tokens_by_dim[dim] = by_movie
        canonical_by_dim[dim] = canonical
        if dim == "language":
            language_none_ids = sentinel_ids

    unique_labels = []
    metadata_coverage = []
    for p in PLATFORMS:
        ids = sets[p]
        for dim in DIMENSIONS:
            assignments = Counter(label for mid in ids for label in tokens_by_dim[dim][mid])
            known_n = sum(bool(tokens_by_dim[dim][mid]) for mid in ids)
            metadata_coverage.append(dict(platform=p,dimension=dim,all_n=len(ids),known_n=known_n,
                                          missing_n=len(ids)-known_n,known_pct=fmt(100*known_n/len(ids) if ids else None),
                                          assignments=sum(assignments.values()),distinct_labels=len(assignments),
                                          none_sentinel_movies=sum(mid in language_none_ids for mid in ids) if dim == "language" else 0))
            for label, n in sorted(assignments.items(), key=lambda entry:(-entry[1],entry[0])):
                unique_labels.append(dict(platform=p,dimension=dim,label=canonical_by_dim[dim][label],
                    movie_count=n,prevalence_pct=fmt(100*n/len(ids) if ids else None),
                    known_base_pct=fmt(100*n/known_n if known_n else None)))

    contributions = []
    for p in PLATFORMS:
        current = sets[p]
        other = set().union(*(sets[q] for q in PLATFORMS if q != p))
        exclusive = current - other
        shared = current & other
        leave_out = len(set().union(*(sets[q] for q in PLATFORMS if q != p)))
        contributions.append(dict(platform=p,movie_count=len(current),exclusive_movies=len(exclusive),
                                  shared_movies=len(shared),exclusive_pct=fmt(100*len(exclusive)/len(current) if current else None),
                                  union_without_platform=leave_out,
                                  marginal_union_contribution=len(exclusive)))
    all_ids = set().union(*sets.values())
    if all_ids != set(by_id):
        raise ValueError('Catalogue union does not reconcile')
    if sum(int(r['exclusive_movies']) for r in contributions) != sum(n==1 for n in movie_membership.values()):
        raise ValueError('Exclusive contributions do not reconcile')

    # Labels and metadata presence are observational metadata, not geographic or linguistic market indicators.
    for dim in DIMENSIONS:
        actual = sum(len(tokens_by_dim[dim][mid]) for mid in by_id)
        if actual != sum(int(r['assignments']) for r in token_quality if r['dimension']==dim):
            raise ValueError('Token assignment mismatch')
        if sum(int(r['known_movies'])+int(r['missing_movies']) for r in token_quality if r['dimension']==dim) != len(by_id):
            raise ValueError('Metadata quality denominator mismatch')
    for r in metadata_coverage:
        if int(r['known_n'])+int(r['missing_n']) != int(r['all_n']):
            raise ValueError('Coverage does not reconcile')

    return {'metadata_assignments': token_assignments, 'metadata_source_quality': token_quality,
            'metadata_platform_coverage': metadata_coverage, 'metadata_label_prevalence': unique_labels,
            'catalogue_contributions': contributions}


def save_table(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f'Cannot save empty table: {path.name}')
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(prepared: Path, phase03: Path, phase04: Path, destination: Path, *, figures=True):
    if destination.exists():
        raise ValueError('Refusing to overwrite existing Phase 05 results')
    pqa_path = prepared/'preparation_qa.json'
    eqa_path = phase03/'eda_qa.json'
    cqa_path = phase04/'comparative_qa.json'
    pqa = json.loads(pqa_path.read_text(encoding='utf-8'))
    eqa = json.loads(eqa_path.read_text(encoding='utf-8'))
    cqa = json.loads(cqa_path.read_text(encoding='utf-8'))
    if (pqa['status'] != 'prepared_with_historical_source_limitations' or
        eqa.get('records') != pqa['movie_rows'] or
        eqa.get('platform_memberships') != pqa['platform_membership_rows'] or
        eqa.get('genre_assignments') != pqa['genre_assignment_rows'] or
        cqa.get('status') != 'comparative_outputs_pending_review'):
        raise ValueError('Unapproved or inconsistent upstream QA')
    for directory, hashes in ((prepared,pqa['output_sha256']),
                              (phase03,eqa['output_hashes']),(phase04,cqa['output_hashes'])):
        for filename, expected in hashes.items():
            if digest(directory/filename) != expected:
                raise ValueError(f'Upstream fingerprint mismatch: {directory/filename}')
    movies = read_csv(prepared/INPUTS[0], {'source_id','platform_count','country_raw','language_raw'})
    memberships = read_csv(prepared/INPUTS[1], {'source_id','platform'})
    genres = read_csv(prepared/INPUTS[2], {'source_id','genre'})
    if (len(movies),len(memberships),len(genres)) != (pqa['movie_rows'],pqa['platform_membership_rows'],pqa['genre_assignment_rows']):
        raise ValueError('Upstream table counts do not reconcile')
    tables = build(movies,memberships,genres)
    destination.parent.mkdir(parents=True,exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='_phase05_stage_',dir=destination.parent))
    try:
        for name,rows in tables.items():
            save_table(staging/f'{name}.csv',rows)
        if figures:
            from streaming_library.metadata_figures import generate
            generate(tables,staging/'figures')
        files = sorted(p for p in staging.rglob('*') if p.is_file())
        qa = dict(status='metadata_analytics_pending_independent_review',
                  generated_at_utc=datetime.now(timezone.utc).isoformat(),
                  source_scope='Undated historical movie membership snapshot; descriptive metadata only',
                  counts={'movies':len(movies),'memberships':len(memberships),'genres':len(genres)},
                  table_rows={name:len(rows) for name,rows in tables.items()},
                  upstream_qa_sha256={'phase02':digest(pqa_path),'phase03':digest(eqa_path),'phase04':digest(cqa_path)},
                  output_hashes={p.relative_to(staging).as_posix():digest(p) for p in files},
                  limitations=['Metadata country/language strings are not verified national origins or available audio tracks',
                               'Literal language None excluded from named-language labels and flagged separately; not assumed to mean missing or silent',
                               'Comma parsing preserves other labels; synonyms or ambiguous geopolitical categories are not merged',
                               'Platform catalogues overlap and cannot be added as independent movie counts',
                               'No causal, market-share, contemporary catalogue or viewership inference'])
        (staging/'metadata_qa.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf-8')
        staging.rename(destination)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return qa


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared-dir',type=Path,default=Path('outputs/phase02_preparation'))
    p.add_argument('--phase03-dir',type=Path,default=Path('outputs/phase03_eda'))
    p.add_argument('--phase04-dir',type=Path,default=Path('outputs/phase04_comparative'))
    p.add_argument('--output-dir',type=Path,default=Path('outputs/phase05_metadata'))
    p.add_argument('--no-figures',action='store_true')
    args = p.parse_args()
    qa = run(args.prepared_dir,args.phase03_dir,args.phase04_dir,args.output_dir,figures=not args.no_figures)
    print('PASS - Phase 05 metadata and contribution analysis')
    print('Tables:',qa['table_rows'],'Output hashes:',len(qa['output_hashes']))
    print('Results:',args.output_dir)


if __name__=='__main__':
    main()
