"""Demo seed: 3 örnek proje oluşturur ve ajanların görev almasını bekler.

Kullanım:
    python seed_demo.py

Master sunucu çalışıyor ve start_agents.py açık olmalı.
"""

import sys
import time
from pathlib import Path

import httpx

MASTER_URL = "http://127.0.0.1:8000"


def _read_token() -> str:
    env_path = Path(__file__).parent / "agent" / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("AGENT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("AGENT_TOKEN bulunamadı — agent/.env dosyasını kontrol edin.")


PROJECTS = [
    {
        "name": "Kütüphane Yönetim Sistemi",
        "text": """
Kütüphane Yönetim Sistemi SRS:

1. Kitap yönetimi: ISBN, başlık, yazar, stok takibi
2. Üye yönetimi: kayıt, giriş, profil güncelleme
3. Ödünç alma / iade: tarih takibi, gecikme cezası hesabı
4. Arama: başlık, yazar, kategori bazlı
5. Admin paneli: katalog yönetimi, raporlar
6. REST API + SQLite veritabanı
7. Responsive HTML/CSS/JS arayüz
8. Pytest ile otomatik testler
9. API dokümantasyonu
""".strip(),
    },
    {
        "name": "Görev Takip Uygulaması",
        "text": """
Görev Takip Uygulaması SRS:

1. Kullanıcı kaydı ve JWT ile kimlik doğrulama
2. Proje oluşturma ve görev atama
3. Görev durumları: bekliyor, devam ediyor, tamamlandı
4. Öncelik seviyeleri: düşük, orta, yüksek, kritik
5. Bildirim sistemi: görev atama ve son tarih hatırlatmaları
6. Ekip üyesi davet ve izin yönetimi
7. FastAPI backend + SQLite
8. Vanilla JS dashboard
9. Birim ve entegrasyon testleri
""".strip(),
    },
    {
        "name": "Blog Platformu",
        "text": """
Blog Platformu SRS:

1. Yazar kaydı ve profil sayfası
2. Makale oluşturma, düzenleme, yayınlama (Markdown destekli)
3. Kategori ve etiket sistemi
4. Yorum bölümü (kayıtlı kullanıcılar)
5. Arama ve filtreleme
6. RSS feed
7. Admin moderasyon paneli
8. FastAPI + SQLite backend
9. SEO dostu HTML/CSS frontend
10. Test suite
""".strip(),
    },
]


def main() -> None:
    token = _read_token()
    headers = {"Authorization": f"Bearer {token}"}

    print("=" * 55)
    print("  Demo Seed — 3 örnek proje oluşturuluyor")
    print("=" * 55)

    with httpx.Client(base_url=MASTER_URL, timeout=30.0) as client:
        # Check server
        try:
            r = client.get("/health")
            r.raise_for_status()
            print(f"  Master sunucu: OK ({MASTER_URL})")
        except Exception as exc:
            print(f"  HATA: Master sunucuya ulaşılamıyor — {exc}")
            print("  Önce 'cd master && uvicorn app:app --reload' çalıştırın.")
            sys.exit(1)

        # Check agents online
        r = client.get("/api/agents")
        agents = r.json() if r.status_code == 200 else []
        online = [a for a in agents if a.get("heartbeat_status") in ("idle", "busy")]
        print(f"  Kayıtlı ajan: {len(agents)}  |  Çevrimiçi: {len(online)}")
        if online == 0:
            print("  UYARI: Hiç çevrimiçi ajan yok. start_agents.py çalıştırın.")

        # Create projects
        created = []
        for proj in PROJECTS:
            r = client.post("/api/projects", data=proj, headers=headers)
            if r.status_code == 202:
                pid = r.json()["id"]
                print(f"  ✓ '{proj['name']}' oluşturuldu (id={pid})")
                created.append(pid)
            else:
                print(f"  ✗ '{proj['name']}' başarısız: HTTP {r.status_code} — {r.text[:80]}")

    print("-" * 55)
    print(f"  {len(created)}/{len(PROJECTS)} proje oluşturuldu.")
    print("  Tarayıcıda http://127.0.0.1:8000 adresini açın.")
    print("  Ajanlar görevleri otomatik olarak çekecek.")
    print("=" * 55)


if __name__ == "__main__":
    main()
