import unittest
from streaming_library.comparative import build, era, decimal


def fixture():
    movies=[]
    for i,(year,imdb,rt,run,count) in enumerate([(1940,'8','80','90',2),(2010,'','','',1),(2002,'6','', '100',1)],1):
        movies.append(dict(source_id=str(i),release_year=str(year),imdb_rating=imdb,rotten_tomatoes_percent=rt,runtime_minutes=run,platform_count=str(count)))
    membership=[dict(source_id=a,platform=b) for a,b in [('1','Netflix'),('1','Hulu'),('2','Netflix'),('3','Prime Video')]]
    genres=[dict(source_id=a,genre=b) for a,b in [('1','Action'),('1','Drama'),('2','Action'),('3','Comedy')]]
    return movies,membership,genres


class ComparativeTests(unittest.TestCase):
    def test_era(self):
        self.assertEqual(era(1949),'before_1950')
        self.assertEqual(era(2010),'2010_2020')
    def test_decimal(self):
        self.assertIsNone(decimal('',0,10))
        with self.assertRaises(ValueError): decimal('11',0,10)
    def test_build_rows(self):
        out=build(*fixture())
        self.assertEqual(len(out['overlap_asymmetry']),6)
        self.assertEqual(len(out['era_metric_coverage']),60)
        self.assertEqual(len(out['platform_completeness']),12)
    def test_overlap_asymmetry(self):
        out=build(*fixture())
        x=next(r for r in out['overlap_asymmetry'] if r['platform_a']=='Netflix' and r['platform_b']=='Hulu')
        self.assertEqual(x['shared'],1)
        self.assertEqual(float(x['share_a_pct']),50)
        self.assertEqual(float(x['share_b_pct']),100)
    def test_fractional_diversity(self):
        out=build(*fixture())
        netflix=next(x for x in out['genre_diversity'] if x['platform']=='Netflix')
        self.assertEqual(netflix['assignment_count'],3)
        self.assertAlmostEqual(float(netflix['effective_genres_simpson']),1.6,places=6)
    def test_era_reconciliation(self):
        out=build(*fixture())
        rows=[r for r in out['era_metric_coverage'] if r['platform']=='Netflix' and r['metric']=='imdb']
        self.assertEqual(sum(r['all_n'] for r in rows),2)
        self.assertEqual(sum(r['observed_n'] for r in rows),1)
    def test_reject_orphan(self):
        m,mem,g=fixture()
        mem.append({'source_id':'999','platform':'Disney+'})
        with self.assertRaises(ValueError):build(m,mem,g)
    def test_reject_duplicate_membership(self):
        m,mem,g=fixture();mem.append(dict(mem[0]))
        with self.assertRaises(ValueError):build(m,mem,g)
    def test_reject_prepared_count_mismatch(self):
        m,mem,g=fixture();m[0]['platform_count']='1'
        with self.assertRaises(ValueError):build(m,mem,g)
    def test_reject_bad_numeric(self):
        m,mem,g=fixture();m[0]['runtime_minutes']='1256'
        with self.assertRaises(ValueError):build(m,mem,g)

if __name__=='__main__':unittest.main()
