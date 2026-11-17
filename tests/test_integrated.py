import tempfile
import pickle
import unittest
from pathlib import Path

from streaming_library.integrated import build_index, describe_selection, filter_ids, csv_rows


class IntegratedTests(unittest.TestCase):
    def setUp(self):
        self.movies=[
            dict(source_id='1',title='One',release_year='2008',platform_count='2',imdb_rating='7.0',rotten_tomatoes_percent='',runtime_minutes='90'),
            dict(source_id='2',title='Two',release_year='2018',platform_count='1',imdb_rating='',rotten_tomatoes_percent='75',runtime_minutes=''),
            dict(source_id='3',title='Three',release_year='1940',platform_count='1',imdb_rating='8',rotten_tomatoes_percent='90',runtime_minutes='70'),
        ]
        membership=[dict(source_id='1',platform='Netflix'),dict(source_id='1',platform='Hulu'),dict(source_id='2',platform='Netflix'),dict(source_id='3',platform='Disney+')]
        genres=[dict(source_id='1',genre='Drama'),dict(source_id='1',genre='Action'),dict(source_id='2',genre='Drama')]
        metadata=[dict(source_id='1',dimension='country',label='United States'),dict(source_id='1',dimension='language',label='French'),dict(source_id='2',dimension='country',label='Canada')]
        self.dataset=build_index(self.movies,membership,genres,metadata)

    def test_index_can_be_pickled_for_streamlit_cache(self):
        restored = pickle.loads(pickle.dumps(self.dataset))
        movies, platforms, genres, metadata = restored
        self.assertEqual(len(filter_ids(movies, platforms, genres, metadata)), 3)
        self.assertEqual(metadata['language']['2'], set())
        self.assertEqual(metadata['country']['1'], {'United States'})

    def test_missing_metadata_filter_preserves_population(self):
        movies, platforms, genres, metadata = self.dataset
        self.assertEqual(filter_ids(movies, platforms, genres, metadata,
                                    metadata_dimension='language'), ['1', '2', '3'])
        self.assertEqual(filter_ids(movies, platforms, genres, metadata,
                                    metadata_dimension='language', metadata_label='French'), ['1'])

    def test_full_population_and_overlap(self):
        m,p,g,x=self.dataset
        ids=filter_ids(m,p,g,x)
        self.assertEqual(describe_selection(ids,m,p,g)['platform_memberships'],4)
        self.assertEqual(describe_selection(ids,m,p,g)['multi_platform_movies'],1)

    def test_platform_filter_does_not_double_count(self):
        m,p,g,x=self.dataset
        self.assertEqual(filter_ids(m,p,g,x,platform='Netflix'),['1','2'])

    def test_release_era_filter(self):
        m,p,g,x=self.dataset
        self.assertEqual(filter_ids(m,p,g,x,era='before_1950'),['3'])

    def test_multilabel_genre_filter(self):
        m,p,g,x=self.dataset
        self.assertEqual(filter_ids(m,p,g,x,genre='Action'),['1'])

    def test_metadata_dimension_label_filter(self):
        m,p,g,x=self.dataset
        self.assertEqual(filter_ids(m,p,g,x,metadata_dimension='country',metadata_label='Canada'),['2'])

    def test_empty_filter(self):
        m,p,g,x=self.dataset
        metrics=describe_selection(filter_ids(m,p,g,x,genre='Nonexistent'),m,p,g)
        self.assertEqual(metrics['unique_movie_records'],0)
        self.assertIsNone(metrics['imdb_mean_observed'])

    def test_observed_only_denominator(self):
        m,p,g,x=self.dataset
        metrics=describe_selection(['1','2'],m,p,g)
        self.assertEqual(metrics['imdb_observed_n'],1)
        self.assertEqual(metrics['imdb_mean_observed'],7.0)

    def test_invalid_dimension_rejected(self):
        m,p,g,x=self.dataset
        with self.assertRaises(ValueError):
            filter_ids(m,p,g,x,metadata_dimension='continent')

    def test_none_sentinel_rejected(self):
        with self.assertRaises(ValueError):
            build_index(self.movies,[dict(source_id='1',platform='Netflix'),dict(source_id='1',platform='Hulu'),dict(source_id='2',platform='Netflix'),dict(source_id='3',platform='Disney+')],[],[dict(source_id='2',dimension='language',label='None')])

    def test_duplicate_membership_rejected(self):
        with self.assertRaises(ValueError):
            build_index(self.movies,[dict(source_id='1',platform='Netflix'),dict(source_id='1',platform='Netflix')],[],[])

    def test_duplicate_metadata_rejected(self):
        with self.assertRaises(ValueError):
            build_index(self.movies,[dict(source_id='1',platform='Netflix'),dict(source_id='1',platform='Hulu'),dict(source_id='2',platform='Netflix'),dict(source_id='3',platform='Disney+')],[],[dict(source_id='1',dimension='language',label='French')]*2)

    def test_missing_csv_field_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.csv'
            p.write_text('a,b\n1,2\n',encoding='utf-8')
            with self.assertRaises(ValueError):
                csv_rows(p,{'not_present'})


if __name__=='__main__':
    unittest.main()
