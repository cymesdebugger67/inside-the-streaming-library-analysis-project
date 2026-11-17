import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from streaming_library.preparation import (
    PLATFORMS, REQUIRED, normalized_identity, parse_optional_number,
    parse_runtime, prepare, split_genres,
)


class PreparationTests(unittest.TestCase):
    def test_identity_normalizes_case_and_whitespace(self):
        self.assertEqual(normalized_identity(" A   Film ", "2020"), ("a film", "2020"))

    def test_imdb_rating(self):
        self.assertEqual(parse_optional_number("7.8/10", denominator=10, maximum=10), ("7.8", "valid"))
        self.assertEqual(parse_optional_number("11/10", denominator=10, maximum=10)[1], "invalid")
        self.assertEqual(parse_optional_number("" , denominator=10, maximum=10)[1], "missing")

    def test_rotten_tomatoes_rating(self):
        self.assertEqual(parse_optional_number("91/100"), ("91", "valid"))
        self.assertEqual(parse_optional_number("91%"), ("91", "valid"))
        self.assertEqual(parse_optional_number("bad")[1], "invalid")

    def test_runtime(self):
        self.assertEqual(parse_runtime("125 min"), ("125", "valid"))
        self.assertEqual(parse_runtime("unknown")[1], "invalid")
        self.assertEqual(parse_runtime("")[1], "missing")

    def test_genres_preserve_multi_label_and_deduplicate(self):
        self.assertEqual(split_genres("Action, Drama, action, Comedy"), (["Action", "Drama", "Comedy"], True))

    def _fixture(self, root):
        root = Path(root)
        data = root / "data.csv"
        manifest = root / "audit.json"
        records = [
            {"ID": "1", "Title": "First Film", "Year": "2010", "Age": "", "IMDb": "7.5/10", "Rotten Tomatoes": "88/100", "Netflix": "1", "Hulu": "0", "Prime Video": "1", "Disney+": "0", "Type": "0", "Directors": "One", "Genres": "Drama, Action", "Country": "US", "Language": "English", "Runtime": "95"},
            {"ID": "2", "Title": "Second Film", "Year": "2019", "Age": "13+", "IMDb": "", "Rotten Tomatoes": "", "Netflix": "0", "Hulu": "1", "Prime Video": "0", "Disney+": "0", "Type": "0", "Directors": "", "Genres": "Comedy", "Country": "", "Language": "", "Runtime": "unknown"},
        ]
        with data.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=REQUIRED)
            writer.writeheader()
            writer.writerows(records)
        raw = data.read_bytes()
        missing = {field: sum(not r[field].strip() for r in records) for field in REQUIRED}
        audit = {"status": "viable_with_historical_source_limitations", "source_sha256": hashlib.sha256(raw).hexdigest(), "qa": {
            "source_rows": 2, "unique_title_year_keys": 2, "duplicate_title_year_groups": 0,
            "platform_flags_total": 3, "platform_counts": {"Netflix": 1, "Hulu": 1, "Prime Video": 1, "Disney+": 0},
            "membership_patterns": {"1010": 1, "0100": 1}, "multi_platform_source_rows": 1,
            "missing_fields": missing,
        }}
        manifest.write_text(json.dumps(audit), encoding="utf-8")
        return data, manifest

    def test_fixture_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            data, manifest = self._fixture(directory)
            target = Path(directory) / "out"
            report = prepare(data, manifest, target)
            self.assertEqual(report["movie_rows"], 2)
            self.assertEqual(report["platform_membership_rows"], 3)
            self.assertEqual(report["genre_assignment_rows"], 3)
            self.assertEqual(report["optional_parsing"]["Runtime"]["invalid"], 1)
            with (target / "movies_clean.csv").open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 2)
            with (target / "platform_memberships.csv").open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 3)

    def test_reject_hash_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            data, manifest = self._fixture(directory)
            data.write_bytes(data.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Source hash differs"):
                prepare(data, manifest, Path(directory) / "out")

    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            data, manifest = self._fixture(directory)
            target = Path(directory) / "out"
            target.mkdir()
            with self.assertRaisesRegex(ValueError, "refuse to overwrite"):
                prepare(data, manifest, target)

    def test_reject_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            data, manifest = self._fixture(directory)
            with data.open(newline="", encoding="utf-8") as stream:
                records = list(csv.DictReader(stream))
            records[1]["ID"] = records[0]["ID"]
            with data.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=REQUIRED)
                writer.writeheader()
                writer.writerows(records)
            audit = json.loads(manifest.read_text(encoding="utf-8"))
            audit["source_sha256"] = hashlib.sha256(data.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Repeated source ID"):
                prepare(data, manifest, Path(directory) / "out")


if __name__ == "__main__":
    unittest.main()
