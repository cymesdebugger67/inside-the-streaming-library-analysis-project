"""Comparative figures: categorical displays and observational coverage."""
from pathlib import Path


def generate(tables, destination: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    destination.mkdir(parents=True,exist_ok=False)
    platforms=('Netflix','Hulu','Prime Video','Disney+')

    def save(name, title):
        ax=plt.gca()
        ax.set_title(title,loc='left',weight='bold',pad=13)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()
        plt.savefig(destination/name,dpi=180,bbox_inches='tight')
        plt.close()

    genre=tables['genre_prevalence']
    totals={}
    for r in genre:
        totals[r['genre']]=totals.get(r['genre'],0)+int(r['movies'])
    selected=[k for k,v in sorted(totals.items(),key=lambda kv:(-kv[1],kv[0]))[:12]]
    lookup={(r['platform'],r['genre']):float(r['prevalence_pct']) for r in genre}
    matrix=[[lookup.get((p,g),0) for g in selected] for p in platforms]
    fig,ax=plt.subplots(figsize=(12,4.7))
    im=ax.imshow(matrix,aspect='auto',interpolation='nearest')
    ax.set_xticks(range(len(selected)),selected,rotation=45,ha='right')
    ax.set_yticks(range(4),platforms)
    plt.colorbar(im,ax=ax,label='Movies with genre tag (% of platform)')
    save('01_genre_prevalence_heatmap.png','Historical genre tag prevalence — non-exclusive labels')

    era=tables['era_metric_coverage']
    group=('before_1950','1950_1979','1980_1999','2000_2009','2010_2020')
    # Categorical decade cohorts, not a historical platform trend.
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    for ax,p in zip(axes.flat,platforms):
        rows=[r for r in era if r['platform']==p and r['metric']=='imdb']
        lookup={r['release_era']:int(r['all_n']) for r in rows}
        n=sum(lookup.values())
        ax.bar(range(len(group)),[100*lookup.get(g,0)/n if n else 0 for g in group])
        ax.set_title(p)
        ax.set_xticks(range(len(group)),['<1950','1950–79','1980–99','2000–09','2010–20'],rotation=30,ha='right')
        ax.set_ylabel('Share of platform movies (%)')
        ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
    fig.suptitle('Film release-era composition, not catalogue growth',weight='bold')
    plt.tight_layout()
    plt.savefig(destination/'02_release_era_small_multiples.png',dpi=180,bbox_inches='tight')
    plt.close()

    missing=tables['platform_completeness']
    lookup={(r['platform'],r['metric']):float(r['observed_pct'] or 0) for r in missing}
    metrics=('imdb','rt','runtime')
    fig,ax=plt.subplots(figsize=(9,4.8))
    for j,m in enumerate(metrics):
        ax.bar([i+(j-1)*.23 for i in range(4)],[lookup[p,m] for p in platforms],width=.23,label={'imdb':'IMDb','rt':'Rotten Tomatoes','runtime':'Runtime'}[m])
    ax.set_xticks(range(4),platforms);ax.set_ylim(0,100);ax.set_ylabel('Observed field completeness (%)')
    ax.legend(frameon=False)
    save('03_rating_runtime_coverage.png','Coverage differences across historical catalogues')

    div=tables['genre_diversity']
    fig,ax=plt.subplots(figsize=(9,4.5))
    ax.barh([r['platform'] for r in div][::-1],[float(r['effective_genres_simpson'] or 0) for r in div][::-1])
    ax.set_xlabel('Effective number of genres (inverse Simpson)')
    save('04_fractional_genre_diversity.png','Genre diversity — fractional tag weighting')
