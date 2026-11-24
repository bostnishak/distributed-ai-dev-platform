# ADR-0013: Code Factory Templates, IDE Bridge, HA Leases, ML Promotion Gate, Accounting & Notebooks (Wave 3C)

- **Status:** Accepted
- **Date:** 2026-11-24

## Decision
1. **EPK-05 (`master/factory/verified_templates.py`):** 8 syntax/security-verified starter templates with automated repair plan generation.
2. **EPK-06 (`master/ide/bridge.py`):** LSP diagnostics & outline symbols, DAP breakpoint verification, and multi-file unified diff generator.
3. **EPK-10 & EPK-30 (`master/ha/leader.py`):** SQLite lease-based HA leader election with rolling-upgrade drain and idempotent task-result deduplication.
4. **EPK-31 (`master/ml_ops/promotion.py`):** Mandatory eval-threshold model promotion gate with canary traffic split and instant audit-logged rollback.
5. **EPK-32 (`master/accounting.py`):** Per-user token/latency/Wh energy ledger with hard/soft daily quotas returning structured HTTP `429`.
6. **EPK-33 (`master/notebook.py`):** Persistent stateful notebook engine with AST-sandboxed Python cell execution and Jupyter `.ipynb` v4.5 import/export.
