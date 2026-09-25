# Katkıda Bulunma Rehberi

Bu rehber git/GitHub'a hiç aşina olmayanlar için yazıldı — adım adım takip edin.

## İlk kurulum (bir kere yapılır)

1. [Git'i indirin](https://git-scm.com/downloads) (yoksa).
2. Repoyu bilgisayarınıza indirin (klonlayın):
   ```bash
   git clone https://github.com/bostnishak/coklu-llm-orkestrasyon.git
   cd coklu-llm-orkestrasyon
   ```
3. Kendi ismiyle git'e tanıtın (bir kere):
   ```bash
   git config --global user.name "Adınız Soyadınız"
   git config --global user.email "kendi-emailiniz@example.com"
   ```

## Değişiklik yapmak istediğinizde (her seferinde bu akış)

**`main` branch'ine doğrudan değişiklik yapamazsınız** — herkes kendi branch'inde çalışıp bir **Pull Request (PR)** açar, biri onaylayınca `main`'e birleşir (merge).

1. **Güncel `main`'i çekin:**
   ```bash
   git checkout main
   git pull
   ```
2. **Kendinize yeni bir branch açın** (isim: ne yaptığınızı kısaca anlatsın):
   ```bash
   git checkout -b duru/phi4-mini-node-kurulumu
   ```
3. **Değişikliklerinizi yapın** (dosya düzenleyin, ekleyin vb.)
4. **Değişiklikleri kaydedin (commit):**
   ```bash
   git add .
   git commit -m "Phi-4-mini node kurulum notlarını ekledim"
   ```
5. **Branch'inizi GitHub'a gönderin (push):**
   ```bash
   git push -u origin duru/phi4-mini-node-kurulumu
   ```
6. **Pull Request açın:** push ettikten sonra terminal size bir link verecek (veya GitHub'da repoya gidince "Compare & pull request" butonu çıkacak). Tıklayın, kısa bir açıklama yazın, "Create pull request" deyin.
7. Biri (ör. İshak) PR'ı inceleyip onaylayınca `main`'e birleşecek. Onaylanana kadar branch'inizde değişiklik yapmaya devam edebilirsiniz — sadece tekrar `git add`, `commit`, `push` yapmanız yeterli.

## Branch isimlendirme

`isminiz/ne-yaptiginiz` formatını kullanın, örnek:
- `furkan/llama-node-setup`
- `semih/gemma-readme-duzeltme`
- `isil/coder-model-testi`

## Sık karşılaşılan durumlar

- **"Merge conflict" hatası aldım:** panik yapmayın, kimseye söyleyip yardım isteyin (İshak'a yazın) — genelde aynı dosyanın aynı satırını iki kişi değiştirince olur.
- **Yanlış branch'te çalıştım:** `git status` ile hangi branch'te olduğunuzu görebilirsiniz, `git checkout main` ile ana branch'e dönebilirsiniz.
- **`.env` dosyasını asla commit etmeyin** — içinde gizli anahtar (key) var, zaten `.gitignore` bunu engelliyor ama emin olmak için `git status`'ta `.env`'in çıkmadığından emin olun.

## CI (otomatik kontrol)

Her PR'da otomatik olarak orkestratör kodu üzerinde temel bir kontrol (lint) çalışır. Kırmızı (başarısız) çıkarsa PR'ı merge etmeden önce düzeltin — hata mesajı GitHub'da "Checks" sekmesinde görünür.
