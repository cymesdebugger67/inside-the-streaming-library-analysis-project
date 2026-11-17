from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import tempfile
from collections import Counter
from pathlib import Path

from streaming_library.integrated import PLATFORMS, load_project, sha256

ERAS = ('before_1950', '1950_1979', '1980_1999', '2000_2009', '2010_2020')
METRICS = (('imdb', 'imdb_rating'), ('rt', 'rotten_tomatoes_percent'), ('runtime', 'runtime_minutes'))


def era(year):
    value = int(year)
    if value < 1950:
        return ERAS[0]
    if value < 1980:
        return ERAS[1]
    if value < 2000:
        return ERAS[2]
    if value < 2010:
        return ERAS[3]
    if value <= 2020:
        return ERAS[4]
    raise ValueError('Unexpected historical release year')


def measure(rows, column):
    data = [float(row[column]) for row in rows if row[column] != '']
    return {'observed_n': len(data), 'coverage_pct': round(100 * len(data) / len(rows), 4) if rows else 0.0,
            'observed_mean': round(statistics.mean(data), 5) if data else '',
            'observed_median': round(statistics.median(data), 5) if data else ''}


def analyse(movies, memberships, genres, metadata):
    if len(movies) != 16744:
        raise ValueError('Unexpected source population')
    if sum(len(memberships[mid]) for mid in movies) != 17381:
        raise ValueError('Unexpected membership count')
    platform_ids = {p: sorted(mid for mid in movies if p in memberships[mid]) for p in PLATFORMS}
    if any(not ids for ids in platform_ids.values()):
        raise ValueError('Missing platform')
    cohorts = {mid: era(movie['release_year']) for mid, movie in movies.items()}
    all_genres = Counter(g for tags in genres.values() for g in tags)
    rows = {}
    release = []
    missingness = []
    scores = []
    standardization = []
    total_era = Counter(cohorts.values())
    if sum(total_era.values()) != len(movies):
        raise ValueError('Era allocation mismatch')
    pooled_weights = {e: total_era[e] / len(movies) for e in ERAS}
    for p in PLATFORMS:
        ids = platform_ids[p]
        group = [movies[mid] for mid in ids]
        overall = measure(group, 'imdb_rating')
        standard_mean = 0.0
        valid_standard = True
        for e in ERAS:
            chosen = [mid for mid in ids if cohorts[mid] == e]
            members = [movies[mid] for mid in chosen]
            release.append({'platform': p, 'release_era': e, 'movie_count': len(chosen),
                            'platform_era_share_pct': round(100*len(chosen)/len(ids),4),
                            'source_union_era_share_pct': round(100*pooled_weights[e],4)})
            for dimension in ('country', 'language'):
                n = sum(bool(metadata[dimension][mid]) for mid in chosen)
                missingness.append({'platform': p, 'release_era': e, 'metric': dimension,
                                    'denominator': len(chosen), 'observed_n': n,
                                    'coverage_pct': round(100*n/len(chosen),4) if chosen else 0.0})
            for metric, key in METRICS:
                stats = measure(members, key)
                scores.append({'platform': p, 'release_era': e, 'metric': metric,
                               'denominator': len(chosen), **stats})
                if metric == 'imdb':
                    if not stats['observed_n'] and pooled_weights[e]:
                        valid_standard = False
                    elif stats['observed_n']:
                        standard_mean += pooled_weights[e] * stats['observed_mean']
            meta_n = sum(bool(movies[mid]['rotten_tomatoes_percent']) for mid in chosen)
            missingness.append({'platform': p, 'release_era': e, 'metric': 'rotten_tomatoes',
                                'denominator': len(chosen), 'observed_n': meta_n,
                                'coverage_pct': round(100*meta_n/len(chosen),4) if chosen else 0.0})
        standardization.append({'platform': p, 'imdb_observed_n': overall['observed_n'],
                                'imdb_observed_coverage_pct': overall['coverage_pct'],
                                'raw_observed_mean': overall['observed_mean'],
                                'era_standardized_observed_mean': round(standard_mean,5) if valid_standard else '',
                                'difference_standard_minus_raw': round(standard_mean-overall['observed_mean'],5) if valid_standard else '',
                                'standardization_population': 'pooled_unique_movie_release_era_distribution',
                                'interpretation': 'descriptive_observed_only_not_quality_ranking'})
    specialization = []
    for p in PLATFORMS:
        ids = platform_ids[p]
        for g in sorted(all_genres):
            n = sum(g in genres[mid] for mid in ids)
            union_n = sum(g in tags for tags in genres.values())
            platform_share = n / len(ids)
            union_share = union_n / len(movies)
            specialization.append({'platform': p, 'genre': g, 'movie_count': n,
                                   'platform_memberships': len(ids), 'prevalence_pct': round(100*platform_share,4),
                                   'source_union_prevalence_pct': round(100*union_share,4),
                                   'prevalence_ratio_vs_union': round(platform_share/union_share,5) if union_share else '',
                                   'union_movie_count': union_n})
    overlaps = []
    for i, p in enumerate(PLATFORMS):
        a = set(platform_ids[p])
        for q in PLATFORMS[i+1:]:
            b = set(platform_ids[q]); shared = len(a & b); union = len(a | b)
            overlaps.append({'platform_a': p, 'platform_b': q, 'a_movies': len(a), 'b_movies': len(b),
                             'shared_movies': shared, 'unique_union': union,
                             'jaccard_pct': round(100*shared/union,5),
                             'a_shared_pct': round(100*shared/len(a),5),
                             'b_shared_pct': round(100*shared/len(b),5),
                             'directional_gap_percentage_points': round(100*shared/len(a)-100*shared/len(b),5)})
    memberships_dist = Counter(len(memberships[mid]) for mid in movies)
    membership_rows = [{'platform_count': k, 'movie_count': memberships_dist[k],
                        'share_of_unique_movies_pct': round(100*memberships_dist[k]/len(movies),5)} for k in range(1,5)]
    ages = sorted({row['age_classification'].strip() or '(missing)' for row in movies.values()})
    age_rows = []
    for p in PLATFORMS:
        ids = platform_ids[p]
        for a in ages:
            n = sum((movies[mid]['age_classification'].strip() or '(missing)') == a for mid in ids)
            age_rows.append({'platform': p, 'age_classification': a, 'movie_count': n,
                             'membership_denominator': len(ids), 'percentage': round(100*n/len(ids),5)})
    rows['release_era_profile'] = release
    rows['metadata_coverage_by_era'] = missingness
    rows['observed_scores_by_era'] = scores
    rows['imdb_era_standardization'] = standardization
    rows['genre_specialization'] = specialization
    rows['overlap_asymmetry'] = overlaps
    rows['membership_multiplicity'] = membership_rows
    rows['age_classification_profile'] = age_rows
    if sum(r['movie_count'] for r in membership_rows) != len(movies):
        raise ValueError('Membership distribution sum mismatch')
    if sum(int(r['platform_count'])*r['movie_count'] for r in membership_rows) != 17381:
        raise ValueError('Membership multiplicity sum mismatch')
    if any(sum(r['movie_count'] for r in release if r['platform']==p)!=len(platform_ids[p]) for p in PLATFORMS):
        raise ValueError('Release profile total mismatch')
    if any(sum(r['movie_count'] for r in age_rows if r['platform']==p)!=len(platform_ids[p]) for p in PLATFORMS):
        raise ValueError('Age profile total mismatch')
    return rows


def write_csv(path, rows):
    if not rows:
        raise ValueError('No table rows')
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def charts(tables, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    def finish(name, fig):
        fig.savefig(folder / (name + '.png'), dpi=165, bbox_inches='tight', facecolor='white')
        plt.close(fig)

    era_colors = plt.get_cmap('viridis')(np.linspace(.18,.83,len(ERAS)))
    fig, ax = plt.subplots(figsize=(10,4.9))
    left = np.zeros(len(PLATFORMS))
    for i,e in enumerate(ERAS):
        vals = [next(r['platform_era_share_pct'] for r in tables['release_era_profile'] if r['platform']==p and r['release_era']==e) for p in PLATFORMS]
        ax.barh(PLATFORMS, vals, left=left, color=era_colors[i], label=e.replace('_','–'))
        left += np.array(vals)
    ax.set_xlim(0,100);ax.set_xlabel('Percentage of each platform’s recorded movies')
    ax.invert_yaxis();ax.legend(loc='upper center',bbox_to_anchor=(.5,-.16),ncol=3,frameon=False,fontsize=8)
    ax.set_title('Release-era composition | historical catalogue snapshot',loc='left',fontweight='bold')
    fig.tight_layout();finish('release_era_composition',fig)

    selected = sorted({r['genre'] for r in tables['genre_specialization'] if r['union_movie_count']>=500},
                      key=lambda g: next(r['union_movie_count'] for r in tables['genre_specialization'] if r['genre']==g),reverse=True)[:12]
    matrix=np.array([[next(r['prevalence_ratio_vs_union'] for r in tables['genre_specialization'] if r['platform']==p and r['genre']==g) for g in selected] for p in PLATFORMS])
    fig,ax=plt.subplots(figsize=(11,4.5)); im=ax.imshow(matrix,aspect='auto',cmap='RdBu_r',vmin=0,vmax=max(2.5,float(matrix.max())))
    ax.set_xticks(range(len(selected)),selected,rotation=42,ha='right');ax.set_yticks(range(len(PLATFORMS)),PLATFORMS)
    for i in range(len(PLATFORMS)):
        for j in range(len(selected)):
            ax.text(j,i,f'{matrix[i,j]:.1f}',ha='center',va='center',fontsize=8,color='black')
    ax.set_title('Genre specialization | prevalence ratio to source union',loc='left',fontweight='bold')
    fig.colorbar(im,ax=ax,label='Relative prevalence; 1 = source union',shrink=.8)
    fig.tight_layout();finish('genre_specialization_heatmap',fig)

    matrix=np.array([[next(r['coverage_pct'] for r in tables['metadata_coverage_by_era'] if r['platform']==p and r['release_era']==e and r['metric']=='rotten_tomatoes') for e in ERAS] for p in PLATFORMS])
    fig,ax=plt.subplots(figsize=(10,4.2));im=ax.imshow(matrix,aspect='auto',cmap='YlGnBu',vmin=0,vmax=100)
    ax.set_xticks(range(len(ERAS)),[e.replace('_','–') for e in ERAS],rotation=20,ha='right');ax.set_yticks(range(len(PLATFORMS)),PLATFORMS)
    for i in range(len(PLATFORMS)):
        for j in range(len(ERAS)):
            ax.text(j,i,f'{matrix[i,j]:.0f}%',ha='center',va='center',fontsize=9,color='white' if matrix[i,j]>65 else 'black')
    ax.set_title('Rotten Tomatoes availability | platform × release era',loc='left',fontweight='bold')
    fig.colorbar(im,ax=ax,label='Observed score coverage (%)',shrink=.8);fig.tight_layout();finish('score_coverage_heatmap',fig)

    data=tables['imdb_era_standardization']; x=np.arange(len(PLATFORMS)); w=.35
    fig,ax=plt.subplots(figsize=(9,4.6))
    ax.bar(x-w/2,[r['raw_observed_mean'] for r in data],w,label='Raw observed mean')
    ax.bar(x+w/2,[r['era_standardized_observed_mean'] for r in data],w,label='Standardized to pooled release eras')
    ax.set_xticks(x,PLATFORMS);ax.set_ylim(0,9);ax.set_ylabel('IMDb score (observed records only)')
    ax.set_title('Release-era standardization | descriptive sensitivity',loc='left',fontweight='bold')
    ax.legend(frameon=False);fig.tight_layout();finish('imdb_release_era_standardization',fig)

    names=[]; left=[]; right=[]
    for r in tables['overlap_asymmetry']:
        names.append(r['platform_a']+' / '+r['platform_b'])
        left.append(r['a_shared_pct']);right.append(r['b_shared_pct'])
    pos=np.arange(len(names));fig,ax=plt.subplots(figsize=(10,5.4))
    ax.barh(pos-.19,left,.36,label='Share of first platform')
    ax.barh(pos+.19,right,.36,label='Share of second platform')
    ax.set_yticks(pos,names);ax.invert_yaxis();ax.set_xlabel('Shared IDs as % of platform’s catalogue')
    ax.set_title('Directional catalogue overlap | denominator matters',loc='left',fontweight='bold')
    ax.legend(frameon=False);fig.tight_layout();finish('directional_platform_overlap',fig)

    membership=tables['membership_multiplicity']; fig,ax=plt.subplots(figsize=(8,4.3))
    ax.bar([str(r['platform_count']) for r in membership],[r['movie_count'] for r in membership])
    for i,r in enumerate(membership):
        ax.text(i,r['movie_count'],str(r['movie_count']),ha='center',va='bottom')
    ax.set_ylabel('Unique source movie records');ax.set_xlabel('Number of represented platforms')
    ax.set_title('Observed multi-platform membership distribution',loc='left',fontweight='bold')
    fig.tight_layout();finish('membership_multiplicity',fig)


def summary_report(tables):
    release=tables['release_era_profile'];scores=tables['observed_scores_by_era'];special=tables['genre_specialization'];overlaps=tables['overlap_asymmetry'];standard=tables['imdb_era_standardization'];multiplicity=tables['membership_multiplicity']
    lines=['# Advanced Historical Streaming Library Analysis','', '**Project owner:** Cyril James Lunzaga','',
           'This is a descriptive extension of the undated historical source snapshot, not an estimate of modern catalogues, subscribers, causation, or current streaming availability.','',
           '## Research extensions','',
           'The analyses compare release-era mixtures, observed-score coverage, genre specialization, directional overlap, membership multiplicity, and the descriptive sensitivity of observed IMDb averages to release-era composition.','',
           '## Release-era composition','',
           '| Platform | Pre-2000 (%) | 2010–2020 (%) |','|---|---:|---:|']
    for p in PLATFORMS:
        old=sum(r['platform_era_share_pct'] for r in release if r['platform']==p and r['release_era'] in ERAS[:3]); recent=next(r['platform_era_share_pct'] for r in release if r['platform']==p and r['release_era']==ERAS[-1]);lines.append(f'| {p} | {old:.2f} | {recent:.2f} |')
    lines +=['','Release eras describe film production dates, not acquisition dates or catalogue-growth trajectories.','',
             '## Rotten Tomatoes recorded score coverage','',
             '| Platform | 2010–2020 score coverage (%) |','|---|---:|']
    for p in PLATFORMS:
        r=next(r for r in scores if r['platform']==p and r['release_era']=='2010_2020' and r['metric']=='rt')
        lines.append(f'| {p} | {r["coverage_pct"]:.2f} |')
    lines+=['','Coverage differences may reflect source completeness, time period and data acquisition; they do not establish the quality of a catalogue.','',
            '## Genre specialization','',
            'Genre prevalence is defined as the share of each platform’s recorded movies tagged with a genre, allowing multi-tag counts. The specialization ratio divides platform prevalence by prevalence among unique source records. The ratio is descriptive, not a significance test.','',
            '| Platform | Most overrepresented genre (at least 100 tagged platform films) | Ratio to union |','|---|---:|---:|']
    for p in PLATFORMS:
        candidates=[r for r in special if r['platform']==p and r['movie_count']>=100 and r['prevalence_ratio_vs_union']!='']
        r=max(candidates,key=lambda x:x['prevalence_ratio_vs_union']);lines.append(f'| {p} | {r["genre"]} | {r["prevalence_ratio_vs_union"]:.2f} |')
    lines+=['','## Directional overlap','',
            '| Platform pair | Shared IDs | % of first platform | % of second platform |','|---|---:|---:|---:|']
    for r in overlaps:
        lines.append(f'| {r["platform_a"]} / {r["platform_b"]} | {r["shared_movies"]} | {r["a_shared_pct"]:.2f} | {r["b_shared_pct"]:.2f} |')
    lines+=['','Asymmetry exists because the two directional percentages use different denominators. Titles may appear on more than two represented services.','',
            '## Membership multiplicity','',
            '| Represented platforms per movie | Unique movie records |','|---|---:|']
    for r in multiplicity:lines.append(f'| {r["platform_count"]} | {r["movie_count"]:,} |')
    lines+=['','## Release-era standardization sensitivity','',
            'The standardized observed IMDb mean weights platform-by-era observed score means by the release-era distribution of the pooled unique-movie source IDs. All historical-era strata are represented, but missing score patterns may be selective. This is an observational composition sensitivity, not a causal adjustment or quality comparison.','',
            '| Platform | Raw observed IMDb mean | Release-era standardized observed mean | Change |','|---|---:|---:|---:|']
    for r in standard:lines.append(f'| {r["platform"]} | {r["raw_observed_mean"]:.3f} | {r["era_standardized_observed_mean"]:.3f} | {r["difference_standard_minus_raw"]:+.3f} |')
    lines+=['','## Methodological boundaries','',
            'The source was not sampled randomly from all available films or contemporary streaming services. A record ID is a source key and need not represent a globally deduplicated film. A multi-platform flag does not establish territorial rights or simultaneous availability. Release year is not a date of joining a platform. Missing values remain missing; ratings are summarized only where observed. Age classifications and multi-label genres reflect the historical source text.','',
            'These analyses are descriptive: no hypothesis-testing p-values, population intervals, market-share estimates, subscriber forecasts, causal claims or recommendation-engine performance are asserted.','',
            '## Reproduction','',
            'Run `python -m streaming_library.advanced_analysis` after preparing verified Phases 02–05. Inspect the generated CSV tables, six PNG figures and `advanced_qa.json` in `outputs/phase08_advanced/`. This output folder is intentionally Git-ignored. For public figure display, publish the independently generated plots included in `assets/advanced/` after confirming that local output hashes match.','']
    return '\n'.join(lines)


def run(root, output):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists():
        raise ValueError('Refusing to overwrite advanced analytical output')
    movies,memberships,genres,metadata=load_project(root)
    tables=analyse(movies,memberships,genres,metadata)
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='_advanced_stage_',dir=output.parent))
    try:
        for name,rows in tables.items():write_csv(stage/(name+'.csv'),rows)
        charts(tables,stage)
        (stage/'advanced_findings.md').write_text(summary_report(tables),encoding='utf-8')
        expected={name:sha256(stage/name) for name in sorted(p.name for p in stage.iterdir() if p.is_file())}
        manifest={'status':'advanced_descriptive_analyses_pending_final_visual_review',
                  'source_population':len(movies), 'platform_memberships':sum(len(x) for x in memberships.values()),
                  'table_rows':{key:len(val) for key,val in tables.items()},
                  'figure_count':len(list(stage.glob('*.png'))),
                  'output_sha256':expected,
                  'provenance':'Verified Phase 02–05 historical source derivatives',
                  'limitations':'Historical undated nonprobability snapshot; descriptive outcomes only'}
        (stage/'advanced_qa.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        stage.rename(output)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return manifest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path('outputs/phase08_advanced'))
    args=parser.parse_args()
    result=run(args.root,args.output)
    print('PASS - Advanced historical streaming analyses')
    print('Movie records:',result['source_population'])
    print('Analytical tables:',len(result['table_rows']))
    print('Figures:',result['figure_count'])
    print('Output:',args.output)


if __name__=='__main__':main()
