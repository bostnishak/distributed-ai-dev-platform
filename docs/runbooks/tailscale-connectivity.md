# Runbook: Tailscale Connectivity & Firewall (`tailscale-connectivity`)

## Symptom
- Remote team agents fail to reach `http://<tailnet-ip>:8000` with timeout, TLS, or IPv6 DNS resolution errors.

## Diagnosis
1. Run `tailscale status` and `tailscale ping <master-hostname>` on both Master and member laptops.
2. Verify Master binding address (`127.0.0.1` for local-only, or explicit `100.x.y.z` tailnet IP for team mode, `SEC-24`).
3. Check if IPv6/ISP DNS hijacking interferes with `*.ts.net` resolution; test directly with the `100.64.0.0/10` IPv4 tailnet IP.
4. Check Windows Defender Firewall rules allowing inbound TCP 8000 strictly from `100.64.0.0/10` (never `0.0.0.0/0`).

## Resolution
1. Start Master bound specifically to the Tailscale IPv4 address using `scripts/dev.ps1 -Tailnet`.
2. Configure `MASTER_URL=http://<master-tailnet-ip>:8000` in the member's `.env` instead of relying on ISP DNS.
3. If the campus/home network blocks UDP DERP relays, switch to offline demo fallback (`scripts/demo_checklist.ps1` + staging agents).
