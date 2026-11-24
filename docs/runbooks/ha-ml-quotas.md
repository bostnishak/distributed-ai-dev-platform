# Runbook: HA Failover, Model Rollback & Daily Quota Operations

## 1. Rolling Master Upgrade (Zero-Downtime Drain)
1. Call `POST /api/ha/drain/{current_leader_id}`.
2. Standby master calls `POST /api/ha/lease` and assumes leadership with incremented `term`.

## 2. Emergency ML Model Rollback
- Call `POST /api/ml/models/{model_id}/rollback` to revert canary traffic to `0%` and record an immutable audit trail event.

## 3. Adjusting User Token/Energy Quotas
- Inspect utilization via `GET /api/accounting/report/{user_id}` and update caps via `PUT /api/accounting/quotas/{user_id}`.
