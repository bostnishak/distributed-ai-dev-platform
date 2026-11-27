"""Policy gate for actions with effects, driven by where the data in context came from (taint).

Content from the web, uploads or external tools is UNTRUSTED. Once a run has read such content it cannot take a
privileged action without a person's approval, secrets never leave the machine, and irreversible actions always ask.
"""

from __future__ import annotations

from dataclasses import dataclass

import security_scan

TRUSTED = "trusted"
UNTRUSTED = "untrusted"
EGRESS = frozenset({"network_egress", "web_search", "mcp_call", "git_push"})
PRIVILEGED = frozenset({"shell_exec", "git_push", "env_read", "policy_edit", "file_delete", "mcp_call", "package_install"})
IRREVERSIBLE = frozenset({"browser_submit", "send_message", "payment", "file_delete", "git_push"})


@dataclass(frozen=True)
class Decision:
    allowed: bool
    needs_approval: bool
    reason: str


class PolicyError(PermissionError):
    """The action was refused; the message says why."""


def has_secret(text: str) -> bool:
    return security_scan.redact(text or "") != (text or "")


def check(action: str, *, integrity: str = TRUSTED, payload: str = "", approved: bool = False) -> Decision:
    """Decide one action. `approved` means a person confirmed this exact action."""
    if action in EGRESS and has_secret(payload):
        return Decision(False, False, "Gizli anahtar içeren veri makine dışına gönderilemez.")
    if action in IRREVERSIBLE and not approved:
        return Decision(False, True, "Geri alınamaz eylem: önce senin onayın gerekiyor.")
    if integrity != TRUSTED and action in PRIVILEGED and not approved:
        return Decision(False, True, "Bu çalışma dışarıdan gelen içerik okudu; yetkili eylem için onayın gerekiyor.")
    return Decision(True, False, "izinli")


def require(action: str, *, integrity: str = TRUSTED, payload: str = "", approved: bool = False) -> None:
    decision = check(action, integrity=integrity, payload=payload, approved=approved)
    if not decision.allowed:
        raise PolicyError(decision.reason)


@dataclass
class Context:
    """The trust level of one run; reading outside content lowers it and nothing raises it again."""

    integrity: str = TRUSTED

    def read_external(self) -> None:
        self.integrity = UNTRUSTED

    def require(self, action: str, *, payload: str = "", approved: bool = False) -> None:
        require(action, integrity=self.integrity, payload=payload, approved=approved)
