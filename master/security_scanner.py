"""Cluster B (`[M30]`, Faz 6.5): Static Security Scanner & Automated Vulnerability Remediator.

Re-exports `scan_code_security` from `self_healing_runner` and adds:
- `auto_remediate_security_issues(source: str, language: str = "python") -> dict`
"""

from __future__ import annotations

import re
from typing import Any

from self_healing_runner import scan_code_security

__all__ = [
    "auto_remediate_security_issues",
    "scan_code_security",
]

_EVAL_RE = re.compile(r"(?<![.\w])eval\s*\(")
_SHELL_TRUE_RE = re.compile(r"shell\s*=\s*True")
_PICKLE_LOADS_RE = re.compile(r"\bpickle\.loads?\s*\(")
_YAML_LOAD_RE = re.compile(r"\byaml\.load\s*\(([^)]+)\)")
_INNER_HTML_RE = re.compile(r"\.innerHTML\s*=\s*")


def auto_remediate_security_issues(source: str, language: str = "python") -> dict[str, Any]:
    """Automatically remediate common high-severity security vulnerabilities in source code."""
    remediated = source or ""
    lang = (language or "python").strip().lower()
    remediations: list[str] = []

    if lang in {"python", "py"}:
        if _EVAL_RE.search(remediated):
            remediated = _EVAL_RE.sub("ast.literal_eval(", remediated)
            if "import ast" not in remediated:
                remediated = "import ast\n" + remediated
            remediations.append("Replaced unsafe `eval(` with `ast.literal_eval(`.")

        if _SHELL_TRUE_RE.search(remediated):
            remediated = _SHELL_TRUE_RE.sub("shell=False", remediated)
            remediations.append("Replaced `shell=True` with `shell=False` in subprocess call.")

        if _PICKLE_LOADS_RE.search(remediated):
            remediated = _PICKLE_LOADS_RE.sub("json.loads(", remediated)
            if "import json" not in remediated:
                remediated = "import json\n" + remediated
            remediations.append("Replaced unsafe `pickle.load/loads` with `json.loads`.")

        if _YAML_LOAD_RE.search(remediated) and "SafeLoader" not in remediated and "safe_load" not in remediated:
            remediated = re.sub(r"\byaml\.load\s*\(", "yaml.safe_load(", remediated)
            remediations.append("Replaced unsafe `yaml.load(` with `yaml.safe_load(`.")

    elif lang in {"javascript", "js", "typescript", "ts", "html"}:
        if _INNER_HTML_RE.search(remediated):
            remediated = _INNER_HTML_RE.sub(".textContent = ", remediated)
            remediations.append("Replaced unsanitized `.innerHTML =` assignment with `.textContent =`.")

        if _EVAL_RE.search(remediated):
            remediated = _EVAL_RE.sub("JSON.parse(", remediated)
            remediations.append("Replaced unsafe JavaScript `eval(` with `JSON.parse(`.")

    return {
        "language": lang,
        "modified": remediated != (source or ""),
        "remediation_count": len(remediations),
        "remediations": remediations,
        "remediated_source": remediated,
    }
