"""Cluster B (`[M34]`, Faz 9.2): Desktop File & Directory Classifier and Organizer.

Provides:
- `classify_and_organize_directory(target_dir: Path, dry_run: bool = True) -> dict`:
  scans files in `target_dir`, classifies them by category (`documents`, `drawings_cad`,
  `spreadsheets_data`, `code`, `images_media`, `archives`), computes size breakdown,
  and (when `dry_run=False`) moves them into category subfolders.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".ppt", ".pptx"},
    "drawings_cad": {".dxf", ".dwg", ".step", ".stp", ".iges", ".igs", ".stl", ".obj", ".fcstd"},
    "spreadsheets_data": {".csv", ".tsv", ".xls", ".xlsx", ".json", ".parquet", ".db", ".sqlite", ".xml"},
    "code": {".py", ".js", ".ts", ".html", ".css", ".sql", ".sh", ".ps1", ".c", ".cpp", ".h", ".java", ".go", ".rs"},
    "images_media": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".mp3", ".wav", ".mp4", ".avi", ".mkv"},
    "archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"},
}


def classify_file_extension(path: Path) -> str:
    ext = path.suffix.lower()
    for category, exts in CATEGORY_EXTENSIONS.items():
        if ext in exts:
            return category
    return "documents"


def classify_and_organize_directory(target_dir: Path, dry_run: bool = True) -> dict[str, Any]:
    """Scan files in `target_dir`, classify by category, compute size breakdown, and optionally move into category subfolders."""
    target_dir = Path(target_dir).resolve()
    categories: dict[str, list[dict[str, Any]]] = {cat: [] for cat in CATEGORY_EXTENSIONS}
    size_breakdown_bytes: dict[str, int] = {cat: 0 for cat in CATEGORY_EXTENSIONS}
    moved_files: list[dict[str, str]] = []

    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "target_dir": str(target_dir),
            "dry_run": dry_run,
            "total_files": 0,
            "total_size_bytes": 0,
            "categories": categories,
            "size_breakdown_bytes": size_breakdown_bytes,
            "moved_files": moved_files,
        }

    for entry in sorted(target_dir.iterdir()):
        if not entry.is_file():
            continue
        cat = classify_file_extension(entry)
        size = entry.stat().st_size
        dest_dir = target_dir / cat
        dest_path = dest_dir / entry.name

        file_record = {
            "name": entry.name,
            "category": cat,
            "size_bytes": size,
            "source_path": str(entry),
            "target_path": str(dest_path),
        }
        categories[cat].append(file_record)
        size_breakdown_bytes[cat] += size

        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if dest_path.exists():
                dest_path = dest_dir / f"{entry.stem}_copy{entry.suffix}"
            shutil.move(str(entry), str(dest_path))
            moved_files.append(
                {
                    "name": entry.name,
                    "category": cat,
                    "from": str(entry),
                    "to": str(dest_path),
                }
            )

    total_files = sum(len(items) for items in categories.values())
    total_size = sum(size_breakdown_bytes.values())

    return {
        "target_dir": str(target_dir),
        "dry_run": dry_run,
        "total_files": total_files,
        "total_size_bytes": total_size,
        "categories": categories,
        "size_breakdown_bytes": size_breakdown_bytes,
        "moved_files": moved_files,
    }
