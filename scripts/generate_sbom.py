"""OPS-13: CycloneDX JSON SBOM Generator & License Compliance Checker (flags GPL/AGPL dependencies)."""

from __future__ import annotations

import importlib.metadata as md
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESTRICTED_LICENSES = ("AGPL", "GPL-3", "GPL-2")


def generate_cyclonedx_sbom(output_path: Path | None = None) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    license_warnings: list[dict[str, str]] = []
    for dist in sorted(md.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
        name = str(dist.metadata.get("Name") or "")
        version = str(dist.version or "")
        lic = str(dist.metadata.get("License") or "UNKNOWN").splitlines()[0][:80]
        if not name:
            continue
        components.append({"type": "library", "name": name, "version": version, "licenses": [{"license": {"name": lic}}]})
        if any(r in lic.upper() for r in RESTRICTED_LICENSES):
            license_warnings.append({"package": name, "version": version, "license": lic})

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"timestamp": datetime.now(UTC).isoformat(), "component": {"name": "distributed-ai-dev-platform", "type": "application"}},
        "components": components,
        "license_warnings": license_warnings,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(sbom, ensure_ascii=False, indent=2), encoding="utf-8")
    return sbom


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "security" / "sbom.cdx.json",
    )
    args = parser.parse_args()
    res = generate_cyclonedx_sbom(args.output)
    print(f"SBOM written: {args.output} ({len(res['components'])} components, {len(res['license_warnings'])} GPL/AGPL warnings)")
