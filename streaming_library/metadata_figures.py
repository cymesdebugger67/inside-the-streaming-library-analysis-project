from pathlib import Path


def generate(tables, destination: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    destination.mkdir(parents=True,exist_ok=False)
    platforms=('Netflix','Hulu','Prime Video','Disney+')
    def finish(fig, name):
        fig.tight_layout()
        fig.savefig(destination/name,dpi=180,bbox_inches='tight')
        plt.close(fig)

    contributions={r['platform']:r for r in tables['catalogue_contributions']}
    fig,ax=plt.subplots(figsize=(10,5))
    ex=[int(contributions[p]['exclusive_movies']) for p in platforms]
    sh=[int(contributions[p]['shared_movies']) for p in platforms]
    x=range(len(platforms))
    ax.bar(x,ex,label='Exclusive to platform in source')
    ax.bar(x,sh,bottom=ex,label='Also on another included platform')
    ax.set_xticks(list(x),platforms)
    ax.set_ylabel('Recorded movies (overlapping across platforms)')
    ax.set_title('Exclusive and shared catalogue memberships — historical snapshot',loc='left')
    ax.legend(frameon=False)
    finish(fig,'01_exclusive_shared_catalogues.png')

    lookup={(r['platform'],r['dimension']):float(r['known_pct']) if r['known_pct'] else 0
            for r in tables['metadata_platform_coverage']}
    fig,ax=plt.subplots(figsize=(9,5))
    w=.32
    for j,dim in enumerate(('country','language')):
        ax.bar([i+(j-.5)*w for i in x],[lookup[p,dim] for p in platforms],width=w,label=dim.title())
    ax.set_xticks(list(x),platforms)
    ax.set_ylim(0,100)
    ax.set_ylabel('Movies with at least one recorded label (%)')
    ax.set_title('Metadata coverage — measured separately by platform',loc='left')
    ax.legend(frameon=False)
    finish(fig,'02_country_language_coverage.png')

    for dim,filename in [('country','03_country_label_prevalence.png'),
                         ('language','04_language_label_prevalence.png')]:
        rows=[r for r in tables['metadata_label_prevalence'] if r['dimension']==dim]
        totals={}
        for r in rows:
            key=r['label']
            totals[key]=totals.get(key,0)+int(r['movie_count'])
        labels=[k for k,_ in sorted(totals.items(),key=lambda item:(-item[1],item[0]))[:10]]
        lookup={(r['platform'],r['label']):float(r['prevalence_pct']) for r in rows}
        fig,ax=plt.subplots(figsize=(11,5))
        heat=[[lookup.get((p,label),0) for label in labels] for p in platforms]
        im=ax.imshow(heat,aspect='auto',interpolation='nearest')
        ax.set_xticks(list(range(len(labels))),labels,rotation=45,ha='right')
        ax.set_yticks(list(range(len(platforms))),platforms)
        ax.set_title(f'{dim.title()} tags in recorded movie metadata — not market reach',loc='left')
        fig.colorbar(im,ax=ax,label='Movies with label (% of platform catalogue)')
        finish(fig,filename)
