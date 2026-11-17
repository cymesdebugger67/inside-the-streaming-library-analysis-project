import unittest
from streaming_library.metadata_analytics import build, extract_tokens


def fixture():
    movies=[dict(source_id='1',platform_count='2',country_raw='United States,United Kingdom',language_raw='English,French'),
            dict(source_id='2',platform_count='1',country_raw='',language_raw='English'),
            dict(source_id='3',platform_count='1',country_raw='France',language_raw='')]
    memberships=[dict(source_id=i,platform=p) for i,p in [('1','Netflix'),('1','Hulu'),('2','Netflix'),('3','Prime Video')]]
    genres=[dict(source_id='1',genre='Drama'),dict(source_id='2',genre='Comedy')]
    return movies,memberships,genres


class MetadataTests(unittest.TestCase):
    def test_tokens_trim_and_deduplicate(self):
        self.assertEqual(extract_tokens(' English , english , French '),(['English','French'],True))
    def test_empty_metadata(self):
        self.assertEqual(extract_tokens('  '),([],False))
    def test_embedded_empty_rejected(self):
        with self.assertRaises(ValueError):extract_tokens('English,,French')
    def test_basic_tables(self):
        t=build(*fixture())
        self.assertEqual(len(t['metadata_assignments']),6)
        self.assertEqual(len(t['metadata_platform_coverage']),8)
        self.assertEqual(len(t['catalogue_contributions']),4)
    def test_exclusive_reconciliation(self):
        t=build(*fixture())
        d={r['platform']:r for r in t['catalogue_contributions']}
        self.assertEqual(int(d['Netflix']['exclusive_movies']),1)
        self.assertEqual(int(d['Hulu']['exclusive_movies']),0)
        self.assertEqual(int(d['Prime Video']['exclusive_movies']),1)
        self.assertEqual(sum(int(r['exclusive_movies']) for r in d.values()),2)
    def test_known_denominator(self):
        t=build(*fixture())
        r=next(r for r in t['metadata_platform_coverage'] if r['platform']=='Netflix' and r['dimension']=='country')
        self.assertEqual((int(r['known_n']),int(r['missing_n'])),(1,1))
        self.assertEqual(float(r['known_pct']),50)
    def test_reject_orphan(self):
        m,p,g=fixture();p.append(dict(source_id='99',platform='Netflix'))
        with self.assertRaises(ValueError):build(m,p,g)
    def test_reject_duplicate_membership(self):
        m,p,g=fixture();p.append(dict(p[0]))
        with self.assertRaises(ValueError):build(m,p,g)
    def test_reject_platform_count(self):
        m,p,g=fixture();m[0]['platform_count']='1'
        with self.assertRaises(ValueError):build(m,p,g)
    def test_reject_duplicate_id(self):
        m,p,g=fixture();m.append(dict(m[0]))
        with self.assertRaises(ValueError):build(m,p,g)
    def test_reject_duplicate_genre(self):
        m,p,g=fixture();g.append(dict(g[0]))
        with self.assertRaises(ValueError):build(m,p,g)
    def test_none_only_not_counted_as_named_language(self):
        m,p,g=fixture()
        m[1]['language_raw']='None'
        t=build(m,p,g)
        lang=[r for r in t['metadata_assignments'] if r['dimension']=='language']
        self.assertFalse(any(r['label'].casefold() == 'none' for r in lang))
        row=next(r for r in t['metadata_source_quality'] if r['dimension']=='language')
        self.assertEqual((row['known_movies'],row['none_sentinel_only_movies']), (1,1))
        cov=next(r for r in t['metadata_platform_coverage'] if r['platform']=='Netflix' and r['dimension']=='language')
        self.assertEqual((cov['known_n'],cov['none_sentinel_movies']), (1,1))

    def test_none_mixed_preserves_named_language(self):
        m,p,g=fixture()
        m[0]['language_raw']='None,French'
        t=build(m,p,g)
        lang=[r['label'] for r in t['metadata_assignments'] if r['dimension']=='language' and r['source_id']=='1']
        self.assertEqual(lang,['French'])
        row=next(r for r in t['metadata_source_quality'] if r['dimension']=='language')
        self.assertEqual(row['none_sentinel_with_named_language_movies'],1)

    def test_case_insensitive_none_and_country_none_preserved(self):
        m,p,g=fixture()
        m[0]['language_raw']='nOnE,English'
        m[0]['country_raw']='None,France'
        t=build(m,p,g)
        self.assertNotIn('nOnE',[r['label'] for r in t['metadata_assignments'] if r['dimension']=='language'])
        self.assertIn('None',[r['label'] for r in t['metadata_assignments'] if r['dimension']=='country'])

    def test_case_variants_preserved_consistently(self):
        m,p,g=fixture();m[1]['language_raw']='english'
        t=build(m,p,g)
        lang=[r['label'] for r in t['metadata_assignments'] if r['dimension']=='language']
        self.assertEqual(lang.count('English'),2)


if __name__=='__main__':unittest.main()
