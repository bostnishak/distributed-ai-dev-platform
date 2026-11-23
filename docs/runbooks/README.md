# Operational Runbooks (OPS-15)

Every `/ready` alert and common operational incident maps to a concrete runbook below following the **Symptom -> Diagnosis -> Resolution** format.

| Incident / `/ready` Check | Runbook |
|---|---|
| Ollama unreachable (`ollama` degraded) | [ollama-down.md](ollama-down.md) |
| Required model or embedding missing (`ollama` degraded) | [model-missing.md](model-missing.md) |
| SQLite lock or write error (`database` down) | [database-locked.md](database-locked.md) |
| Low free disk space (`disk` degraded/down) | [disk-full.md](disk-full.md) |
| Distributed agent offline or lease timeout | [agent-offline.md](agent-offline.md) |
| Tailscale connectivity / DNS / IPv6 / firewall | [tailscale-connectivity.md](tailscale-connectivity.md) |
| Hallucination or RAG eval regression in CI | [eval-regression.md](eval-regression.md) |
| Encrypted backup & disaster recovery restore | [backup-restore.md](backup-restore.md) |
