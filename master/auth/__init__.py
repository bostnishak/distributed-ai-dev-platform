"""SEC-01 & SEC-02: Local Accounts, Signed HttpOnly Sessions, RBAC, and Optional Tailscale Identity."""

from auth.api import router
from auth.service import init_auth_db

__all__ = ["init_auth_db", "router"]
