import csv
import json
import math
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from streaming_library.advanced_analysis import ERAS, analyse, era, measure, run
from streaming_library.integrated import load_project, sha256


class AdvancedAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[1]
        if not (cls.root/'outputs/phase02_preparation/preparation_qa.json').is_file():
            raise unittest.SkipTest('Verified historical source outputs unavailable')
        cls.movies,cls.memberships,cls.genres,cls.metadata=load_project(cls.root)
        cls.tables=analyse(cls.movies,cls.memberships,cls.genres,cls.metadata)

    def test_era_buckets(self):
        self.assertEqual([era(y) for y in [1902,1950,1980,2000,2010,2020]],
                         list(ERAS)[0:1]+list(ERAS)[1:2]+list(ERAS)[2:3]+list(ERAS)[3:4]+list(ERAS)[4:5]+list(ERAS)[4:5])
        with self.assertRaises(ValueError):era(2021)

    def test_observed_denominators(self):
        result=measure([{'value':'6.0'},{'value':''},{'value':'8.0'}],'value')
        self.assertEqual(result['observed_n'],2)
        self.assertAlmostEqual(result['coverage_pct'],66.6667)
        self.assertEqual(result['observed_mean'],7)
        self.assertEqual(result['observed_median'],7)

    def test_release_era_membership_reconciles(self):
        totals=defaultdict(int)
        for r in self.tables['release_era_profile']:
            totals[r['platform']]+=r['movie_count']
        self.assertEqual(dict(totals),{'Netflix':3560,'Hulu':903,'Prime Video':12354,'Disney+':564})

    def test_metadata_coverage_bounds(self):
        for r in self.tables['metadata_coverage_by_era']:
            self.assertLessEqual(r['observed_n'],r['denominator'])
            self.assertGreaterEqual(r['coverage_pct'],0)
            self.assertLessEqual(r['coverage_pct'],100)

    def test_score_rows_are_observed_only(self):
        for r in self.tables['observed_scores_by_era']:
            self.assertLessEqual(r['observed_n'],r['denominator'])
            if r['observed_n'] == 0:
                self.assertEqual(r['observed_mean'],'')

    def test_genre_specialization_denominator(self):
        for r in self.tables['genre_specialization']:
            self.assertLessEqual(r['movie_count'],r['platform_memberships'])
            self.assertGreaterEqual(r['prevalence_ratio_vs_union'],0)
            self.assertLessEqual(r['union_movie_count'],16744)

    def test_overlap_directionality(self):
        self.assertEqual(len(self.tables['overlap_asymmetry']),6)
        for r in self.tables['overlap_asymmetry']:
            self.assertLessEqual(r['shared_movies'],min(r['a_movies'],r['b_movies']))
            self.assertAlmostEqual(r['a_shared_pct'],100*r['shared_movies']/r['a_movies'],places=4)
            self.assertAlmostEqual(r['b_shared_pct'],100*r['shared_movies']/r['b_movies'],places=4)

    def test_membership_multiplicity(self):
        data=self.tables['membership_multiplicity']
        self.assertEqual(sum(r['movie_count'] for r in data),16744)
        self.assertEqual(sum(r['movie_count']*r['platform_count'] for r in data),17381)
        self.assertEqual(next(r['movie_count'] for r in data if r['platform_count']==1),16117)

    def test_age_classification_totals(self):
        totals=defaultdict(int)
        for r in self.tables['age_classification_profile']:
            totals[r['platform']]+=r['movie_count']
        self.assertEqual(dict(totals),{'Netflix':3560,'Hulu':903,'Prime Video':12354,'Disney+':564})

    def test_standardization(self):
        self.assertEqual(len(self.tables['imdb_era_standardization']),4)
        for r in self.tables['imdb_era_standardization']:
            self.assertTrue(0 <= r['raw_observed_mean'] <= 10)
            self.assertTrue(0 <= r['era_standardized_observed_mean'] <= 10)
            self.assertAlmostEqual(r['era_standardized_observed_mean']-r['raw_observed_mean'],r['difference_standard_minus_raw'],places=4)

    def test_full_generation_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'advanced'
            manifest=run(self.root,out)
            self.assertEqual(manifest['figure_count'],6)
            self.assertEqual(len(manifest['table_rows']),8)
            self.assertEqual(manifest['source_population'],16744)
            for name,checksum in manifest['output_sha256'].items():
                self.assertEqual(sha256(out/name),checksum)
            with self.assertRaises(ValueError):run(self.root,out)


if __name__ == '__main__':
    unittest.main()
