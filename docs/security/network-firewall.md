# Ağ Bağlama ve Windows Güvenlik Duvarı Politikası (SEC-24)

## 1. Varsayılan Bağlama Adresi (`127.0.0.1`)
- Master servisi varsayılan olarak **yalnızca `127.0.0.1:8000`** (loopback) adresine bağlanır; `0.0.0.0` yasaktır.
- `docker-compose.yml` içinde master portu `127.0.0.1:8000:8000` olarak sınırlıdır.
- Yerel geliştirme başlatma komutu:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
  ```

## 2. Tailscale (Tailnet) Üzerinden Ekip Erişimi
Ekip üyelerinin yalnızca Tailscale CGNAT ağı (`100.64.0.0/10`) üzerinden bağlanması için:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1 -Tailscale
```
Bu betik `tailscale ip -4` çıktısını doğrular ve Uvicorn'u **yalnızca Tailscale arayüz IP'sine** bağlar; yerel Wi-Fi/LAN IP adresinden 8000 portuna yapılan bağlantılar reddedilir (`refused`).

## 3. Kapsamlı Windows Güvenlik Duvarı Kuralı (Yalnız Tailnet)
`-Profile Any` **asla kullanılmaz**. Yalnızca `Private` profilinde ve `RemoteAddress 100.64.0.0/10` aralığı için izin verilir:

```powershell
New-NetFirewallRule `
  -DisplayName "CM6453 Master (Tailscale Only)" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8000 `
  -Profile Private `
  -RemoteAddress 100.64.0.0/10
```

Eski geniş kapsamlı bir kural varsa kaldırın:
```powershell
Remove-NetFirewallRule -DisplayName "CM6453*" -ErrorAction SilentlyContinue
```
