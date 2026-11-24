# Parça 1 — Doğrulanmış eksik yetenekler (kodda iz bulunamayan özellikler)

## SOH · Eksik yetenek: Sohbet

#### SOH-01 · Mesajı düzenleyip yeniden gönderme (yerinde)
- **Sorun:** [DOĞRULANDI: F204] Mesajı düzenleyip yeniden gönderme (yerinde): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `editMessage|edit-message|messageEdit` 0 eşleşme).
- **Değişiklik:** Gönderilmiş kullanıcı mesajını yerinde düzenleme ve dallanma (arayüz + API + test).
- **Kabul:** Mesajı düzenleyip yeniden gönderme (yerinde) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-02 · Yanıtı durdur ve devam ettir
- **Sorun:** [DOĞRULANDI: F204] Yanıtı durdur ve devam ettir: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `continue-generation|continueGeneration|resumeStream` 0 eşleşme).
- **Değişiklik:** Kesilen yanıtı kaldığı yerden sürdürme (arayüz + API + test).
- **Kabul:** Yanıtı durdur ve devam ettir uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-03 · Sohbet arşivleme
- **Sorun:** [DOĞRULANDI: F204] Sohbet arşivleme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `archiveChat|archived_chats|/archive` 0 eşleşme).
- **Değişiklik:** Sohbeti silmeden arşive alma (arayüz + API + test).
- **Kabul:** Sohbet arşivleme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-04 · Sohbet başlığını otomatik üretme
- **Sorun:** [DOĞRULANDI: F204] Sohbet başlığını otomatik üretme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `autoTitle|generate_title|generateTitle|auto_title` 0 eşleşme).
- **Değişiklik:** İlk mesajdan kısa başlık üretme (arayüz + API + test).
- **Kabul:** Sohbet başlığını otomatik üretme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-05 · Mesaj bazlı alıntı/yanıtlama
- **Sorun:** [DOĞRULANDI: F204] Mesaj bazlı alıntı/yanıtlama: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `quoteMessage|replyTo|quote_reply` 0 eşleşme).
- **Değişiklik:** Mesajın bir bölümünü alıntılayarak soru sorma (arayüz + API + test).
- **Kabul:** Mesaj bazlı alıntı/yanıtlama uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-06 · Sesli sohbet modu (sürekli konuşma)
- **Sorun:** [DOĞRULANDI: F204] Sesli sohbet modu (sürekli konuşma): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `voiceMode|voice_mode|handsFree|hands-free|continuous.*speech` 0 eşleşme).
- **Değişiklik:** Kesintisiz sesli konuşma döngüsü (arayüz + API + test).
- **Kabul:** Sesli sohbet modu (sürekli konuşma) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### SOH-07 · Sohbette kullanılan modeli değiştirme (model seçici)
- **Sorun:** [DOĞRULANDI: F204] Sohbette kullanılan modeli değiştirme (model seçici): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `modelPicker|model-picker|selectModel|model_select` 0 eşleşme).
- **Değişiklik:** Yanıt öncesi model/ajan seçimi (arayüz + API + test).
- **Kabul:** Sohbette kullanılan modeli değiştirme (model seçici) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-08 · Mesaj bağlantısı (kalıcı link)
- **Sorun:** [DOĞRULANDI: F204] Mesaj bağlantısı (kalıcı link): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `permalink|messageLink|message-link` 0 eşleşme).
- **Değişiklik:** Tek mesaja bağlantı (arayüz + API + test).
- **Kabul:** Mesaj bağlantısı (kalıcı link) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-09 · Taslak mesajı kaydetme
- **Sorun:** [DOĞRULANDI: F204] Taslak mesajı kaydetme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `draft.*(save|store|localStorage)|saveDraft` 0 eşleşme).
- **Değişiklik:** Gönderilmemiş mesajı koruma (arayüz + API + test).
- **Kabul:** Taslak mesajı kaydetme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### SOH-10 · Panodan görsel yapıştırma
- **Sorun:** [DOĞRULANDI: F204] Panodan görsel yapıştırma: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `clipboardData|onpaste|addEventListener\('paste'` 0 eşleşme).
- **Değişiklik:** Panodan görsel/dosya yapıştırma (arayüz + API + test).
- **Kabul:** Panodan görsel yapıştırma uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

## HAF · Eksik yetenek: Hafıza

#### HAF-01 · Projeye özgü kalıcı talimatlar
- **Sorun:** [DOĞRULANDI: F204] Projeye özgü kalıcı talimatlar: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `project_instructions|projectInstructions|custom_instructions.*project` 0 eşleşme).
- **Değişiklik:** Proje düzeyinde sistem talimatı (arayüz + API + test).
- **Kabul:** Projeye özgü kalıcı talimatlar uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### HAF-02 · Hafıza zaman çizelgesi (ne zaman öğrenildi)
- **Sorun:** [DOĞRULANDI: F204] Hafıza zaman çizelgesi (ne zaman öğrenildi): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `memory.*timeline|learned_at|created_at.*memory` 0 eşleşme).
- **Değişiklik:** Hafıza geçmişi görünümü (arayüz + API + test).
- **Kabul:** Hafıza zaman çizelgesi (ne zaman öğrenildi) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## DOS · Eksik yetenek: Dosya

#### DOS-01 · PDF içinde sayfa önizleme
- **Sorun:** [DOĞRULANDI: F204] PDF içinde sayfa önizleme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `pdf\.js|pdfjs|renderPage|page-preview` 0 eşleşme).
- **Değişiklik:** Kaynak PDF sayfasını görüntüleme (arayüz + API + test).
- **Kabul:** PDF içinde sayfa önizleme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DOS-02 · Ekran görüntüsünden kod/arayüz üretme
- **Sorun:** [DOĞRULANDI: F204] Ekran görüntüsünden kod/arayüz üretme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `screenshot.*(to|→).*code|ui_from_image` 0 eşleşme).
- **Değişiklik:** Görselden arayüz üretme (arayüz + API + test).
- **Kabul:** Ekran görüntüsünden kod/arayüz üretme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DOS-03 · Dosya türüne göre önizleme (CSV tablo, JSON ağaç)
- **Sorun:** [DOĞRULANDI: F204] Dosya türüne göre önizleme (CSV tablo, JSON ağaç): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `jsonTree|csvPreview|previewCsv` 0 eşleşme).
- **Değişiklik:** Dosya önizleyici (arayüz + API + test).
- **Kabul:** Dosya türüne göre önizleme (CSV tablo, JSON ağaç) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DOS-04 · Google Drive / OneDrive bağlayıcısı
- **Sorun:** [DOĞRULANDI: F204] Google Drive / OneDrive bağlayıcısı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `drive\.google|graph\.microsoft|onedrive` 0 eşleşme).
- **Değişiklik:** Bulut dosya bağlayıcısı (arayüz + API + test).
- **Kabul:** Google Drive / OneDrive bağlayıcısı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### DOS-05 · GitHub depo bağlayıcısı
- **Sorun:** [DOĞRULANDI: F204] GitHub depo bağlayıcısı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `api\.github\.com|github_connector|githubRepo` 0 eşleşme).
- **Değişiklik:** Depoyu bağlayıp soru sorma (arayüz + API + test).
- **Kabul:** GitHub depo bağlayıcısı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### DOS-06 · Toplu belge yükleme (klasör)
- **Sorun:** [DOĞRULANDI: F204] Toplu belge yükleme (klasör): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `webkitdirectory|directory upload|folderUpload` 0 eşleşme).
- **Değişiklik:** Klasör yükleme (arayüz + API + test).
- **Kabul:** Toplu belge yükleme (klasör) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DOS-07 · Belge sürümleme ve yeniden yükleme
- **Sorun:** [DOĞRULANDI: F204] Belge sürümleme ve yeniden yükleme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `document_versions|doc_version` 0 eşleşme).
- **Değişiklik:** Belge sürümleri (arayüz + API + test).
- **Kabul:** Belge sürümleme ve yeniden yükleme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DOS-08 · El yazısı tanıma
- **Sorun:** [DOĞRULANDI: F204] El yazısı tanıma: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `handwriting|trocr` 0 eşleşme).
- **Değişiklik:** El yazısı OCR (arayüz + API + test).
- **Kabul:** El yazısı tanıma uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · L · Bağ: - · Durum: açık

## KOD · Eksik yetenek: Kod

#### KOD-01 · Monaco/CodeMirror tabanlı editör
- **Sorun:** [DOĞRULANDI: F204] Monaco/CodeMirror tabanlı editör: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `monaco|codemirror|CodeMirror` 0 eşleşme).
- **Değişiklik:** Gerçek kod editörü (arayüz + API + test).
- **Kabul:** Monaco/CodeMirror tabanlı editör uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### KOD-02 · Çalışma alanında git geçmişi grafiği
- **Sorun:** [DOĞRULANDI: F204] Çalışma alanında git geçmişi grafiği: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `git log|gitgraph|commit.*graph` 0 eşleşme).
- **Değişiklik:** Commit geçmişi arayüzü (arayüz + API + test).
- **Kabul:** Çalışma alanında git geçmişi grafiği uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-03 · Bağımlılık güvenlik taraması (pip-audit/npm audit) üretilen projede
- **Sorun:** [DOĞRULANDI: F204] Bağımlılık güvenlik taraması (pip-audit/npm audit) üretilen projede: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `pip-audit|npm audit|safety check` 0 eşleşme).
- **Değişiklik:** Üretilen proje güvenlik taraması (arayüz + API + test).
- **Kabul:** Bağımlılık güvenlik taraması (pip-audit/npm audit) üretilen projede uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-04 · Proje şablon galerisi (8 şablon)
- **Sorun:** [DOĞRULANDI: F204] Proje şablon galerisi (8 şablon): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `templates/|template_gallery` 0 eşleşme).
- **Değişiklik:** Hazır başlangıç şablonları (arayüz + API + test).
- **Kabul:** Proje şablon galerisi (8 şablon) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-05 · Canlı önizleme ile hot reload
- **Sorun:** [DOĞRULANDI: F204] Canlı önizleme ile hot reload: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `hot.?reload|livereload|websocket.*preview` 0 eşleşme).
- **Değişiklik:** Önizlemede anlık yenileme (arayüz + API + test).
- **Kabul:** Canlı önizleme ile hot reload uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-06 · API test aracı (istemci) arayüzü
- **Sorun:** [DOĞRULANDI: F204] API test aracı (istemci) arayüzü: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `api_tester|requestBuilder|postman` 0 eşleşme).
- **Değişiklik:** İstek gönderme paneli (arayüz + API + test).
- **Kabul:** API test aracı (istemci) arayüzü uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-07 · Kod açıklama modu (satır satır)
- **Sorun:** [DOĞRULANDI: F204] Kod açıklama modu (satır satır): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `explain_code|line_by_line|explainCode` 0 eşleşme).
- **Değişiklik:** Kod parçası açıklayıcı (arayüz + API + test).
- **Kabul:** Kod açıklama modu (satır satır) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-08 · Kod çevirisi (dilden dile) doğrulamalı
- **Sorun:** [DOĞRULANDI: F204] Kod çevirisi (dilden dile) doğrulamalı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `translate_code|code_translate` 0 eşleşme).
- **Değişiklik:** Python→JS gibi çeviri + test (arayüz + API + test).
- **Kabul:** Kod çevirisi (dilden dile) doğrulamalı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### KOD-09 · Regex test aracı
- **Sorun:** [DOĞRULANDI: F204] Regex test aracı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `regex_tester|regexTester` 0 eşleşme).
- **Değişiklik:** Regex deneme paneli (arayüz + API + test).
- **Kabul:** Regex test aracı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

## SUN · Eksik yetenek: Sunum

#### SUN-01 · Slayt başına yeniden üretme
- **Sorun:** [DOĞRULANDI: F204] Slayt başına yeniden üretme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `regenerate_slide|regenerateSlide` 0 eşleşme).
- **Değişiklik:** Tek slaytı yeniden üretme (arayüz + API + test).
- **Kabul:** Slayt başına yeniden üretme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### SUN-02 · Slayt görsel/ikon kitaplığı
- **Sorun:** [DOĞRULANDI: F204] Slayt görsel/ikon kitaplığı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `icon_library|iconSet|slide_icons` 0 eşleşme).
- **Değişiklik:** Yerel ikon seti (arayüz + API + test).
- **Kabul:** Slayt görsel/ikon kitaplığı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### SUN-03 · Sunum notları sesli prova (konuşma süresi)
- **Sorun:** [DOĞRULANDI: F204] Sunum notları sesli prova (konuşma süresi): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `rehearse|speaker_timer|speakerTimer` 0 eşleşme).
- **Değişiklik:** Prova modu (arayüz + API + test).
- **Kabul:** Sunum notları sesli prova (konuşma süresi) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### SUN-04 · Word belgesi stil/şablon yükleme
- **Sorun:** [DOĞRULANDI: F204] Word belgesi stil/şablon yükleme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `docx.*template|template.*docx|DocxTemplate` 0 eşleşme).
- **Değişiklik:** Kurumsal DOCX şablonu (arayüz + API + test).
- **Kabul:** Word belgesi stil/şablon yükleme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### SUN-05 · Dilekçe/sözleşme alan doldurma (form)
- **Sorun:** [DOĞRULANDI: F204] Dilekçe/sözleşme alan doldurma (form): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `fill_form|pdf_form|AcroForm` 0 eşleşme).
- **Değişiklik:** PDF form doldurma (arayüz + API + test).
- **Kabul:** Dilekçe/sözleşme alan doldurma (form) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### SUN-06 · Sertifika/fatura toplu üretimi (mail merge)
- **Sorun:** [DOĞRULANDI: F204] Sertifika/fatura toplu üretimi (mail merge): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `mail_merge|mailMerge|bulk_generate` 0 eşleşme).
- **Değişiklik:** Toplu belge üretimi (arayüz + API + test).
- **Kabul:** Sertifika/fatura toplu üretimi (mail merge) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## ARS · Eksik yetenek: Araştırma

#### ARS-01 · Kaynak PDF otomatik indirme ve dizinleme
- **Sorun:** [DOĞRULANDI: F204] Kaynak PDF otomatik indirme ve dizinleme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `download_source|fetch_pdf|source_download` 0 eşleşme).
- **Değişiklik:** Kaynak makaleyi indirip dizinleme (arayüz + API + test).
- **Kabul:** Kaynak PDF otomatik indirme ve dizinleme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARS-02 · Araştırma geçmişi ve tekrar çalıştırma
- **Sorun:** [DOĞRULANDI: F204] Araştırma geçmişi ve tekrar çalıştırma: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `research_history|rerun_research` 0 eşleşme).
- **Değişiklik:** Araştırma kayıtları (arayüz + API + test).
- **Kabul:** Araştırma geçmişi ve tekrar çalıştırma uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARS-03 · Zamana duyarlı sorgular için tarih bağlamı
- **Sorun:** [DOĞRULANDI: F204] Zamana duyarlı sorgular için tarih bağlamı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `current_date|today_iso|now_utc.*prompt` 0 eşleşme).
- **Değişiklik:** Prompt'a güncel tarih (arayüz + API + test).
- **Kabul:** Zamana duyarlı sorgular için tarih bağlamı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARS-04 · Kaynak arşivleme (web sayfası anlık görüntüsü)
- **Sorun:** [DOĞRULANDI: F204] Kaynak arşivleme (web sayfası anlık görüntüsü): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `archive_page|snapshot_page|wayback` 0 eşleşme).
- **Değişiklik:** Sayfa arşivi (arayüz + API + test).
- **Kabul:** Kaynak arşivleme (web sayfası anlık görüntüsü) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARS-05 · Çoklu dilli arama (TR→EN sorgu)
- **Sorun:** [DOĞRULANDI: F204] Çoklu dilli arama (TR→EN sorgu): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `query_translation|translate_query|multilingual_search` 0 eşleşme).
- **Değişiklik:** Sorgu çevirisi (arayüz + API + test).
- **Kabul:** Çoklu dilli arama (TR→EN sorgu) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

## MED · Eksik yetenek: Medya

#### MED-01 · Ses temizleme/dönüştürme
- **Sorun:** [DOĞRULANDI: F204] Ses temizleme/dönüştürme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `pydub|ffmpeg|audio_convert` 0 eşleşme).
- **Değişiklik:** Ses işleme (arayüz + API + test).
- **Kabul:** Ses temizleme/dönüştürme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### MED-02 · QR/barkod üretimi
- **Sorun:** [DOĞRULANDI: F204] QR/barkod üretimi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `qrcode|segno|barcode` 0 eşleşme).
- **Değişiklik:** QR/barkod aracı (arayüz + API + test).
- **Kabul:** QR/barkod üretimi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### MED-03 · SVG/ikon üretimi
- **Sorun:** [DOĞRULANDI: F204] SVG/ikon üretimi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `svg_generate|generate_svg` 0 eşleşme).
- **Değişiklik:** SVG üretimi (arayüz + API + test).
- **Kabul:** SVG/ikon üretimi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### MED-04 · Video üretimi/montajı
- **Sorun:** [DOĞRULANDI: F204] Video üretimi/montajı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `moviepy|video_generate` 0 eşleşme).
- **Değişiklik:** Basit video montajı (arayüz + API + test).
- **Kabul:** Video üretimi/montajı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### MED-05 · Harita/koordinat işleme
- **Sorun:** [DOĞRULANDI: F204] Harita/koordinat işleme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `geopy|folium|leaflet|geocod` 0 eşleşme).
- **Değişiklik:** Harita araçları (arayüz + API + test).
- **Kabul:** Harita/koordinat işleme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## VER · Eksik yetenek: Veri

#### VER-01 · CSV'den otomatik grafik önerisi
- **Sorun:** [DOĞRULANDI: F204] CSV'den otomatik grafik önerisi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `suggest_chart|autoChart|chart_suggest` 0 eşleşme).
- **Değişiklik:** Grafik önerisi (arayüz + API + test).
- **Kabul:** CSV'den otomatik grafik önerisi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### VER-02 · Veri temizleme önerileri ve uygulama
- **Sorun:** [DOĞRULANDI: F204] Veri temizleme önerileri ve uygulama: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `clean_data|dedupe_rows|fillna|impute` 0 eşleşme).
- **Değişiklik:** Temizleme aracı (arayüz + API + test).
- **Kabul:** Veri temizleme önerileri ve uygulama uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### VER-03 · Excel pivot tablo üretimi
- **Sorun:** [DOĞRULANDI: F204] Excel pivot tablo üretimi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `pivot` 0 eşleşme).
- **Değişiklik:** Pivot tablo (arayüz + API + test).
- **Kabul:** Excel pivot tablo üretimi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### VER-04 · Dashboard üretimi (HTML) veriden
- **Sorun:** [DOĞRULANDI: F204] Dashboard üretimi (HTML) veriden: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `generate_dashboard|dashboard_builder` 0 eşleşme).
- **Değişiklik:** Veriden pano (arayüz + API + test).
- **Kabul:** Dashboard üretimi (HTML) veriden uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### VER-05 · Anket/form üretimi ve toplama
- **Sorun:** [DOĞRULANDI: F204] Anket/form üretimi ve toplama: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `survey|form_builder` 0 eşleşme).
- **Değişiklik:** Form oluşturucu (arayüz + API + test).
- **Kabul:** Anket/form üretimi ve toplama uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## AJN · Eksik yetenek: Ajan

#### AJN-01 · Kullanıcı tanımlı ajan/asistan oluşturucu (GPTs benzeri)
- **Sorun:** [DOĞRULANDI: F204] Kullanıcı tanımlı ajan/asistan oluşturucu (GPTs benzeri): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `custom_agent|agent_builder|assistant_builder|create_assistant` 0 eşleşme).
- **Değişiklik:** Kendi asistanını tanımlama (arayüz + API + test).
- **Kabul:** Kullanıcı tanımlı ajan/asistan oluşturucu (GPTs benzeri) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### AJN-02 · Zamanlanmış görevler (her sabah rapor)
- **Sorun:** [DOĞRULANDI: F204] Zamanlanmış görevler (her sabah rapor): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `cron|apscheduler|scheduled_task|schedule_job` 0 eşleşme).
- **Değişiklik:** Zamanlanmış asistan görevleri (arayüz + API + test).
- **Kabul:** Zamanlanmış görevler (her sabah rapor) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### AJN-03 · Ajan yetenek sınavı (benchmark) sonuç grafiği
- **Sorun:** [DOĞRULANDI: F204] Ajan yetenek sınavı (benchmark) sonuç grafiği: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `benchmark.*(chart|graph)|benchmarkChart` 0 eşleşme).
- **Değişiklik:** Benchmark grafiği (arayüz + API + test).
- **Kabul:** Ajan yetenek sınavı (benchmark) sonuç grafiği uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### AJN-04 · Görev öncelik değiştirme arayüzü
- **Sorun:** [DOĞRULANDI: F204] Görev öncelik değiştirme arayüzü: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `set_priority|priority.*(select|ui)` 0 eşleşme).
- **Değişiklik:** Görev önceliği (arayüz + API + test).
- **Kabul:** Görev öncelik değiştirme arayüzü uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### AJN-05 · Ajan bakım modu (boşalt)
- **Sorun:** [DOĞRULANDI: F204] Ajan bakım modu (boşalt): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `drain|maintenance_mode|cordon` 0 eşleşme).
- **Değişiklik:** Ajanı boşaltma (arayüz + API + test).
- **Kabul:** Ajan bakım modu (boşalt) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### AJN-06 · İnsan onayı gerektiren adımlar (human-in-the-loop) arayüzü
- **Sorun:** [DOĞRULANDI: F204] İnsan onayı gerektiren adımlar (human-in-the-loop) arayüzü: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `approval_gate|approve_step|human_in_the_loop` 0 eşleşme).
- **Değişiklik:** Onay kapısı (arayüz + API + test).
- **Kabul:** İnsan onayı gerektiren adımlar (human-in-the-loop) arayüzü uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### AJN-07 · Ajan marketplace/araç galerisi
- **Sorun:** [DOĞRULANDI: F204] Ajan marketplace/araç galerisi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `marketplace|tool_gallery` 0 eşleşme).
- **Değişiklik:** Araç galerisi (arayüz + API + test).
- **Kabul:** Ajan marketplace/araç galerisi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## OPR · Eksik yetenek: Operasyon

#### OPR-01 · Günlük görüntüleyici (arayüz)
- **Sorun:** [DOĞRULANDI: F204] Günlük görüntüleyici (arayüz): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `log_viewer|logs.*stream|/api/admin/logs` 0 eşleşme).
- **Değişiklik:** Günlük sayfası (arayüz + API + test).
- **Kabul:** Günlük görüntüleyici (arayüz) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### OPR-02 · Sağlık sihirbazı otomatik düzeltme
- **Sorun:** [DOĞRULANDI: F204] Sağlık sihirbazı otomatik düzeltme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `auto_fix|fix_it|remediate` 0 eşleşme).
- **Değişiklik:** Tek tıkla düzeltme (arayüz + API + test).
- **Kabul:** Sağlık sihirbazı otomatik düzeltme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### OPR-03 · Telemetri/analitik (yerel) kullanım pano
- **Sorun:** [DOĞRULANDI: F204] Telemetri/analitik (yerel) kullanım pano: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `usage_analytics|analytics` 0 eşleşme).
- **Değişiklik:** Kullanım analitiği (arayüz + API + test).
- **Kabul:** Telemetri/analitik (yerel) kullanım pano uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### OPR-04 · Yük dengeleyici/çoklu master
- **Sorun:** [DOĞRULANDI: F204] Yük dengeleyici/çoklu master: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `leader_election|failover|ha_master` 0 eşleşme).
- **Değişiklik:** Yüksek erişilebilirlik (arayüz + API + test).
- **Kabul:** Yük dengeleyici/çoklu master uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## GUV · Eksik yetenek: Güvenlik

#### GUV-01 · İki aşamalı doğrulama (TOTP)
- **Sorun:** [DOĞRULANDI: F204] İki aşamalı doğrulama (TOTP): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `totp|pyotp|otpauth` 0 eşleşme).
- **Değişiklik:** 2FA (arayüz + API + test).
- **Kabul:** İki aşamalı doğrulama (TOTP) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### GUV-02 · Parola gücü denetimi
- **Sorun:** [DOĞRULANDI: F204] Parola gücü denetimi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `zxcvbn|password_strength|min_length.*password` 0 eşleşme).
- **Değişiklik:** Parola politikası (arayüz + API + test).
- **Kabul:** Parola gücü denetimi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GUV-03 · Oturum listesi ve uzaktan çıkış
- **Sorun:** [DOĞRULANDI: F204] Oturum listesi ve uzaktan çıkış: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `list_sessions|sessions.*revoke_all` 0 eşleşme).
- **Değişiklik:** Oturum yönetimi (arayüz + API + test).
- **Kabul:** Oturum listesi ve uzaktan çıkış uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GUV-04 · Hesap kilitleme ve bildirim
- **Sorun:** [DOĞRULANDI: F204] Hesap kilitleme ve bildirim: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `account_lock|locked_until|lockout` 0 eşleşme).
- **Değişiklik:** Hesap kilidi (arayüz + API + test).
- **Kabul:** Hesap kilitleme ve bildirim uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GUV-05 · IP izin listesi
- **Sorun:** [DOĞRULANDI: F204] IP izin listesi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `ip_allowlist|allowed_ips` 0 eşleşme).
- **Değişiklik:** IP kısıtı (arayüz + API + test).
- **Kabul:** IP izin listesi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GUV-06 · Dosya antivirüs taraması
- **Sorun:** [DOĞRULANDI: F204] Dosya antivirüs taraması: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `clamd|clamav` 0 eşleşme).
- **Değişiklik:** Antivirüs (arayüz + API + test).
- **Kabul:** Dosya antivirüs taraması uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### GUV-07 · Gizli bilgi tespiti yüklemelerde (anahtar sızıntısı)
- **Sorun:** [DOĞRULANDI: F204] Gizli bilgi tespiti yüklemelerde (anahtar sızıntısı): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `detect_secrets|gitleaks|secret_scan` 0 eşleşme).
- **Değişiklik:** Sır taraması (arayüz + API + test).
- **Kabul:** Gizli bilgi tespiti yüklemelerde (anahtar sızıntısı) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P0 · M · Bağ: - · Durum: açık

## ENT · Eksik yetenek: Entegrasyon

#### ENT-01 · Takvim (.ics) dışa aktarma
- **Sorun:** [DOĞRULANDI: F204] Takvim (.ics) dışa aktarma: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `\.ics|icalendar|VEVENT` 0 eşleşme).
- **Değişiklik:** Takvim dosyası (arayüz + API + test).
- **Kabul:** Takvim (.ics) dışa aktarma uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ENT-02 · Telegram/WhatsApp botu
- **Sorun:** [DOĞRULANDI: F204] Telegram/WhatsApp botu: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `telegram|whatsapp|python-telegram-bot` 0 eşleşme).
- **Değişiklik:** Mesajlaşma botu (arayüz + API + test).
- **Kabul:** Telegram/WhatsApp botu uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### ENT-03 · Tarayıcı eklentisi
- **Sorun:** [DOĞRULANDI: F204] Tarayıcı eklentisi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `manifest\.json.*extension|chrome\.runtime` 0 eşleşme).
- **Değişiklik:** Tarayıcı eklentisi (arayüz + API + test).
- **Kabul:** Tarayıcı eklentisi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### ENT-04 · Komut satırı istemcisi (CLI)
- **Sorun:** [DOĞRULANDI: F204] Komut satırı istemcisi (CLI): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `argparse.*assistant|cli_client|dadp-cli` 0 eşleşme).
- **Değişiklik:** CLI (arayüz + API + test).
- **Kabul:** Komut satırı istemcisi (CLI) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ENT-05 · Python/JS SDK
- **Sorun:** [DOĞRULANDI: F204] Python/JS SDK: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `sdk/|client_sdk` 0 eşleşme).
- **Değişiklik:** SDK (arayüz + API + test).
- **Kabul:** Python/JS SDK uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ENT-06 · Webhook ile dış sisteme bildirim
- **Sorun:** [DOĞRULANDI: F204] Webhook ile dış sisteme bildirim: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `outgoing_webhook|post_webhook` 0 eşleşme).
- **Değişiklik:** Giden webhook (arayüz + API + test).
- **Kabul:** Webhook ile dış sisteme bildirim uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ENT-07 · Sosyal medya/metin biçimleri (tweet, LinkedIn)
- **Sorun:** [DOĞRULANDI: F204] Sosyal medya/metin biçimleri (tweet, LinkedIn): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `linkedin|tweet` 0 eşleşme).
- **Değişiklik:** Platforma özel yazım (arayüz + API + test).
- **Kabul:** Sosyal medya/metin biçimleri (tweet, LinkedIn) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## ERI · Eksik yetenek: Erişilebilirlik

#### ERI-01 · Klavye kısayol haritası ekranı
- **Sorun:** [DOĞRULANDI: F204] Klavye kısayol haritası ekranı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `shortcuts.*(modal|help)|keyboardShortcuts` 0 eşleşme).
- **Değişiklik:** Kısayol listesi (arayüz + API + test).
- **Kabul:** Klavye kısayol haritası ekranı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ERI-02 · Yazı boyutu ayarı
- **Sorun:** [DOĞRULANDI: F204] Yazı boyutu ayarı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `fontScale|font-size.*setting|text-size` 0 eşleşme).
- **Değişiklik:** Yazı boyutu (arayüz + API + test).
- **Kabul:** Yazı boyutu ayarı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ERI-03 · Hareketi azalt (prefers-reduced-motion)
- **Sorun:** [DOĞRULANDI: F204] Hareketi azalt (prefers-reduced-motion): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `prefers-reduced-motion` 0 eşleşme).
- **Değişiklik:** Hareket azaltma (arayüz + API + test).
- **Kabul:** Hareketi azalt (prefers-reduced-motion) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ERI-04 · Boş durum yönlendirmeleri
- **Sorun:** [DOĞRULANDI: F204] Boş durum yönlendirmeleri: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `empty-state|emptyState` 0 eşleşme).
- **Değişiklik:** Boş durum (arayüz + API + test).
- **Kabul:** Boş durum yönlendirmeleri uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ERI-05 · Bağlam yardım ipuçları (tooltip sistemi)
- **Sorun:** [DOĞRULANDI: F204] Bağlam yardım ipuçları (tooltip sistemi): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `tooltip` 0 eşleşme).
- **Değişiklik:** İpucu sistemi (arayüz + API + test).
- **Kabul:** Bağlam yardım ipuçları (tooltip sistemi) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ERI-06 · Toast bildirim sistemi
- **Sorun:** [DOĞRULANDI: F204] Toast bildirim sistemi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `toast` 0 eşleşme).
- **Değişiklik:** Bildirim sistemi (arayüz + API + test).
- **Kabul:** Toast bildirim sistemi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

## EGT · Eksik yetenek: Eğitim

#### EGT-01 · Alıştırma/test üretimi ve puanlama
- **Sorun:** [DOĞRULANDI: F204] Alıştırma/test üretimi ve puanlama: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `quiz|exam_generate|generate_questions` 0 eşleşme).
- **Değişiklik:** Test üretimi (arayüz + API + test).
- **Kabul:** Alıştırma/test üretimi ve puanlama uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### EGT-02 · Müfredat/ders planı üretimi
- **Sorun:** [DOĞRULANDI: F204] Müfredat/ders planı üretimi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `lesson_plan|curriculum` 0 eşleşme).
- **Değişiklik:** Ders planı (arayüz + API + test).
- **Kabul:** Müfredat/ders planı üretimi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### EGT-03 · Öğrenme ilerleme takibi
- **Sorun:** [DOĞRULANDI: F204] Öğrenme ilerleme takibi: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `learning_progress|mastery|progress_tracker` 0 eşleşme).
- **Değişiklik:** İlerleme takibi (arayüz + API + test).
- **Kabul:** Öğrenme ilerleme takibi uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### EGT-04 · Kod ödevi otomatik değerlendirme
- **Sorun:** [DOĞRULANDI: F204] Kod ödevi otomatik değerlendirme: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `autograder|grade_submission` 0 eşleşme).
- **Değişiklik:** Ödev değerlendirme (arayüz + API + test).
- **Kabul:** Kod ödevi otomatik değerlendirme uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### EGT-05 · Dil öğrenme modu (telaffuz/çeviri)
- **Sorun:** [DOĞRULANDI: F204] Dil öğrenme modu (telaffuz/çeviri): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `language_learning|pronunciation` 0 eşleşme).
- **Değişiklik:** Dil öğrenme (arayüz + API + test).
- **Kabul:** Dil öğrenme modu (telaffuz/çeviri) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## ALN · Eksik yetenek: Alan

#### ALN-01 · Sağlık: ilaç/etkileşim veri tabanı
- **Sorun:** [DOĞRULANDI: F204] Sağlık: ilaç/etkileşim veri tabanı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `drug_interaction|ilac_etkilesim|atc_code` 0 eşleşme).
- **Değişiklik:** İlaç bilgisi (arayüz + API + test).
- **Kabul:** Sağlık: ilaç/etkileşim veri tabanı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ALN-02 · Mühendislik: malzeme veri tabanı
- **Sorun:** [DOĞRULANDI: F204] Mühendislik: malzeme veri tabanı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `material_db|materials_table|steel_grades` 0 eşleşme).
- **Değişiklik:** Malzeme özellikleri (arayüz + API + test).
- **Kabul:** Mühendislik: malzeme veri tabanı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ALN-03 · Mimari/inşaat: metraj hesapları
- **Sorun:** [DOĞRULANDI: F204] Mimari/inşaat: metraj hesapları: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `metraj|quantity_takeoff|bill_of_quantities` 0 eşleşme).
- **Değişiklik:** Metraj (arayüz + API + test).
- **Kabul:** Mimari/inşaat: metraj hesapları uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ALN-04 · Elektronik: devre şeması/Spice
- **Sorun:** [DOĞRULANDI: F204] Elektronik: devre şeması/Spice: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `spice|ngspice|schematic` 0 eşleşme).
- **Değişiklik:** Devre simülasyonu (arayüz + API + test).
- **Kabul:** Elektronik: devre şeması/Spice uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### ALN-05 · Takvim/vergi/hesaplayıcılar (Türkiye)
- **Sorun:** [DOĞRULANDI: F204] Takvim/vergi/hesaplayıcılar (Türkiye): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `vergi|income_tax|gelir_vergisi` 0 eşleşme).
- **Değişiklik:** Vergi hesaplayıcı (arayüz + API + test).
- **Kabul:** Takvim/vergi/hesaplayıcılar (Türkiye) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ALN-06 · Seyahat planı üretimi (rota/bütçe)
- **Sorun:** [DOĞRULANDI: F204] Seyahat planı üretimi (rota/bütçe): kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `itinerary|trip_plan` 0 eşleşme).
- **Değişiklik:** Seyahat planlayıcı (arayüz + API + test).
- **Kabul:** Seyahat planı üretimi (rota/bütçe) uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### ALN-07 · Tarif/beslenme hesabı
- **Sorun:** [DOĞRULANDI: F204] Tarif/beslenme hesabı: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `recipe|nutrition|kalori` 0 eşleşme).
- **Değişiklik:** Tarif/besin değeri (arayüz + API + test).
- **Kabul:** Tarif/beslenme hesabı uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var.
- **Meta:** P2 · M · Bağ: - · Durum: açık
