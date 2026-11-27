"""Render scripts/spec_matrix.tsv (one row per specification item) into docs/sartname-madde-listesi.md."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"C": "canlı", "T": "test", "K": "kısmi", "Y": "yok", "X": "dışarıda", "E": "teknik engel"}


def rows(text: str) -> list[list[str]]:
    out = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        cells = line.split("\t")
        cells += [""] * (5 - len(cells))
        if cells[3] in NAMES:
            out.append(cells[:5])
    return out


def render(items: list[list[str]]) -> str:
    versions = sorted({r[0] for r in items})
    lines = [
        "# v1-v4 şartnameleri: madde madde durum",
        "",
        "**canlı** = gerçek modellerle denendi ve geçti. **test** = otomatik testle geçti. **kısmi** = bir bölümü var.",
        "**yok** = henüz yazılmadı. **dışarıda** = senin onayınla kapsam dışı. **teknik engel** = bu araçlarla yapılamıyor.",
        "",
        "Bu dosya `scripts/spec_matrix.tsv` dosyasından üretilir: `python scripts/spec_matrix.py`",
        "",
        "| Sürüm | " + " | ".join(NAMES.values()) + " | Toplam |",
        "|" + "---|" * (len(NAMES) + 2),
    ]
    for v in versions:
        count = Counter(r[3] for r in items if r[0] == v)
        lines.append(f"| {v} | " + " | ".join(str(count[k]) for k in NAMES) + f" | {sum(count.values())} |")
    total = Counter(r[3] for r in items)
    lines.append("| **Hepsi** | " + " | ".join(str(total[k]) for k in NAMES) + f" | {len(items)} |")
    for v in versions:
        lines += ["", f"## {v}", "", "| Bölüm | Madde | Durum | Not |", "|---|---|---|---|"]
        lines += [f"| {r[1]} | {r[2]} | {NAMES[r[3]]} | {r[4]} |" for r in items if r[0] == v]
    return "\n".join(lines) + "\n"


def main() -> None:
    items = rows((ROOT / "scripts" / "spec_matrix.tsv").read_text(encoding="utf-8"))
    (ROOT / "docs" / "sartname-madde-listesi.md").write_text(render(items), encoding="utf-8")
    print(dict(Counter(r[3] for r in items)), len(items))


if __name__ == "__main__":
    main()
