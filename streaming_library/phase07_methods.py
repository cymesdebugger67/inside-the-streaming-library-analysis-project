from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from streaming_library.integrated import PLATFORMS, csv_rows, sha256, verify_stages


def read_inputs(root: Path):
    verify_stages(root)
    folder = root / 'outputs' / 'phase02_preparation'
    movies = csv_rows(folder / 'movies_clean.csv', {'source_id','platform_count'})
    memberships = csv_rows(folder / 'platform_memberships.csv', {'source_id','platform'})
    genres = csv_rows(folder / 'movie_genres.csv', {'source_id','genre'})
    return movies, memberships, genres


def incidence(movies, memberships, genres):
    ids = [r['source_id'] for r in movies]
    if len(ids) != len(set(ids)) or not ids or any(not mid for mid in ids):
        raise ValueError('Duplicate, missing, or empty movie IDs')
    allowed = set(ids)
    by_platform = {p: set() for p in PLATFORMS}
    by_id = defaultdict(set)
    seen = set()
    for row in memberships:
        mid,p = row['source_id'],row['platform']
        if mid not in allowed or p not in by_platform or (mid,p) in seen:
            raise ValueError('Invalid or duplicate membership')
        seen.add((mid,p))
        by_platform[p].add(mid)
        by_id[mid].add(p)
    if set(by_id) != allowed:
        raise ValueError('Movie without platform membership')
    if any(len(by_id[row['source_id']]) != int(row['platform_count']) for row in movies):
        raise ValueError('Platform count mismatch')
    by_genre = {mid: set() for mid in ids}
    seen = set()
    for row in genres:
        mid,g = row['source_id'],row['genre']
        if mid not in allowed or not g or (mid,g) in seen:
            raise ValueError('Invalid or duplicate genre assignment')
        seen.add((mid,g))
        by_genre[mid].add(g)
    return by_platform, by_id, by_genre


def exact_coalitions(platforms):
    names = tuple(PLATFORMS)
    coalition = {}
    rows = []
    for mask in range(1 << len(names)):
        chosen = tuple(names[j] for j in range(len(names)) if mask & (1 << j))
        members = set().union(*(platforms[p] for p in chosen)) if chosen else set()
        coalition[mask] = members
        rows.append({'subset_mask':mask,'subset': ' + '.join(chosen) if chosen else '(empty)',
                     'platform_count':len(chosen),'unique_movies':len(members)})
    return coalition, rows


def exact_shapley(platforms, by_id):
    coalition, subsets = exact_coalitions(platforms)
    n = len(PLATFORMS)
    factorial = math.factorial
    result = []
    for i,p in enumerate(PLATFORMS):
        bit = 1 << i
        phi = 0.0
        for mask in range(1 << n):
            if mask & bit: continue
            size = bin(mask).count("1")
            weight = factorial(size) * factorial(n-size-1) / factorial(n)
            phi += weight * (len(coalition[mask | bit]) - len(coalition[mask]))
        direct = sum(1/len(by_id[mid]) for mid in platforms[p])
        if not math.isclose(phi, direct, abs_tol=1e-7):
            raise ValueError('Coalition and member-based Shapley mismatch')
        exclusive = sum(len(by_id[mid]) == 1 for mid in platforms[p])
        result.append({'platform':p,'membership_movies':len(platforms[p]),
                       'exclusive_movies':exclusive,'shapley_allocated_movies':f'{phi:.9f}',
                       'shapley_share_pct':f'{100*phi/len(by_id):.6f}',
                       'shared_allocation_movies':f'{phi-exclusive:.9f}'})
    if not math.isclose(sum(float(r['shapley_allocated_movies']) for r in result), len(by_id), abs_tol=1e-6):
        raise ValueError('Shapley allocation does not reconcile to union')
    if len(coalition[(1 << n)-1]) != len(by_id):
        raise ValueError('Coalition union does not equal source population')
    return subsets, result


def diversity(ids, by_genre, method):
    if method not in ('fractional_movie', 'full_tag'):
        raise ValueError('Unknown genre allocation')
    weights = Counter()
    known = 0
    for mid in ids:
        tags = by_genre[mid]
        if not tags: continue
        known += 1
        for tag in tags:
            weights[tag] += (1/len(tags) if method == 'fractional_movie' else 1)
    total = sum(weights.values())
    probs = [w/total for w in weights.values()] if total else []
    shannon = -sum(p*math.log(p) for p in probs)
    effective = math.exp(shannon) if probs else None
    simpson = 1/sum(p*p for p in probs) if probs else None
    return {'known_genre_movies':known,'distinct_genres':len(weights),
            'assignment_weight':f'{total:.6f}',
            'shannon_entropy':f'{shannon:.9f}' if probs else '',
            'effective_genres_shannon':f'{effective:.9f}' if probs else '',
            'effective_genres_simpson':f'{simpson:.9f}' if probs else ''}


def genre_sensitivity(platforms, by_genre):
    result=[]
    for platform in PLATFORMS:
        ids=platforms[platform]
        for method in ('fractional_movie','full_tag'):
            result.append({'platform':platform,'allocation_method':method,
                           'membership_movies':len(ids),**diversity(ids,by_genre,method)})
    return result


def equal_size_sensitivity(platforms, by_genre, *, draws=200, seed=20261117):
    if draws < 1: raise ValueError('Draws must be positive')
    size=min(len(v) for v in platforms.values())
    if size < 1: raise ValueError('Empty platform catalogue')
    rng=random.Random(seed)
    result=[]
    for platform in PLATFORMS:
        population=sorted(platforms[platform])
        for draw in range(draws):
            sampled=rng.sample(population,size)
            d=diversity(sampled,by_genre,'fractional_movie')
            result.append({'platform':platform,'draw':draw+1,'sample_size':size,
                           'effective_genres_shannon':d['effective_genres_shannon'],
                           'effective_genres_simpson':d['effective_genres_simpson'],
                           'genre_known_n':d['known_genre_movies']})
    return result


def write_rows(path,rows):
    if not rows: raise ValueError('Empty analytical table')
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run(root: Path, output: Path, *, draws=200, seed=20261117):
    root=root.resolve();output=output.resolve()
    if output.exists(): raise ValueError('Refusing to overwrite Phase 07 outputs')
    movies,memberships,genres=read_inputs(root)
    platforms,by_id,by_genre=incidence(movies,memberships,genres)
    subsets,shapley=exact_shapley(platforms,by_id)
    genre_rows=genre_sensitivity(platforms,by_genre)
    sample_rows=equal_size_sensitivity(platforms,by_genre,draws=draws,seed=seed)
    total=len(movies)
    if len(memberships)!=sum(len(ids) for ids in platforms.values()):
        raise ValueError('Memberships do not reconcile')
    if len(genres)!=sum(map(len,by_genre.values())):
        raise ValueError('Genre assignments do not reconcile')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='_phase07_stage_',dir=output.parent))
    try:
        tables={'coalition_coverage':subsets,'shapley_attribution':shapley,
                'genre_entropy_sensitivity':genre_rows,'equal_size_genre_resampling':sample_rows}
        for name,rows in tables.items():write_rows(stage/f'{name}.csv',rows)
        summary={
            'status':'phase07_methods_pending_review',
            'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'source_population':total,
            'membership_count':len(memberships),
            'genre_assignment_count':len(genres),
            'coalitions':len(subsets),
            'shapley_sum':sum(float(r['shapley_allocated_movies']) for r in shapley),
            'shapley':{r['platform']:float(r['shapley_allocated_movies']) for r in shapley},
            'resampling':{'seed':seed,'draws_per_platform':draws,'sample_size':min(map(len,platforms.values())),
                          'purpose':'Within-archive, equal-size descriptive sensitivity only; not statistical inference'},
            'input_manifests':{
                name:sha256(root/'outputs'/name/manifest) for name,manifest in [
                    ('phase02_preparation','preparation_qa.json'),
                    ('phase03_eda','eda_qa.json'),
                    ('phase04_comparative','comparative_qa.json'),
                    ('phase05_metadata_reviewed','metadata_qa.json')]},
            'output_hashes':{p.name:sha256(p) for p in sorted(stage.glob('*.csv'))},
            'interpretation':'No current catalogue, probability-sample, uncertainty interval or causal claim'}
        (stage/'phase07_methods_qa.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        stage.rename(output)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path('outputs/phase07_methods'))
    parser.add_argument('--draws',type=int,default=200)
    parser.add_argument('--seed',type=int,default=20261117)
    args=parser.parse_args()
    summary=run(args.root,args.output,draws=args.draws,seed=args.seed)
    print('PASS - Phase 07 exact attribution and diversity sensitivity')
    print('Source records:',summary['source_population'])
    print('Coalitions:',summary['coalitions'])
    print('Shapley allocation sum:',summary['shapley_sum'])
    print('Output:',args.output)


if __name__=='__main__':main()
