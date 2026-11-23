# Runbook: Distributed Agent Offline (`agent-offline`)

## Symptom
- Agent status shows `offline` in the Agents tab or `GET /api/agents`.
- Tasks assigned to the agent time out and are re-queued by lease recovery (`DIST-06`).

## Diagnosis
1. Check heartbeat age in `GET /api/agents` and task lease logs in `GET /api/events`.
2. On the member's machine, verify `MASTER_URL`, `AGENT_TOKEN`, and local Ollama health.
3. Verify Tailscale connectivity between the member laptop and Master (see [tailscale-connectivity.md](tailscale-connectivity.md)).

## Resolution
1. Restart the member agent via `agent-node/` start script or `python start_agents.py`.
2. Confirm the agent re-registers with its capability profile (`DIST-01`) and resumes polling.
3. If the member machine remains unavailable, verify lease expiry re-assigned its pending task to another capable online agent with zero task loss.
