"""Final-report input validation and formatting checks."""
import tempfile
import unittest
from pathlib import Path
from streaming_library.final_research import fmt, load_rows


class FinalResearchTests(unittest.TestCase):
    def test_decimal_format(self):
        self.assertEqual(fmt('15.12345',3),'15.123')

    def test_empty_csv_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'empty.csv'
            path.write_text('col\n',encoding='utf-8')
            with self.assertRaises(ValueError):load_rows(path,{'col'})

    def test_missing_columns_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'wrong.csv'
            path.write_text('a\n1\n',encoding='utf-8')
            with self.assertRaises(ValueError):load_rows(path,{'b'})

    def test_malformed_row_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad.csv'
            path.write_text('a,b\n1\n',encoding='utf-8')
            with self.assertRaises(ValueError):load_rows(path,{'a','b'})


if __name__=='__main__':unittest.main()
