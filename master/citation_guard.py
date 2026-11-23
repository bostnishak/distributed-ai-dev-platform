"""Cluster C ([M42]): Mandatory Numerical & Standard Citation Verification Guardrail."""

from __future__ import annotations

from typing import Any

from hybrid_graph_rag import verify_citations


def verify_numerical_citations(answer: str, retrieved_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify numerical claims in ``answer`` against ``retrieved_docs`` and attach source tags."""
    return verify_citations(answer=answer, retrieved_docs=retrieved_docs)


__all__ = [
    "verify_citations",
    "verify_numerical_citations",
]
