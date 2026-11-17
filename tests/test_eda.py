import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from streaming_library.eda import analyze, make_outputs, runtime_band, era


class TestHistoricalEDA(unittest.TestCase):
    def setUp(self):
        self.qa = {"movie_rows": 3, "platform_membership_rows": 4,
                   "genre_assignment_rows": 4, "multi_platform_movies": 1,
                   "platform_counts": {"Netflix": 2, "Hulu": 1, "Prime Video": 1, "Disney+": 0}}
        def movie(mid, year, count, imdb, rt, runtime):
            return dict(source_id=mid, release_year=str(year), platform_count=str(count),
                has_multiple_platforms=str(int(count > 1)), imdb_rating=imdb,
                rotten_tomatoes_percent=rt, runtime_minutes=runtime,
                has_imdb_rating=str(int(bool(imdb))), has_rotten_tomatoes_rating=str(int(bool(rt))),
                has_runtime=str(int(bool(runtime))))
        self.movies = [movie("1", 2010, 2, "8.8", "87", "148"),
                       movie("2", 1999, 1, "", "", ""),
                       movie("3", 2020, 1, "7.2", "", "89")]
        self.memberships = [dict(source_id="1", platform="Netflix"),dict(source_id="1", platform="Hulu"),
                            dict(source_id="2", platform="Netflix"),dict(source_id="3", platform="Prime Video")]
        self.genres = [dict(source_id="1", genre="Action"),dict(source_id="1", genre="Sci-Fi"),
                       dict(source_id="2", genre="Action"),dict(source_id="3", genre="Drama")]

    def test_feature_engineering(self):
        table = make_outputs(self.movies, self.memberships, self.genres, self.qa)
        one = table["movie_features"][0]
        self.assertEqual(one["release_decade"], 2010)
        self.assertEqual(one["genre_count"], 2)
        self.assertEqual(one["rating_coverage"], "both")
        self.assertEqual(table["movie_features"][1]["runtime_band"], "missing_invalid")

    def test_overlap_exact(self):
        rows = make_outputs(self.movies, self.memberships, self.genres, self.qa)["overlap"]
        pair = next(r for r in rows if r["platform_a"] == "Netflix" and r["platform_b"] == "Hulu")
        self.assertEqual(pair["shared_movies"], 1)
        self.assertEqual(pair["union_movies"], 2)
        self.assertEqual(pair["jaccard_pct"], "50.000000")

    def test_nonexclusive_genre(self):
        tables = make_outputs(self.movies, self.memberships, self.genres, self.qa)
        counts = [r for r in tables["genre_platform"] if r["platform"] == "Netflix"]
        self.assertEqual(sum(r["movies"] for r in counts), 3)

    def test_empty_platform_handling(self):
        tables = make_outputs(self.movies, self.memberships, self.genres, self.qa)
        self.assertEqual(tables["platform_summary"][3]["movie_count"], 0)
        self.assertEqual(tables["platform_summary"][3]["imdb_coverage_pct"], "")

    def test_reject_duplicate_membership(self):
        with self.assertRaisesRegex(ValueError, "duplicate membership"):
            make_outputs(self.movies, self.memberships + [self.memberships[0]], self.genres, self.qa)

    def test_reject_unknown_genre_movie(self):
        with self.assertRaisesRegex(ValueError, "Orphan"):
            make_outputs(self.movies, self.memberships, self.genres + [dict(source_id="unknown", genre="Comedy")], self.qa)

    def test_runtime_bands(self):
        self.assertEqual(runtime_band(None), "missing_invalid")
        self.assertEqual(runtime_band(60), "60_89")
        self.assertEqual(runtime_band(150), "150_plus")

    def test_release_era(self):
        self.assertEqual(era(1940), "pre_1950")
        self.assertEqual(era(2010), "2010_plus")

    def test_hash_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            prepared = base / "p"
            prepared.mkdir()
            data = {"movies_clean.csv": self.movies, "platform_memberships.csv": self.memberships,
                    "movie_genres.csv": self.genres}
            hashes = {}
            for name, rows in data.items():
                path = prepared / name
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            qa = dict(self.qa, status="prepared_with_historical_source_limitations", output_sha256=hashes)
            (prepared / "preparation_qa.json").write_text(json.dumps(qa), encoding="utf-8")
            report = analyze(prepared, base / "eda", figures=False)
            self.assertEqual(report["records"], 3)
            self.assertEqual(len(report["table_rows"]), 7)
            with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                analyze(prepared, base / "eda", figures=False)
            with (prepared / "movies_clean.csv").open("a", encoding="utf-8") as stream:
                stream.write("tamper\n")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                analyze(prepared, base / "another", figures=False)


if __name__ == "__main__":
    unittest.main()
