"""EPK-06 IDE Bridge package (LSP diagnostics, DAP debug sessions, multi-file unified diffs)."""

from ide.bridge import (
    compute_multi_file_diff,
    create_dap_trace_session,
    get_lsp_diagnostics,
    router,
)

__all__ = [
    "compute_multi_file_diff",
    "create_dap_trace_session",
    "get_lsp_diagnostics",
    "router",
]
