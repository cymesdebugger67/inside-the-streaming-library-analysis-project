from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = (
    ("Phase 01", "outputs/source_viability/source_audit.json", None),
    ("Phase 02", "outputs/phase02_preparation/preparation_qa.json", "output_sha256"),
    ("Phase 03", "outputs/phase03_eda/eda_qa.json", "output_hashes"),
    ("Phase 04", "outputs/phase04_comparative/comparative_qa.json", "output_hashes"),
)


def main() -> None:
    for stage, manifest_name, hash_field in STAGES:
        manifest_path = ROOT / manifest_name
        if not manifest_path.is_file():
            raise SystemExit(f"STOP - {stage} manifest missing: {manifest_name}")
        report = json.loads(manifest_path.read_text(encoding="utf-8"))
        if hash_field is None:
            source = ROOT / "data/raw/historical_streaming_movies.csv"
            if not source.is_file():
                raise SystemExit("STOP - Missing historical CSV")
            expected = report["source_sha256"]
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            if actual != expected:
                raise SystemExit("STOP - Phase 01 source hash mismatch")
            count = report["qa"]["source_rows"]
        else:
            files = report[hash_field]
            folder = manifest_path.parent
            for relative, expected in files.items():
                path = folder / relative
                if not path.is_file():
                    raise SystemExit(f"STOP - Missing {stage} output: {relative}")
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != expected:
                    raise SystemExit(f"STOP - {stage} output hash mismatch: {relative}")
            count = len(files)
        print(f"PASS - {stage}: verified {count} {'source records' if hash_field is None else 'outputs'}")
    print("PASS - Local integrity checks completed; scientific and publication review remain separate")


if __name__ == "__main__":
    main()
