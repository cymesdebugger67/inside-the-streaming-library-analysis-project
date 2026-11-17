import csv
import tempfile
import unittest
from pathlib import Path

from streaming_library.source_audit import REQUIRED_COLUMNS, audit_csv, create_report, normalized_key, parse_optional_numeric


class SourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "sample.csv"

    def tearDown(self):
        self.temp.cleanup()

    def write_rows(self, rows, fields=REQUIRED_COLUMNS):
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def record(self, **overrides):
        row = dict.fromkeys(REQUIRED_COLUMNS, "")
        row.update({"ID": "1", "Title": "Film One", "Year": "2020", "Netflix": "1", "Hulu": "0", "Prime Video": "0", "Disney+": "0", "Type": "0", "Genres": "Drama,Action", "IMDb": "7.2", "Rotten Tomatoes": "80%", "Runtime": "120"})
        row.update(overrides)
        return row

    def test_basic_audit_and_report(self):
        self.write_rows([self.record(), self.record(ID="2", Title="Film Two", Netflix="1", Hulu="1", Genres="Comedy")])
        report = audit_csv(self.path, min_rows=2)
        self.assertEqual(report["qa"]["source_rows"], 2)
        self.assertEqual(report["qa"]["platform_counts"]["Netflix"], 2)
        self.assertEqual(report["qa"]["platform_counts"]["Hulu"], 1)
        self.assertEqual(report["qa"]["multi_platform_source_rows"], 1)
        self.assertEqual(report["qa"]["genre_tag_assignments"], 3)
        self.assertIn("Phase 01", create_report(report))

    def test_duplicate_detection_is_normalized(self):
        self.write_rows([self.record(), self.record(ID="2", Title=" FILM--ONE ")])
        report = audit_csv(self.path, min_rows=2)
        self.assertEqual(report["qa"]["duplicate_title_year_groups"], 1)
        self.assertEqual(report["qa"]["duplicate_title_year_excess_rows"], 1)

    def test_invalid_binary_flag_rejected(self):
        self.write_rows([self.record(Hulu="yes")])
        with self.assertRaisesRegex(ValueError, "Nonbinary"):
            audit_csv(self.path, min_rows=1)

    def test_missing_required_column_rejected(self):
        fields = tuple(field for field in REQUIRED_COLUMNS if field != "Genres")
        self.write_rows([{key: val for key, val in self.record().items() if key in fields}], fields=fields)
        with self.assertRaisesRegex(ValueError, "missing: Genres"):
            audit_csv(self.path, min_rows=1)

    def test_too_small_rejected(self):
        self.write_rows([self.record()])
        with self.assertRaisesRegex(ValueError, "below required"):
            audit_csv(self.path, min_rows=2)

    def test_all_zero_membership_rejected(self):
        self.write_rows([self.record(Netflix="0")])
        with self.assertRaisesRegex(ValueError, "no named platform"):
            audit_csv(self.path, min_rows=1)

    def test_empty_title_rejected(self):
        self.write_rows([self.record(Title="")])
        with self.assertRaisesRegex(ValueError, "Essential title/year"):
            audit_csv(self.path, min_rows=1)

    def test_age_and_rating_missingness_is_preserved(self):
        self.write_rows([self.record(Year="1997", IMDb="", **{"Rotten Tomatoes": ""})])
        report = audit_csv(self.path, min_rows=1)
        self.assertEqual(report["qa"]["missing_fields"]["IMDb"], 1)
        self.assertEqual(report["qa"]["release_year_min"], 1997)

    def test_optional_numeric_parsing(self):
        self.assertEqual(parse_optional_numeric("89%", 0, 100, "%"), 89)
        self.assertIsNone(parse_optional_numeric("x%", 0, 100, "%"))
        self.assertIsNone(parse_optional_numeric("inf", 0, 100))

    def test_unicode_title_key(self):
        self.assertEqual(normalized_key("FİLM – One", "2020"), normalized_key("fi̇lm one", "2020"))


if __name__ == "__main__":
    unittest.main()
