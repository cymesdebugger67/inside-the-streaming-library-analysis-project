from pathlib import Path
import csv
import json

from streaming_library.integrated import sha256


def read_table(folder, name):
    with (folder / (name + '.csv')).open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))


def main():
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit('Install dashboard dependencies using requirements-dashboard.txt') from exc
    root = Path(__file__).resolve().parents[1]
    folder = root / 'outputs' / 'phase08_advanced'
    st.set_page_config(page_title='Streaming Library | Analytical Atlas', layout='wide')
    st.title('Inside the Streaming Library | Analytical Atlas')
    st.caption('Cyril James Lunzaga · Historical source-record analysis')
    st.info('Undated historical four-platform movie snapshot. Not current catalogue availability, market share, viewership or causal evidence.')
    manifest_file = folder / 'advanced_qa.json'
    if not manifest_file.is_file():
        st.error('Generate outputs first: python -m streaming_library.advanced_analysis')
        st.stop()
    try:
        manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
        for name, fingerprint in manifest['output_sha256'].items():
            if sha256(folder/name) != fingerprint:
                raise ValueError('Output hash mismatch: '+name)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        st.error('Analytical output validation failed: '+str(exc))
        st.stop()
    left, middle, right = st.columns(3)
    left.metric('Source movie records', f'{manifest["source_population"]:,}')
    middle.metric('Platform memberships', f'{manifest["platform_memberships"]:,}')
    right.metric('New analytical tables', len(manifest['table_rows']))
    pages = {
        'Release eras': [('release_era_composition.png','release_era_profile')],
        'Genre specialization': [('genre_specialization_heatmap.png','genre_specialization')],
        'Score completeness': [('score_coverage_heatmap.png','metadata_coverage_by_era'),('imdb_release_era_standardization.png','imdb_era_standardization')],
        'Catalogue overlap': [('directional_platform_overlap.png','overlap_asymmetry'),('membership_multiplicity.png','membership_multiplicity')],
        'Detailed score profiles': [(None,'observed_scores_by_era'),(None,'age_classification_profile')],
    }
    choice = st.selectbox('Analytical topic', tuple(pages))
    for picture, table in pages[choice]:
        st.subheader(table.replace('_',' ').title())
        if picture:
            st.image(str(folder/picture), width='stretch')
        data = read_table(folder,table)
        st.dataframe(data, width='stretch', hide_index=True)
    st.divider()
    st.subheader('Research interpretation and boundaries')
    st.markdown((folder/'advanced_findings.md').read_text(encoding='utf-8'))
    st.caption('All tables and figures have file-level fingerprints recorded in advanced_qa.json. This application reads locally generated results, not current platform APIs.')


if __name__ == '__main__':
    main()
