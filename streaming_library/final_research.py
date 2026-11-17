from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from streaming_library.integrated import PLATFORMS, sha256, verify_stages


def load_rows(path: Path, columns: set[str]):
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not columns.issubset(reader.fieldnames):
            raise ValueError('Unexpected table schema: ' + str(path))
        rows = list(reader)
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError('Empty or malformed table: ' + str(path))
    return rows


def verify_methods(root: Path):
    verify_stages(root)
    folder = root / 'outputs' / 'phase07_methods'
    qa = json.loads((folder / 'phase07_methods_qa.json').read_text(encoding='utf-8'))
    expected = {'coalition_coverage.csv', 'shapley_attribution.csv',
                'genre_entropy_sensitivity.csv', 'equal_size_genre_resampling.csv'}
    if set(qa['output_hashes']) != expected:
        raise ValueError('Phase 07 output manifest does not match approved schema')
    for name, fingerprint in qa['output_hashes'].items():
        file = folder / name
        if not file.is_file() or sha256(file) != fingerprint:
            raise ValueError('Phase 07 fingerprint mismatch: ' + name)
    if (qa['source_population'], qa['membership_count'], qa['genre_assignment_count'], qa['coalitions']) != (16744, 17381, 39098, 16):
        raise ValueError('Phase 07 population mismatch')
    return qa


def fmt(value, digits=2):
    return f'{float(value):,.{digits}f}'


def generate(root: Path, output: Path):
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Refusing to overwrite existing final report')
    qa = verify_methods(root)
    base = root / 'outputs'
    coalitions = load_rows(base/'phase07_methods/coalition_coverage.csv', {'subset_mask','unique_movies'})
    shapley = load_rows(base/'phase07_methods/shapley_attribution.csv', {'platform','membership_movies','exclusive_movies','shapley_allocated_movies'})
    sensitivity = load_rows(base/'phase07_methods/genre_entropy_sensitivity.csv', {'platform','allocation_method','effective_genres_shannon','known_genre_movies','membership_movies'})
    draws = load_rows(base/'phase07_methods/equal_size_genre_resampling.csv', {'platform','draw','sample_size','effective_genres_shannon','genre_known_n'})
    summary = load_rows(base/'phase03_eda/platform_summary.csv', {'platform','movie_count','release_year_median','rt_n','rt_coverage_pct'})
    overlap = load_rows(base/'phase04_comparative/overlap_asymmetry.csv', {'platform_a','platform_b','shared','jaccard_pct'})
    meta = load_rows(base/'phase05_metadata_reviewed/metadata_source_quality.csv', {'dimension','known_movies','missing_movies','assignments'})
    genre = load_rows(base/'phase03_eda/genre_platform.csv', {'platform','genre','movies','percent_of_platform_movies'})
    integrated = json.loads((base/'phase06_integrated/integrated_summary.json').read_text(encoding='utf-8'))
    if (integrated['source_population'], integrated['metrics']['platform_memberships'], integrated['metrics']['multi_platform_movies']) != (16744,17381,627):
        raise ValueError('Integrated summary reconciliation failed')
    if len(coalitions) != 16 or sorted(int(r['subset_mask']) for r in coalitions) != list(range(16)):
        raise ValueError('Coalition enumeration incomplete')
    if int(coalitions[0]['unique_movies']) != 0 or int(coalitions[-1]['unique_movies']) != 16744:
        raise ValueError('Coalition endpoints incorrect')
    if len(shapley) != 4 or set(r['platform'] for r in shapley) != set(PLATFORMS):
        raise ValueError('Platform attribution missing')
    if not math.isclose(sum(float(r['shapley_allocated_movies']) for r in shapley),16744,abs_tol=1e-6):
        raise ValueError('Shapley efficiency failed')
    if len(sensitivity) != 8 or len(draws) != 4*qa['resampling']['draws_per_platform']:
        raise ValueError('Genre sensitivity row count mismatch')
    if any(int(r['sample_size']) != qa['resampling']['sample_size'] for r in draws):
        raise ValueError('Resampling sample size mismatch')
    if set(r['dimension'] for r in meta) != {'country','language'}:
        raise ValueError('Missing metadata dimension')
    by_platform = {r['platform']:r for r in summary}
    div = {(r['platform'],r['allocation_method']):r for r in sensitivity}
    draw_group = defaultdict(list)
    for r in draws:
        draw_group[r['platform']].append(float(r['effective_genres_shannon']))
    top_pair = max(overlap,key=lambda r:float(r['jaccard_pct']))
    overall = integrated['metrics']
    parts = [
        '# Inside the Streaming Library — Research Findings', '',
        '**Project owner:** Cyril James Lunzaga', '',
        '**Study design:** descriptive analysis of one undated, historical, four-platform movie catalogue snapshot. This is not a study of contemporary availability, audiences, subscriber demand, or market share.', '',
        '## Research question and interpretation', '',
        'How does recorded movie catalogue size relate to unique union coverage, platform overlap, release-era composition, observed metadata and genre variety? Does additional membership correspond to additional unique represented movie records? The unit is the source movie ID; platform flags and genre labels can overlap.', '',
        '## Source and data lineage', '',
        'The source is the 17-column historical CSV mirror of the Ruchi Bhatia four-platform movies dataset, retrieved from the [SalimAmarti OTT_movies_Project mirror](https://github.com/SalimAmarti/OTT_movies_Project/blob/master/MoviesOnStreamingPlatforms_updated.csv). Exact raw SHA-256: `c7a1b949495c35879b038c97f92bbe233d1b0b348719f3d4a8020927645c0c27`. Its precise collection/snapshot date is not established. Source movie IDs are not independently verified global film identifiers. Output tables are reconstructed from hashed Phases 02–05 and the reviewed Phase 07 methods manifest.', '',
        '## Dataset quality and analytical grain', '',
        f'- Distinct source movie records: **{overall["unique_movie_records"]:,}**; platform memberships (non-exclusive): **{overall["platform_memberships"]:,}**; source records with multiple represented platforms: **{overall["multi_platform_movies"]:,}**.',
        '- Prepared dataset has **39,098 multi-label genre assignments**. All platform totals count memberships, not independent unique films.',
        f'- Observed numeric metadata: IMDb **{overall["imdb_observed_n"]:,} / 16,744**, Rotten Tomatoes **{overall["rt_observed_n"]:,} / 16,744**, valid runtime **{overall["runtime_observed_n"]:,} / 16,744**. Means apply only among observed values; missingness may be selective.',
        '- One source runtime (Colorado, 1940, source ID 13180, value 1256) is deliberately excluded from validated runtime statistics rather than guessed or corrected.',
    ]
    for r in sorted(meta,key=lambda r:r['dimension']):
        parts.append(f'- Recorded {r["dimension"]} metadata: **{int(r["known_movies"]):,}** movie records with >=1 recognized label; **{int(r["missing_movies"]):,}** without a recognized label; **{int(r["assignments"]):,}** labels. The named-language policy excludes literal `None` tokens but keeps raw source text.')
    parts += ['', '## Platform catalogue size and observed coverage', '',
              '| Platform | Membership movies | Median film release year | Rotten Tomatoes observed | RT coverage |',
              '|---|---:|---:|---:|---:|']
    for p in PLATFORMS:
        r=by_platform[p]
        parts.append(f'| {p} | {int(r["movie_count"]):,} | {int(float(r["release_year_median"]))} | {int(r["rt_n"]):,} | {fmt(r["rt_coverage_pct"])}% |')
    parts += ['', 'Different release-year compositions and unequal score coverage prevent a credible platform-quality ranking from observed score means. Release year is not the date a title entered any service.', '',
              '## Pairwise overlap', '',
              '| Pair | Shared source movie IDs | Jaccard similarity |', '|---|---:|---:|']
    for r in overlap:
        parts.append(f'| {r["platform_a"]} / {r["platform_b"]} | {int(r["shared"]):,} | {fmt(r["jaccard_pct"])}% |')
    parts += ['', f'The largest **observed Jaccard percentage** in these source flags is {top_pair["platform_a"]} / {top_pair["platform_b"]} ({fmt(top_pair["jaccard_pct"])}%). These pairs need not be representative of future catalogues.', '',
              '## Unique coverage and exact four-player Shapley attribution', '',
              'Sixteen coalitions (including the empty set) yield the total represented union. A movie listed by k of the four platforms contributes 1/k Shapley units to each represented platform; the four allocations therefore sum to the 16,744 source IDs.', '',
              '| Platform | Membership movies | Exclusive within four-platform dataset | Shapley allocated movie equivalents |', '|---|---:|---:|---:|']
    for r in shapley:
        parts.append(f'| {r["platform"]} | {int(r["membership_movies"]):,} | {int(r["exclusive_movies"]):,} | {fmt(r["shapley_allocated_movies"],3)} |')
    parts += ['', '**Interpretation:** exclusivity/leave-one-out union loss is a separate measure from Shapley allocation. A Shapley share is an accounting allocation of historical source IDs, not subscriber value, audience preference, or commercial market share.', '',
              '## Genre composition, diversity and sensitivity', '',
              'Fractional movie allocation gives each genre-classified movie total weight 1 across all of its tags. Full-tag allocation gives each tag weight 1; both are plausible descriptions of different quantities. Shannon effective genres = exp(Shannon entropy). Missing genres are excluded and their coverage is separately reported.', '',
              '| Platform | Fractional effective Shannon genres | Full-tag effective Shannon genres | Genre-known source movies |', '|---|---:|---:|---:|']
    for p in PLATFORMS:
        a,b=div[p,'fractional_movie'],div[p,'full_tag']
        parts.append(f'| {p} | {fmt(a["effective_genres_shannon"],3)} | {fmt(b["effective_genres_shannon"],3)} | {int(a["known_genre_movies"]):,} / {int(a["membership_movies"]):,} |')
    parts += ['', f'Equal-size descriptive resampling draws **{qa["resampling"]["sample_size"]:,}** movies without replacement from each platform for **{qa["resampling"]["draws_per_platform"]:,}** draws per platform, seed **{qa["resampling"]["seed"]}**. Values below summarize *within-archive variation*, not inferential confidence intervals.', '',
              '| Platform | Mean effective Shannon genres | Minimum | Maximum |', '|---|---:|---:|---:|']
    for p in PLATFORMS:
        v=draw_group[p]
        parts.append(f'| {p} | {fmt(sum(v)/len(v),3)} | {fmt(min(v),3)} | {fmt(max(v),3)} |')
    parts += ['', 'Disney+ has the smallest represented catalogue (564 movies); every size-564 draw therefore includes its complete represented catalogue, producing an identical result on every draw. These resamples are not independent observations of platform policies or future catalogues.', '',
              '## Recorded genre prevalence example', '',
              'Genre percentages use total movies on each represented platform as denominators and are **not mutually exclusive**. Three frequently reported genres in each catalogue (as recorded):', '',
              '| Platform | Genre | Movie records | Percentage of platform movies |', '|---|---|---:|---:|']
    for p in PLATFORMS:
        matches=sorted((r for r in genre if r['platform']==p),key=lambda r:-int(r['movies']))[:3]
        for r in matches:
            parts.append(f'| {p} | {r["genre"]} | {int(r["movies"]):,} | {fmt(r["percent_of_platform_movies"])}% |')
    parts += ['', '## Limitations and decisions', '',
              '- Historical mirror snapshot date is unknown, and archived platform flags have not been reverified against current catalogues.',
              '- Records are historical source IDs; they do not establish global work identity, intellectual-property exclusivity, streaming territory, availability windows or viewer experience.',
              '- Multi-label genre, country and language metadata are imperfect source text. Country labels do not validate geography and language labels do not verify audio tracks.',
              '- Invalid runtime and absent scores are not imputed. Comparing observed score averages across differently covered catalogues would invite selection bias.',
              '- Diversity rankings depend on tag-weighting definitions and catalogue size; equal-size resampling is a descriptive robustness check, not a population confidence interval.',
              '- No bootstrap population intervals or membership-prediction model are claimed: neither would identify contemporary market outcomes from this undated nonprobability source.',
              '- No causal, longitudinal catalogue-growth, revenue, subscriber, viewing, or market-share conclusions are supported.', '',
              '## Reproducibility and evidence trail', '',
              'Reproduce with the exact raw CSV and SHA-256 noted above. Generate stages in the order documented in README.md and then execute `python -m streaming_library.final_research`. The final report generator checks stage QA hashes and reconciles the coalition, Shapley, genre and resampling tables before writing output; it refuses to replace an existing report. The comprehensive report is generated locally under ignored outputs; source data and generated tables are not public Git artifacts.', '',
              '## Conclusion', '',
              'These data show substantial differences in **historically represented** platform movie counts, small overall multi-platform record incidence, and platform-dependent genre compositions. Exact Shapley attribution distinguishes unique coverage from overlapping membership accounting. Diversity comparisons change with tag weighting and equal-size selection. They provide a transparent descriptive comparison of this source snapshot, **not** evidence about present-day services or consumer decisions.', ''
              ]
    output.parent.mkdir(parents=True,exist_ok=True)
    data='\n'.join(parts)
    output.write_text(data,encoding='utf-8')
    return {'report_sha256':sha256(output),'report':str(output),'source_movies':16744,'platforms':4,
            'phase07_qa_sha256':sha256(base/'phase07_methods/phase07_methods_qa.json')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path('outputs/phase07_final/research_findings.md'))
    args=parser.parse_args()
    result=generate(args.root,args.output)
    print('PASS - source-grounded report created')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
