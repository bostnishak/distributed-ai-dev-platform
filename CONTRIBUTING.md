# Katkıda Bulunma Rehberi (PROC-05)

Bu rehber hem takım üyeleri hem de projede çalışan yapay zekâ kodlama araçları için ortak kuralları tanımlar.

## İlk kurulum (bir kere yapılır)

1. [Git](https://git-scm.com/downloads) ve Python 3.12 kurun.
2. Repoyu klonlayın ve pre-commit kancalarını etkinleştirin:
   ```bash
   git clone https://github.com/bostnishak/distributed-ai-dev-platform.git
   cd distributed-ai-dev-platform
   pip install pre-commit && pre-commit install
   ```
3. Yerel geliştirme ortamını tek komutla başlatın:
   - Windows: `.\scripts\dev.ps1`
   - Linux/macOS: `./scripts/dev.sh`

Kendi bilgisayarınıza ajan kurmak için [agent-node/README.md](agent-node/README.md) rehberine bakın.

## Değişiklik akışı

**`main` branch'ine doğrudan commit atılmaz.** Her değişiklik kendi branch'inde (veya paralel araçlar için ayrı `git worktree` içinde) yapılır ve Pull Request (PR) ile birleştirilir.

1. Güncel daldan yeni branch açın (`isminiz/PB-xx-kisa-aciklama`).
2. Önce kabul kriterini doğrulayan testi yazın, sonra kodu uygulayın.
3. PR açmadan önce tüm kapıları yerelde çalıştırın:
   ```powershell
   .\master\venv\Scripts\python.exe -m ruff check master agent scripts
   .\master\venv\Scripts\python.exe -m pytest master/tests/ -q
   .\master\venv\Scripts\python.exe -m pytest -m security master/tests/ -v
   .\master\venv\Scripts\python.exe scripts/plan_tool.py check
   .\master\venv\Scripts\python.exe scripts/plan_tool.py wiring --fail-on-new
   ```
4. Commit mesajları İngilizce (Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`) yazılır.
5. PR şablonundaki **Definition of Done** ve **Kanıt** bölümlerini eksiksiz doldurun.

## Yapay zekâ araçları için zorunlu kurallar

Projede birden fazla yapay zekâ aracı (Antigravity, Claude vb.) katkı yapabilir. Her araç şu kurallara uymak zorundadır:

1. **Kanıtsız "tamam" yasağı:** Bir plan maddesi yalnızca kabul testi node ID'si + commit hash'i `docs/plan-v2/PROGRESS.json` içine yazıldığında ve `python scripts/plan_tool.py status` doğruladığında `done` sayılır. Plan dosyalarındaki `Durum: açık` satırı asla elle değiştirilmez.
2. **Yer tutucu ve sessiz hata yasağı:** `TODO`, boş `pass` gövde, `except Exception: pass` veya eksik girdide uydurma varsayılan veri üretimi kesinlikle yasaktır.
3. **Eş zamanlı çalışma izolasyonu:** Aynı çalışma ağacında birden fazla araç aynı dosyalara yazmamalıdır; ayrı dal / `git worktree` kullanılır ve başkasının çalışması geri alınmaz.
4. **Sıfır sır, sıfır emoji, sıfır CDN:** Repoya `.env`, token veya anahtar yazılmaz; arayüzde/belgelerde emoji ve dış CDN kullanılmaz.
5. **Mimari karar değişikliği:** `docs/adr/` altındaki bir karar (D1-D8) değişiyorsa yeni bir ADR eklenir.

## İnceleme (Review) kontrol listesi

- **Yetki ve güvenlik:** Yeni değiştirici endpoint `SEC-22` matrisinden geçiyor mu? Kullanıcı izolasyonu (`owner_id`) korunuyor mu?
- **Halüsinasyon ve doğrulama:** İddialar kaynaklı mı, eksik girdide dürüstçe reddediyor mu, eval gerilemesi var mı?
- **Bağlantı ve test:** Yeni modüller canlı uygulamaya bağlı mı (`plan_tool.py wiring`), testler gerçek LLM/ağ olmadan geçiyor mu?
- **Belgeler:** [Definition of Done](docs/scrum/definition-of-done.md) maddelerinin tümü karşılandı mı?
