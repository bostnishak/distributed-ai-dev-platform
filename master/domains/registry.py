"""DOM-12: Zero-Code Declarative Domain Onboarding Framework (YAML specs + schema validator)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SPECS_DIR = Path(__file__).resolve().parent / "specs"
REQUIRED_DOMAIN_KEYS = ("id", "name", "version", "risk_level", "intents", "knowledge_collections", "tools", "output_contract", "disclaimer", "eval_questions")


def validate_domain_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """DOM-12: Validate a YAML domain definition without touching Python code."""
    missing = [k for k in REQUIRED_DOMAIN_KEYS if k not in spec or spec[k] in (None, "", [])]
    eval_qs = spec.get("eval_questions") or []
    errors: list[str] = []
    if missing:
        errors.append(f"Eksik zorunlu alanlar: {', '.join(missing)}")
    if spec.get("risk_level") not in {"low", "medium", "high"}:
        errors.append("risk_level yalnız low/medium/high olabilir.")
    if len(eval_qs) < 20:
        errors.append(f"Alan eval seti en az 20 soru içermelidir (mevcut: {len(eval_qs)}).")
    return {"valid": len(errors) == 0, "domain_id": spec.get("id", ""), "eval_count": len(eval_qs), "errors": errors}


def load_all_domain_specs(specs_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    base = specs_dir or SPECS_DIR
    loaded: dict[str, dict[str, Any]] = {}
    if not base.is_dir():
        return loaded
    for yml in sorted(base.glob("*.yaml")):
        raw = yaml.safe_load(yml.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and validate_domain_spec(raw)["valid"]:
            loaded[str(raw["id"])] = raw
    return loaded
