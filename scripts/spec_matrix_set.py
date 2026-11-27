"""Update one or more matrix rows: python scripts/spec_matrix_set.py "<text in item>=<status>=<note>" ... then re-render."""

from __future__ import annotations

import sys
from pathlib import Path

import spec_matrix

TSV = Path(__file__).resolve().parent / "spec_matrix.tsv"


def main(updates: list[str]) -> None:
    lines = TSV.read_text(encoding="utf-8").splitlines()
    for update in updates:
        needle, status, note = update.split("=", 2)
        hits = [i for i, line in enumerate(lines) if not line.startswith("#") and needle in line.split("\t")[2]]
        if len(hits) != 1 or status not in spec_matrix.NAMES:
            raise SystemExit(f"{needle!r}: {len(hits)} satır eşleşti, durum {status!r}")
        cells = (lines[hits[0]].split("\t") + [""] * 5)[:5]
        lines[hits[0]] = "\t".join([*cells[:3], status, note])
    TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec_matrix.main()


if __name__ == "__main__":
    main(sys.argv[1:])
