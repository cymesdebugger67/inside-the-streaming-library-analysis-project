"""Independent analytical properties of exact catalogue attribution."""
import math
import unittest
from streaming_library.phase07_methods import (incidence, exact_coalitions, exact_shapley,
                                                diversity, genre_sensitivity, equal_size_sensitivity)


def fixture():
    m=[{'source_id':str(i),'platform_count':str(n)} for i,n in [(1,2),(2,1),(3,1),(4,1)]]
    p=[{'source_id':a,'platform':b} for a,b in [('1','Netflix'),('1','Hulu'),('2','Netflix'),
                                                ('3','Prime Video'),('4','Disney+')]]
    g=[{'source_id':a,'genre':b} for a,b in [('1','Action'),('1','Drama'),('2','Drama'),
                                             ('3','Comedy'),('4','Comedy')]]
    return m,p,g


class Phase07MethodsTests(unittest.TestCase):
    def test_coalition_count_and_union(self):
        groups,by_id,genres=incidence(*fixture())
        sets,rows=exact_coalitions(groups)
        self.assertEqual(len(rows),16)
        self.assertEqual(rows[0]['unique_movies'],0)
        self.assertEqual(rows[-1]['unique_movies'],4)

    def test_shapley_efficiency_and_shared_fractions(self):
        groups,by_id,genres=incidence(*fixture())
        subsets,rows=exact_shapley(groups,by_id)
        alloc={r['platform']:float(r['shapley_allocated_movies']) for r in rows}
        self.assertEqual(alloc,{'Netflix':1.5,'Hulu':0.5,'Prime Video':1.0,'Disney+':1.0})
        self.assertAlmostEqual(sum(alloc.values()),4)
        self.assertEqual({r['platform']:r['exclusive_movies'] for r in rows},
                         {'Netflix':1,'Hulu':0,'Prime Video':1,'Disney+':1})

    def test_all_shared_fair_shares(self):
        m=[{'source_id':'A','platform_count':'4'}]
        p=[{'source_id':'A','platform':q} for q in ('Netflix','Hulu','Prime Video','Disney+')]
        groups,by_id,_=incidence(m,p,[])
        _,rows=exact_shapley(groups,by_id)
        self.assertTrue(all(float(r['shapley_allocated_movies'])==0.25 for r in rows))

    def test_equal_tag_diversity(self):
        group={'a','b'}
        tags={'a':{'Drama'},'b':{'Comedy'}}
        d=diversity(group,tags,'fractional_movie')
        self.assertAlmostEqual(float(d['effective_genres_shannon']),2)
        self.assertAlmostEqual(float(d['effective_genres_simpson']),2)

    def test_full_tag_vs_fractional_differ(self):
        tags={'a':{'Action','Drama'},'b':{'Drama'}}
        fraction=diversity({'a','b'},tags,'fractional_movie')
        full=diversity({'a','b'},tags,'full_tag')
        self.assertNotEqual(fraction['effective_genres_shannon'],full['effective_genres_shannon'])

    def test_no_genre_rows(self):
        d=diversity(['a'],{'a':set()},'fractional_movie')
        self.assertEqual(d['effective_genres_shannon'],'')
        self.assertEqual(d['known_genre_movies'],0)

    def test_repeatable_resampling(self):
        groups,by_id,genres=incidence(*fixture())
        a=equal_size_sensitivity(groups,genres,draws=3,seed=7)
        b=equal_size_sensitivity(groups,genres,draws=3,seed=7)
        self.assertEqual(a,b)
        self.assertEqual(len(a),12)
        self.assertTrue(all(row['sample_size']==1 for row in a))

    def test_invalid_membership_rejected(self):
        m,p,g=fixture()
        p.append(dict(p[0]))
        with self.assertRaises(ValueError):incidence(m,p,g)

    def test_invalid_movie_count_rejected(self):
        m,p,g=fixture();m[0]['platform_count']='1'
        with self.assertRaises(ValueError):incidence(m,p,g)

    def test_invalid_genre_rejected(self):
        m,p,g=fixture();g.append(dict(g[0]))
        with self.assertRaises(ValueError):incidence(m,p,g)

    def test_no_movie_without_membership(self):
        m,p,g=fixture();p=[row for row in p if row['source_id']!='4']
        with self.assertRaises(ValueError):incidence(m,p,g)

    def test_bad_allocation_method(self):
        with self.assertRaises(ValueError):diversity([],{ },'unknown')


if __name__=='__main__':unittest.main()
