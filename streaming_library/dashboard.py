"""Local Streamlit dashboard: streamlit run streaming_library/dashboard.py"""
from __future__ import annotations

from pathlib import Path

from streaming_library.integrated import (
    PLATFORMS, describe_selection, filter_ids, load_project,
)

ERA = ('All','before_1950','1950_1979','1980_1999','2000_2009','2010_plus')


def main():
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit('Install the optional dashboard dependencies: python -m pip install -r requirements-dashboard.txt') from exc

    st.set_page_config(page_title='Inside the Streaming Library', layout='wide')
    st.title('Inside the Streaming Library')
    st.caption('Historical movie catalogue membership analysis · Cyril James Lunzaga')
    st.warning('Historical undated snapshot. Not current availability, viewing activity, market share, or catalogue growth.')
    root = Path(__file__).resolve().parents[1]

    @st.cache_data(show_spinner=False)
    def data():
        return load_project(root)

    try:
        movies, memberships, genres, metadata = data()
    except (OSError, ValueError, KeyError) as exc:
        st.error(f'Input validation failed: {exc}. Generate and validate Phases 02–05 first.')
        st.stop()

    genre_options = sorted({g for labels in genres.values() for g in labels})
    platform = st.sidebar.selectbox('Recorded platform', ('All', *PLATFORMS))
    era = st.sidebar.selectbox('Movie release era', ERA)
    genre = st.sidebar.selectbox('Recorded genre', ('All', *genre_options))
    dim = st.sidebar.selectbox('Metadata category', ('All','country','language'))
    labels = ('All', *sorted({label for values in metadata.get(dim,{}).values() for label in values})) if dim != 'All' else ('All',)
    label = st.sidebar.selectbox('Recorded metadata label', labels)
    ids = filter_ids(movies,memberships,genres,metadata,platform=platform,era=era,genre=genre,metadata_dimension=dim,metadata_label=label)
    summary = describe_selection(ids,movies,memberships,genres)
    a,b,c = st.columns(3)
    a.metric('Unique movie records', f'{summary["unique_movie_records"]:,}')
    b.metric('Platform memberships', f'{summary["platform_memberships"]:,}')
    c.metric('Multi-platform movies', f'{summary["multi_platform_movies"]:,}')
    st.caption('Counts reflect current filters. A film can appear on multiple platforms and in multiple genres.')
    col1,col2 = st.columns(2)
    with col1:
        st.subheader('Membership by platform')
        st.bar_chart(summary['platform_movie_counts'], horizontal=True)
    with col2:
        st.subheader('Top 15 recorded genres')
        if summary['top_genres']:
            st.bar_chart({r['genre']:r['movie_count'] for r in summary['top_genres']},horizontal=True)
        else:
            st.info('No genre labels in this selection')
    st.subheader('Numeric metadata availability')
    cols=st.columns(3)
    for target, label, key in zip(cols, ('IMDb','Rotten Tomatoes','Runtime'), ('imdb','rt','runtime')):
        n=summary[f'{key}_observed_n']
        mean=summary[f'{key}_mean_observed']
        with target:
            st.metric(label + ' observed', f'{n:,} / {len(ids):,}')
            st.caption('Observed mean: ' + (f'{mean:.2f}' if mean is not None else 'N/A'))
    st.caption('Observed averages exclude missing values and may be selection-biased; do not interpret them as quality rankings.')
    st.subheader('Movie records (limited preview)')
    st.dataframe([{'title':movies[mid]['title'], 'release_year':movies[mid]['release_year'],
                   'platforms':', '.join(sorted(memberships[mid])), 'genre_count':len(genres[mid])}
                  for mid in ids[:100]], width="stretch",hide_index=True)
    st.caption(f'Preview displays up to 100 of {len(ids):,} selected records. No raw dataset is transmitted by the analysis code; local Streamlit configuration determines deployment behavior.')


if __name__ == '__main__':
    main()
