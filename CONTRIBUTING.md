# Katkıda Bulunma Rehberi

Bu rehber git/GitHub'a hiç aşina olmayanlar için yazıldı; adım adım takip edin.

## İlk kurulum (bir kere yapılır)

1. [Git'i indirin](https://git-scm.com/downloads) (yoksa).
2. GitHub'dan gelen **collaborator davetini** kabul edin (e-postanıza veya GitHub bildirimlerinize gelir).
3. Repoyu bilgisayarınıza indirin (klonlayın):
   ```bash
   git clone https://github.com/bostnishak/distributed-ai-dev-platform.git
   cd distributed-ai-dev-platform
   ```
4. Git'e kendinizi tanıtın (bir kere):
   ```bash
   git config --global user.name "Adınız Soyadınız"
   git config --global user.email "github-hesabinizdaki-email@example.com"
   ```

Kendi bilgisayarınıza ajan kurmak için ayrıca [agent-node/README.md](agent-node/README.md)'ye bakın.

## Değişiklik yapmak istediğinizde (her seferinde bu akış)

**`main` branch'ine doğrudan değişiklik yapılamaz.** Herkes kendi branch'inde çalışır ve bir **Pull Request (PR)** açar. CI (otomatik kontrol) yeşil olunca ve bir takım arkadaşı onaylayınca PR `main`'e birleşir (merge).

1. **Güncel `main`'i çekin:**
   ```bash
   git checkout main
   git pull
   ```
2. **Trello'da üzerinde çalışacağınız kartı** "Yapılıyor" listesine taşıyın ve kartın ID'sini not edin (ör. `PB-24`).
3. **Kendinize yeni bir branch açın.** İsim `isminiz/kart-id-kisa-aciklama` biçiminde olsun:
   ```bash
   git checkout -b duru/PB-22-yetenek-degerlendirme
   ```
4. **Değişikliklerinizi yapın** ve bilgisayarınızda test edin (aşağıdaki "Testler").
5. **Değişiklikleri kaydedin (commit).** Commit mesajları İngilizce yazılır:
   ```bash
   git add .
   git commit -m "Add capability evaluation runner"
   ```
6. **Branch'inizi GitHub'a gönderin (push):**
   ```bash
   git push -u origin duru/PB-22-yetenek-degerlendirme
   ```
7. **Pull Request açın.** Push sonrası terminalde çıkan linke tıklayın ya da GitHub'da "Compare & pull request" butonuna basın.
   - Başlık kart ID'siyle başlasın: `PB-22: Capability evaluation runner`.
   - Açıklamada ne yaptığınızı ve nasıl test ettiğinizi yazın.
8. **Review isteyin:** PR sayfasında sağdaki "Reviewers" kısmından bir takım arkadaşınızı seçin.
9. Trello kartını "İnceleme / Test" listesine taşıyın ve kartta PR linkini paylaşın.
10. Onay gelince PR'ı birleştirin ve kartı "Bitti"ye taşıyın.

## Review yaparken

- Kod anlaşılır mı? Test var mı? CI yeşil mi?
- [Definition of Done](docs/scrum/definition-of-done.md) maddeleri sağlanıyor mu?
- Gerekirse değişiklik isteyin ("Request changes"). Uygunsa "Approve" deyin.

## Yazım kuralları

- **Arayüz metinleri Türkçe**, **kod yorumları İngilizce**, **commit mesajları İngilizce**.
- Hocaya giden dokümanlar (README, `docs/` altı) İngilizce. Takım rehberleri (bu dosya, `agent-node/README.md`) Türkçe.

## Testler

Kod değiştirdiyseniz PR açmadan önce çalıştırın (Windows; macOS/Linux'ta `.venv/bin/...`):

```bash
cd master
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests/ -v
.venv\Scripts\python -m ruff check .
```

`agent` klasörü için de aynısı geçerli.

## Sık karşılaşılan durumlar

- **"Merge conflict" hatası aldım:** Panik yapmayın, ekipten yardım isteyin. Genelde aynı dosyanın aynı satırını iki kişi değiştirince olur.
- **Yanlış branch'te çalıştım:** `git status` ile hangi branch'te olduğunuzu görün. `git checkout main` ile ana branch'e dönebilirsiniz.
- **`.env` dosyalarını asla commit etmeyin.** İçlerinde gizli anahtarlar (`AGENT_TOKEN` vb.) var. `.gitignore` bunları engelliyor, yine de `git status` çıktısında `.env` görmediğinizden emin olun.

## CI (otomatik kontrol)

Her PR'da GitHub Actions şunları çalıştırır:

- `master` ve `agent` için lint (ruff) ve birim testleri (pytest)
- Docker imajlarının derlenmesi

Kırmızı (başarısız) çıkarsa PR birleştirilemez. Hata mesajı GitHub'da PR'ın "Checks" sekmesinde görünür.
