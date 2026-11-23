"""DIST-13 & DIST-14: Tailscale Network Discovery, 5-Mode Connectivity Diagnostics & Agent One-Liner Setup."""

from __future__ import annotations

from typing import Any


def parse_tailscale_peers(status_json: dict[str, Any]) -> list[dict[str, Any]]:
    """DIST-13: Extract candidate agent nodes and MagicDNS hostnames from `tailscale status --json`."""
    peers: list[dict[str, Any]] = []
    for _key, p in (status_json.get("Peer") or {}).items():
        ips = p.get("TailscaleIPs") or []
        peers.append({
            "hostname": str(p.get("HostName") or ""),
            "dns_name": str(p.get("DNSName") or "").rstrip("."),
            "tailnet_ip": str(ips[0]) if ips else "",
            "online": bool(p.get("Online", False)),
            "os": str(p.get("OS") or ""),
        })
    return peers


def diagnose_tailscale_failure(probes: dict[str, Any]) -> dict[str, Any]:
    """DIST-13: Classify all 5 known Tailscale/master connectivity failure modes with actionable remediation."""
    if not probes.get("control_plane_ok", True):
        return {
            "category": "control_plane_unreachable",
            "message": "Tailscale kontrol sunucusuna ulaşılamıyor (IPv6/TLS engeli olabilir).",
            "fix": "1) IPv6'yı geçici kapatıp `tailscale up` deneyin, 2) Sistem saati ve TLS sertifikasını doğrulayın.",
        }
    if not probes.get("ip_is_tailnet", True):
        return {
            "category": "wrong_ip",
            "message": "Master adresi 100.64.0.0/10 Tailscale aralığında değil.",
            "fix": "`tailscale ip -4` çıktısındaki 100.x.y.z adresini kullanın; `0.0.0.0` yerine tailnet IP bağlayın.",
        }
    if not probes.get("port_open", True):
        return {
            "category": "port_closed",
            "message": "Master 8000 portu kapalı veya Windows güvenlik duvarı engelliyor.",
            "fix": "Master sunucusunu başlatın ve güvenlik duvarında yalnız 100.64.0.0/10 için TCP 8000'e izin verin.",
        }
    if probes.get("acl_denied", False):
        return {
            "category": "acl_blocked",
            "message": "Tailscale ACL politikası bu ajanın master porta erişimini reddediyor.",
            "fix": "Tailscale Admin Console ACL kurallarında `tag:agent -> tag:master:8000` iznini ekleyin.",
        }
    if probes.get("schema_mismatch", False):
        return {
            "category": "version_mismatch",
            "message": "Ajan ve Master sürümü uyumsuz.",
            "fix": "Ajan düğümünde `git pull` ve kurulum betiğini yeniden çalıştırın.",
        }
    return {"category": "healthy", "message": "Tailscale ve Master bağlantısı sağlıklı.", "fix": ""}


def generate_agent_install_command(master_url: str, *, os_type: str = "windows", model: str = "qwen2.5-coder:7b") -> dict[str, str]:
    """DIST-14: Generate validated one-line setup command for Windows or Linux agent onboarding."""
    clean_url = master_url.rstrip("/")
    if os_type.lower() == "linux":
        cmd = f"curl -fsSL {clean_url}/static/agent-setup.sh | bash -s -- --master {clean_url} --model {model}"
    else:
        cmd = f".\\agent-node\\setup.ps1 -MasterUrl '{clean_url}' -Model '{model}' -InstallService"
    return {"os": os_type.lower(), "master_url": clean_url, "model": model, "command": cmd}
