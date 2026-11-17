"""Historical catalogue comparison with multi-label and missingness safeguards."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

PLATFORMS = ('Netflix', 'Hulu', 'Prime Video', 'Disney+')
INPUTS = ('movies_clean.csv', 'platform_memberships.csv', 'movie_genres.csv')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def read_csv(path, required):
    with path.open(newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        if r.fieldnames is None or not set(required).issubset(r.fieldnames):
            raise ValueError(f'Columns missing in {path}')
        rows = list(r)
    if any(None in row or any(x is None for x in row.values()) for row in rows):
        raise ValueError(f'Malformed CSV row in {path}')
    return rows


def decimal(value, low, high):
    if not value:
        return None
    num = float(value)
    if not math.isfinite(num) or not low <= num <= high:
        raise ValueError(f'Invalid prepared numeric value {value}')
    return num


def era(y):
    if y < 1950: return 'before_1950'
    if y < 1980: return '1950_1979'
    if y < 2000: return '1980_1999'
    if y < 2010: return '2000_2009'
    return '2010_2020'


def fnum(x):
    return '' if x is None else f'{x:.6f}'


def build(movies, memberships, genres):
    by_id = {}
    for m in movies:
        mid = m['source_id']
        if not mid or mid in by_id:
            raise ValueError('Duplicate or blank source ID')
        by_id[mid] = m
    platforms = {p: set() for p in PLATFORMS}
    pairs = set()
    for row in memberships:
        mid, platform = row['source_id'], row['platform']
        if mid not in by_id or platform not in platforms or (mid, platform) in pairs:
            raise ValueError('Invalid platform membership')
        platforms[platform].add(mid)
        pairs.add((mid, platform))
    if {mid for mid, _ in pairs} != set(by_id):
        raise ValueError('Missing platform membership')
    by_genre = defaultdict(set)
    gpairs = set()
    for row in genres:
        mid, g = row['source_id'], row['genre'].strip()
        if mid not in by_id or not g or (mid,g) in gpairs:
            raise ValueError('Invalid genre assignment')
        gpairs.add((mid,g))
        by_genre[mid].add(g)
    features = {}
    for mid, m in by_id.items():
        year = int(m['release_year'])
        if not 1880 <= year <= 2020:
            raise ValueError('Unexpected release year outside snapshot range')
        features[mid] = {'era': era(year), 'imdb':decimal(m['imdb_rating'],0,10),
                         'rt':decimal(m['rotten_tomatoes_percent'],0,100),
                         'runtime':decimal(m['runtime_minutes'],1,1000)}
        count = sum(mid in ids for ids in platforms.values())
        if int(m['platform_count']) != count:
            raise ValueError('Prepared platform count disagrees')
    # Overlap: meaningful asymmetry under vastly unequal catalogue sizes.
    overlap = []
    for a,b in combinations(PLATFORMS,2):
        x,y=platforms[a],platforms[b]
        shared=len(x&y)
        overlap.append(dict(platform_a=a,platform_b=b,shared=shared, unique_a=len(x-y),unique_b=len(y-x),
                            share_a_pct=fnum(100*shared/len(x) if x else None),share_b_pct=fnum(100*shared/len(y) if y else None),
                            jaccard_pct=fnum(100*shared/len(x|y) if x|y else None)))
    # Count multi-label tags as full movies for prevalence; fractional counts only for diversity.
    diversity=[]
    genre_prevalence=[]
    for p in PLATFORMS:
        ids=platforms[p]
        assignments=Counter(g for mid in ids for g in by_genre[mid])
        fractional=Counter()
        classified=0
        for mid in ids:
            labels=by_genre[mid]
            if labels:
                classified += 1
                for g in labels:
                    fractional[g] += 1/len(labels)
        total=sum(fractional.values())
        probs=[v/total for v in fractional.values()] if total else []
        simpson=1-sum(x*x for x in probs) if probs else None
        effective=(1/sum(x*x for x in probs)) if probs else None
        diversity.append(dict(platform=p, movie_count=len(ids), genre_known_n=classified,
                              genre_missing_n=len(ids)-classified, distinct_genres=len(assignments),
                              assignment_count=sum(assignments.values()),fractional_diversity_simpson=fnum(simpson),
                              effective_genres_simpson=fnum(effective)))
        for g,count in sorted(assignments.items()):
            genre_prevalence.append(dict(platform=p,genre=g,movies=count,prevalence_pct=fnum(100*count/len(ids) if ids else None),
                                         fractional_movie_equivalents=fnum(fractional[g])))
    # No inferential hypothesis tests: full observed archived listing, provenance/sampling unknown.
    era_metrics=[]
    for p in PLATFORMS:
        for group in ('before_1950','1950_1979','1980_1999','2000_2009','2010_2020'):
            ids=[mid for mid in platforms[p] if features[mid]['era']==group]
            for field in ('imdb','rt','runtime'):
                vals=[features[mid][field] for mid in ids if features[mid][field] is not None]
                vals.sort()
                median=(vals[(len(vals)-1)//2]+vals[len(vals)//2])/2 if vals else None
                era_metrics.append(dict(platform=p,release_era=group,metric=field,all_n=len(ids),
                                        observed_n=len(vals),missing_n=len(ids)-len(vals),
                                        coverage_pct=fnum(100*len(vals)/len(ids) if ids else None),
                                        observed_mean=fnum(sum(vals)/len(vals) if vals else None),
                                        observed_median=fnum(median)))
    # Missingness is diagnostic, not random or a propensity model.
    completeness=[]
    for p in PLATFORMS:
        ids=platforms[p]
        for field in ('imdb','rt','runtime'):
            observed=sum(features[mid][field] is not None for mid in ids)
            completeness.append(dict(platform=p,metric=field,all_n=len(ids),observed_n=observed,
                                     missing_n=len(ids)-observed,observed_pct=fnum(100*observed/len(ids) if ids else None)))
    outputs={'overlap_asymmetry':overlap,'genre_diversity':diversity,
             'genre_prevalence':genre_prevalence,'era_metric_coverage':era_metrics,
             'platform_completeness':completeness}
    for p in PLATFORMS:
        for field in ('imdb','rt','runtime'):
            cohort=[r for r in era_metrics if r['platform']==p and r['metric']==field]
            overall=next(r for r in completeness if r['platform']==p and r['metric']==field)
            if sum(r['all_n'] for r in cohort)!=overall['all_n'] or sum(r['observed_n'] for r in cohort)!=overall['observed_n']:
                raise ValueError('Release-era cohort count mismatch')
    if sum(int(r['assignment_count']) for r in diversity)!=sum(len(by_genre[mid]) for ids in platforms.values() for mid in ids):
        raise ValueError('Genre assignment reconciliation failed')
    return outputs


def save_table(path, rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def run(prepared, phase03, destination, *, figures=True):
    if destination.exists():
        raise ValueError('Refusing to overwrite existing Phase 04 output')
    pqa_path=prepared/'preparation_qa.json'
    pqa=json.loads(pqa_path.read_text(encoding='utf-8'))
    if pqa.get('status')!='prepared_with_historical_source_limitations':
        raise ValueError('Phase 02 status not approved')
    for name in INPUTS:
        if digest(prepared/name)!=pqa['output_sha256'][name]:
            raise ValueError(f'Phase 02 hash mismatch: {name}')
    eqa_path=phase03/'eda_qa.json'
    eqa=json.loads(eqa_path.read_text(encoding='utf-8'))
    if eqa.get('records')!=pqa['movie_rows'] or eqa.get('platform_memberships')!=pqa['platform_membership_rows'] or eqa.get('genre_assignments')!=pqa['genre_assignment_rows']:
        raise ValueError('Phase 03 counts disagree with Phase 02')
    for name,expected in eqa['output_hashes'].items():
        if digest(phase03/name)!=expected:
            raise ValueError(f'Phase 03 output hash mismatch: {name}')
    movies=read_csv(prepared/INPUTS[0],{'source_id','release_year','platform_count','imdb_rating','rotten_tomatoes_percent','runtime_minutes'})
    memberships=read_csv(prepared/INPUTS[1],{'source_id','platform'})
    genres=read_csv(prepared/INPUTS[2],{'source_id','genre'})
    if (len(movies),len(memberships),len(genres)) != (pqa['movie_rows'],pqa['platform_membership_rows'],pqa['genre_assignment_rows']):
        raise ValueError('Phase 02 actual CSV lengths disagree with QA')
    outputs=build(movies,memberships,genres)
    destination.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='_phase04_stage_',dir=destination.parent))
    try:
        for name,rows in outputs.items():
            save_table(staging/f'{name}.csv',rows)
        if figures:
            from streaming_library.comparative_figures import generate
            generate(outputs,staging/'figures')
        files=sorted(p for p in staging.rglob('*') if p.is_file())
        qa=dict(status='comparative_outputs_pending_review',generated_at_utc=datetime.now(timezone.utc).isoformat(),
                scope='Historical descriptive comparisons only; no inference to current catalogues',
                input_qa_hashes={'phase02':digest(pqa_path),'phase03':digest(eqa_path)},
                counts={'movies':len(movies),'memberships':len(memberships),'genres':len(genres)},
                table_rows={name:len(rows) for name,rows in outputs.items()},
                output_hashes={p.relative_to(staging).as_posix():digest(p) for p in files},
                cautions=['Platforms overlap, so group estimates are dependent',
                          'Genre tags are multi-label; fractional allocation is only a diversity sensitivity measure',
                          'Observed rating means describe non-missing rows only',
                          'Release era is film release date, not catalogue entry date',
                          'Unknown historical sampling/snapshot prevents population inference'])
        (staging/'comparative_qa.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf-8')
        staging.rename(destination)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return qa


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-dir',type=Path,default=Path('outputs/phase02_preparation'))
    parser.add_argument('--phase03-dir',type=Path,default=Path('outputs/phase03_eda'))
    parser.add_argument('--output-dir',type=Path,default=Path('outputs/phase04_comparative'))
    parser.add_argument('--no-figures',action='store_true')
    args=parser.parse_args()
    qa=run(args.prepared_dir,args.phase03_dir,args.output_dir,figures=not args.no_figures)
    print('PASS - Phase 04 historical comparative analysis')
    print('Tables:',qa['table_rows'],'output hashes:',len(qa['output_hashes']))
    print('Outputs:',args.output_dir)

if __name__=='__main__': main()
