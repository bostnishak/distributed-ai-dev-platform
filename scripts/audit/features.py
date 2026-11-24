"""Capability-absence matrix: features the big assistants offer, each checked against routes and source text."""

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "master"

# (category, feature, presence regex, what to build)
F = [
    # --- chat experience
    ("Sohbet", "Mesajı düzenleyip yeniden gönderme (yerinde)", r"editMessage|edit-message|messageEdit", "Gönderilmiş kullanıcı mesajını yerinde düzenleme ve dallanma"),
    ("Sohbet", "Yanıt dalları arasında gezinme (1/3)", r"branchIndex|responseVariants|alternatives\b|variant", "Aynı soru için birden çok yanıt varyantı ve gezinme"),
    ("Sohbet", "Yanıtı durdur ve devam ettir", r"continue-generation|continueGeneration|resumeStream", "Kesilen yanıtı kaldığı yerden sürdürme"),
    ("Sohbet", "Sohbet sabitleme (pin)", r"pinChat|pinned_chat|chat.*pin", "Önemli sohbetleri sabitleme"),
    ("Sohbet", "Sohbet klasörleri / projeler", r"chat_folders|chatFolder|folders", "Sohbetleri klasörlere ayırma"),
    ("Sohbet", "Sohbet arşivleme", r"archiveChat|archived_chats|/archive", "Sohbeti silmeden arşive alma"),
    ("Sohbet", "Sohbet başlığını otomatik üretme", r"autoTitle|generate_title|generateTitle|auto_title", "İlk mesajdan kısa başlık üretme"),
    ("Sohbet", "Mesaj bazlı alıntı/yanıtlama", r"quoteMessage|replyTo|quote_reply", "Mesajın bir bölümünü alıntılayarak soru sorma"),
    ("Sohbet", "Sesli sohbet modu (sürekli konuşma)", r"voiceMode|voice_mode|handsFree|hands-free|continuous.*speech", "Kesintisiz sesli konuşma döngüsü"),
    ("Sohbet", "Yanıt sesli okuma ayarları (ses/hız seçimi)", r"speechRate|voiceName|utterance\.rate|SpeechSynthesisUtterance", "TTS ses ve hız seçimi"),
    ("Sohbet", "Sohbette kullanılan modeli değiştirme (model seçici)", r"modelPicker|model-picker|selectModel|model_select", "Yanıt öncesi model/ajan seçimi"),
    ("Sohbet", "Geçici (kayıtsız) sohbet modu", r"incognito|temporaryChat|temporary_chat|ephemeral", "Hiçbir yere kaydedilmeyen sohbet"),
    ("Sohbet", "Sohbet içi arama (Ctrl+F benzeri)", r"searchInChat|find-in-chat|chatSearch", "Açık sohbet içinde arama"),
    ("Sohbet", "Mesaj bağlantısı (kalıcı link)", r"permalink|messageLink|message-link", "Tek mesaja bağlantı"),
    ("Sohbet", "Yanıt uzunluğu/ton hızlı ayarı", r"responseLength|tone", "Yanıt başına uzunluk/ton seçici"),
    ("Sohbet", "Taslak mesajı kaydetme", r"draft.*(save|store|localStorage)|saveDraft", "Gönderilmemiş mesajı koruma"),
    ("Sohbet", "Çoklu dosya sürükle-bırak", r"ondrop|dragover|drop.*files", "Sürükle-bırak yükleme"),
    ("Sohbet", "Panodan görsel yapıştırma", r"clipboardData|onpaste|addEventListener\('paste'", "Panodan görsel/dosya yapıştırma"),
    ("Sohbet", "Yanıtı Markdown/PDF/DOCX olarak dışa aktarma", r"export.*(pdf|docx)|toPdf|to_docx", "Sohbet/yanıt PDF-DOCX dışa aktarma"),
    ("Sohbet", "Mesaja tepki/emoji değil, kalite puanı (1-5)", r"rating|stars|score_feedback", "Yanıt kalite puanı"),
    # --- memory / personalization
    ("Hafıza", "Hafıza kayıtlarını görme ve düzenleme arayüzü", r"memories.*(edit|put|patch)|editMemory", "Hafıza kaydı düzenleme"),
    ("Hafıza", "Hafızaya 'bunu hatırla' komutu", r"remember_this|rememberThis|/remember|hatırla", "Sohbette doğal dille hafıza ekleme"),
    ("Hafıza", "Hafıza dışa/içe aktarma", r"memories.*export|importMemories|memory_export", "Hafıza taşıma"),
    ("Hafıza", "Projeye özgü kalıcı talimatlar", r"project_instructions|projectInstructions|custom_instructions.*project", "Proje düzeyinde sistem talimatı"),
    ("Hafıza", "Kişilik/ton ön ayarları", r"persona|personality_preset|tonePreset", "Hazır kişilik/ton profilleri"),
    ("Hafıza", "Hafıza zaman çizelgesi (ne zaman öğrenildi)", r"memory.*timeline|learned_at|created_at.*memory", "Hafıza geçmişi görünümü"),
    ("Hafıza", "Konuşmalar arası bağlam arama ('geçen hafta ne konuştuk')", r"history/search|searchHistory", "Geçmiş sohbet araması"),
    ("Hafıza", "Kullanıcı bazlı veri saklama süresi arayüzü", r"retention.*(ui|select|setting)|retentionDays", "Saklama süresi ayarı"),
    # --- files / RAG
    ("Dosya", "PDF içinde sayfa önizleme", r"pdf\.js|pdfjs|renderPage|page-preview", "Kaynak PDF sayfasını görüntüleme"),
    ("Dosya", "Görsel dosya yükleyip soru sorma (VQA)", r"vision|VLM|image_url|describe_image", "Görsel anlama"),
    ("Dosya", "Ekran görüntüsünden kod/arayüz üretme", r"screenshot.*(to|→).*code|ui_from_image", "Görselden arayüz üretme"),
    ("Dosya", "Dosya türüne göre önizleme (CSV tablo, JSON ağaç)", r"jsonTree|csvPreview|previewCsv", "Dosya önizleyici"),
    ("Dosya", "Google Drive / OneDrive bağlayıcısı", r"drive\.google|graph\.microsoft|onedrive", "Bulut dosya bağlayıcısı"),
    ("Dosya", "GitHub depo bağlayıcısı", r"api\.github\.com|github_connector|githubRepo", "Depoyu bağlayıp soru sorma"),
    ("Dosya", "Toplu belge yükleme (klasör)", r"webkitdirectory|directory upload|folderUpload", "Klasör yükleme"),
    ("Dosya", "Belge sürümleme ve yeniden yükleme", r"document_versions|doc_version", "Belge sürümleri"),
    ("Dosya", "OCR (taranmış belge)", r"pytesseract|easyocr|paddleocr|ocr_enabled", "Taranmış PDF/görselden metin"),
    ("Dosya", "El yazısı tanıma", r"handwriting|trocr", "El yazısı OCR"),
    ("Dosya", "Tablo çıkarma sonucunu XLSX indirme", r"table.*xlsx|tables_to_xlsx", "Çıkarılan tabloyu Excel'e aktarma"),
    ("Dosya", "Belge karşılaştırma (iki sürüm farkı)", r"compare_documents|document_diff|docDiff", "İki belge farkı"),
    ("Dosya", "E-posta (.eml/.msg) yükleme", r"\.eml|\.msg|email.*parse", "E-posta dosyası ayrıştırma"),
    ("Dosya", "Ses dosyası yükleyip transkripsiyon", r"transcribe", "Toplantı kaydı transkripsiyonu"),
    ("Dosya", "Video yükleyip özet (kare+ses)", r"keyframe|key_frame|video_summary|ffmpeg", "Video analizi"),
    ("Dosya", "Arşiv (zip) içindeki belgeleri toplu dizinleme", r"index_zip|zip.*ingest|ingest.*zip", "ZIP toplu dizinleme"),
    # --- code / IDE
    ("Kod", "Monaco/CodeMirror tabanlı editör", r"monaco|codemirror|CodeMirror", "Gerçek kod editörü"),
    ("Kod", "Sözdizimi vurgulama (highlight.js/Prism)", r"highlight\.js|hljs|prism", "Kod vurgulama kitaplığı"),
    ("Kod", "Dil sunucusu (LSP) köprüsü", r"pyright|tsserver|language.server|lsp", "Kod tamamlama/tanılama"),
    ("Kod", "Etkileşimli terminal (PTY)", r"pty|winpty|ConPTY|xterm", "Gerçek terminal"),
    ("Kod", "Hata ayıklayıcı (DAP)", r"debugpy|DAP|breakpoint", "Kesme noktalı hata ayıklama"),
    ("Kod", "Çalışma alanında git geçmişi grafiği", r"git log|gitgraph|commit.*graph", "Commit geçmişi arayüzü"),
    ("Kod", "Çok dosyalı toplu yeniden düzenleme (rename symbol)", r"rename_symbol|renameSymbol|refactor", "Sembol yeniden adlandırma"),
    ("Kod", "Test üretme ve çalıştırma düğmesi", r"generate_tests|run_tests|pytest.*action", "Testleri üret/çalıştır"),
    ("Kod", "Kod incelemesi (PR benzeri) arayüzü", r"code_review|review_comments|reviewPanel", "Diff üzerinde inceleme yorumları"),
    ("Kod", "Bağımlılık güvenlik taraması (pip-audit/npm audit) üretilen projede", r"pip-audit|npm audit|safety check", "Üretilen proje güvenlik taraması"),
    ("Kod", "Docker/compose dosyası üretimi", r"Dockerfile.*generate|generate_dockerfile|docker-compose", "Dockerfile üretimi"),
    ("Kod", "Proje şablon galerisi (8 şablon)", r"templates/|template_gallery", "Hazır başlangıç şablonları"),
    ("Kod", "Canlı önizleme ile hot reload", r"hot.?reload|livereload|websocket.*preview", "Önizlemede anlık yenileme"),
    ("Kod", "Kod snippet kitaplığı", r"snippet", "Kaydedilen kod parçaları"),
    ("Kod", "Jupyter benzeri hücre çalıştırma (not defteri)", r"notebook|ipynb|jupyter|nbformat", "Not defteri modu"),
    ("Kod", "Veritabanı şeması görselleştirme (ERD) arayüzde", r"erd|mermaid.*er", "ERD gösterimi"),
    ("Kod", "API test aracı (istemci) arayüzü", r"api_tester|requestBuilder|postman", "İstek gönderme paneli"),
    ("Kod", "Kod açıklama modu (satır satır)", r"explain_code|line_by_line|explainCode", "Kod parçası açıklayıcı"),
    ("Kod", "Kod çevirisi (dilden dile) doğrulamalı", r"translate_code|code_translate", "Python→JS gibi çeviri + test"),
    ("Kod", "Regex test aracı", r"regex_tester|regexTester", "Regex deneme paneli"),
    ("Kod", "SQL çalıştırma (salt-okunur) ve sonuç tablosu", r"run_sql|sql_query|/sql", "SQL aracı arayüzü"),
    # --- presentations / docs
    ("Sunum", "Sunum şablon/tema galerisi", r"theme_gallery|slide_themes|presentation.*theme", "Tema seçimi"),
    ("Sunum", "Slayt başına yeniden üretme", r"regenerate_slide|regenerateSlide", "Tek slaytı yeniden üretme"),
    ("Sunum", "Slayt görsel/ikon kitaplığı", r"icon_library|iconSet|slide_icons", "Yerel ikon seti"),
    ("Sunum", "PPTX → PDF/PNG önizleme", r"libreoffice|soffice|pptx.*pdf|render_slide", "Sunum önizlemesi"),
    ("Sunum", "Sunum notları sesli prova (konuşma süresi)", r"rehearse|speaker_timer|speakerTimer", "Prova modu"),
    ("Sunum", "Excel formül doğrulama", r"formulas|xlcalculator|LibreOffice.*recalc", "XLSX formül hesaplama testi"),
    ("Sunum", "Word belgesi stil/şablon yükleme", r"docx.*template|template.*docx|DocxTemplate", "Kurumsal DOCX şablonu"),
    ("Sunum", "Belgede yorum/değişiklik izleme", r"tracked_changes|track_changes|w:ins|w:del", "Değişiklik izleme"),
    ("Sunum", "Dilekçe/sözleşme alan doldurma (form)", r"fill_form|pdf_form|AcroForm", "PDF form doldurma"),
    ("Sunum", "LaTeX/Overleaf çıktısı", r"latex|\.tex\b|pdflatex", "Bilimsel makale LaTeX"),
    ("Sunum", "Markdown → kitap/rapor (TOC, sayfa numarası) PDF", r"weasyprint|reportlab|fpdf|pdfkit", "PDF üretici"),
    ("Sunum", "Poster/afiş/infografik üretimi", r"infographic|poster", "Görsel tasarım çıktıları"),
    ("Sunum", "Sertifika/fatura toplu üretimi (mail merge)", r"mail_merge|mailMerge|bulk_generate", "Toplu belge üretimi"),
    # --- research / web
    ("Araştırma", "Web arama sağlayıcısı yapılandırılmış", r"SEARXNG_URL.*http|searx.*configured", "Çalışan bir arama sağlayıcısı (SearXNG vb.)"),
    ("Araştırma", "Haber/RSS izleme", r"feedparser|rss", "Konu izleme (RSS)"),
    ("Araştırma", "Akademik arama (arXiv/Semantic Scholar/CrossRef)", r"arxiv|semanticscholar|crossref|openalex", "Akademik kaynak arama"),
    ("Araştırma", "Wikipedia/Wikidata arama", r"wikipedia|wikidata", "Bilgi tabanı arama"),
    ("Araştırma", "Kaynak PDF otomatik indirme ve dizinleme", r"download_source|fetch_pdf|source_download", "Kaynak makaleyi indirip dizinleme"),
    ("Araştırma", "Araştırma planı kullanıcı onayı", r"approve_plan|research_plan|plan_approval", "Plana onay/düzenleme"),
    ("Araştırma", "Araştırma geçmişi ve tekrar çalıştırma", r"research_history|rerun_research", "Araştırma kayıtları"),
    ("Araştırma", "Zamana duyarlı sorgular için tarih bağlamı", r"current_date|today_iso|now_utc.*prompt", "Prompt'a güncel tarih"),
    ("Araştırma", "Kaynak arşivleme (web sayfası anlık görüntüsü)", r"archive_page|snapshot_page|wayback", "Sayfa arşivi"),
    ("Araştırma", "Çoklu dilli arama (TR→EN sorgu)", r"query_translation|translate_query|multilingual_search", "Sorgu çevirisi"),
    ("Araştırma", "Alıntı biçimleri (APA/IEEE/Chicago) arayüzü", r"citation_style|IEEE|Vancouver", "Kaynakça biçim seçici"),
    ("Araştırma", "Kaynak güvenilirlik göstergesi arayüzde", r"credibility.*(badge|ui)|source_credibility", "Kaynak güven rozeti"),
    # --- media
    ("Medya", "Yerel görsel üretimi (SD/ComfyUI)", r"stable.?diffusion|comfyui|diffusers|image_gen.*model", "Gerçek görsel üretim modeli"),
    ("Medya", "Görsel düzenleme (arka plan kaldırma, kırpma)", r"rembg|remove_background|image_edit|inpaint", "Görsel düzenleme"),
    ("Medya", "Metinden sese (yerel TTS) dosya üretimi", r"piper|coqui|pyttsx|edge.tts|tts_file", "Sunucu tarafı TTS"),
    ("Medya", "Altyazı üretimi (SRT)", r"\.srt|srt_export|subtitle", "Video/ses altyazısı"),
    ("Medya", "Ses temizleme/dönüştürme", r"pydub|ffmpeg|audio_convert", "Ses işleme"),
    ("Medya", "Diyagram üretimi (Mermaid/Graphviz) çizim", r"mermaid\.(render|init)|graphviz|dot -T", "Diyagram çizme"),
    ("Medya", "QR/barkod üretimi", r"qrcode|segno|barcode", "QR/barkod aracı"),
    ("Medya", "Grafik üretimi (matplotlib/plotly) sohbetten", r"matplotlib|plotly|vega|chart\.js|echarts", "Veriden grafik"),
    ("Medya", "SVG/ikon üretimi", r"svg_generate|generate_svg", "SVG üretimi"),
    ("Medya", "Video üretimi/montajı", r"moviepy|video_generate", "Basit video montajı"),
    ("Medya", "3B model (STL/OBJ) üretimi ve görüntüleme", r"three\.js|trimesh|\.stl|\.obj", "3B önizleme"),
    ("Medya", "Harita/koordinat işleme", r"geopy|folium|leaflet|geocod", "Harita araçları"),
    # --- data analysis
    ("Veri", "CSV'den otomatik grafik önerisi", r"suggest_chart|autoChart|chart_suggest", "Grafik önerisi"),
    ("Veri", "Pandas benzeri veri dönüştürme sohbetten", r"pandas|polars|duckdb", "Veri çerçevesi motoru"),
    ("Veri", "İstatistik testleri (t-test, ANOVA, ki-kare)", r"scipy|statsmodels|stat-test", "İstatistik testi"),
    ("Veri", "Zaman serisi tahmini (ARIMA/Prophet)", r"statsmodels.*ARIMA|prophet|forecast", "Tahmin"),
    ("Veri", "Aykırı değer ve veri kalitesi raporu", r"outlier|data_quality|profile_report", "Veri profili"),
    ("Veri", "Veri temizleme önerileri ve uygulama", r"clean_data|dedupe_rows|fillna|impute", "Temizleme aracı"),
    ("Veri", "Veritabanına bağlanma (PostgreSQL/MySQL) sohbetten", r"psycopg|pymysql|sqlalchemy.*create_engine", "Harici DB bağlayıcısı"),
    ("Veri", "Excel pivot tablo üretimi", r"pivot", "Pivot tablo"),
    ("Veri", "Dashboard üretimi (HTML) veriden", r"generate_dashboard|dashboard_builder", "Veriden pano"),
    ("Veri", "Makine öğrenmesi modeli eğitimi (sklearn) sohbetten", r"sklearn|scikit|AutoML|automl", "Basit ML eğitim"),
    ("Veri", "Anket/form üretimi ve toplama", r"survey|form_builder", "Form oluşturucu"),
    ("Veri", "Veri anonimleştirme", r"anonymi[sz]e", "Anonimleştirme"),
    # --- agents / distributed
    ("Ajan", "Kullanıcı tanımlı ajan/asistan oluşturucu (GPTs benzeri)", r"custom_agent|agent_builder|assistant_builder|create_assistant", "Kendi asistanını tanımlama"),
    ("Ajan", "Zamanlanmış görevler (her sabah rapor)", r"cron|apscheduler|scheduled_task|schedule_job", "Zamanlanmış asistan görevleri"),
    ("Ajan", "Webhook/olay tetikleyici", r"webhook", "Dış olayla görev tetikleme"),
    ("Ajan", "Ajan başına GPU/VRAM görünür panosu", r"vram|nvidia-smi|gpu_memory", "VRAM panosu"),
    ("Ajan", "Ajan yetenek sınavı (benchmark) sonuç grafiği", r"benchmark.*(chart|graph)|benchmarkChart", "Benchmark grafiği"),
    ("Ajan", "Görev öncelik değiştirme arayüzü", r"set_priority|priority.*(select|ui)", "Görev önceliği"),
    ("Ajan", "Ajan bakım modu (boşalt)", r"drain|maintenance_mode|cordon", "Ajanı boşaltma"),
    ("Ajan", "Ajan etiketleri/gruplar", r"agent_tags|agent_group|labels", "Ajan gruplama"),
    ("Ajan", "Görev tekrar oynatma (replay) arayüzü", r"replay", "Çalıştırma tekrarı"),
    ("Ajan", "İnsan onayı gerektiren adımlar (human-in-the-loop) arayüzü", r"approval_gate|approve_step|human_in_the_loop", "Onay kapısı"),
    ("Ajan", "MCP sunucusu olarak dışa açma", r"mcp_server|FastMCP|expose.*mcp", "Platformu MCP sunucusu yapma"),
    ("Ajan", "Ajan marketplace/araç galerisi", r"marketplace|tool_gallery", "Araç galerisi"),
    # --- admin / ops
    ("Operasyon", "Kullanıcı yönetimi sayfası (liste/rol/devre dışı)", r"list_users|users.*(table|admin)|/api/auth/users", "Kullanıcı yönetimi arayüzü"),
    ("Operasyon", "Kota ve kullanım limitleri (token/gün)", r"quota|usage_limit|token_budget", "Kullanıcı kotası"),
    ("Operasyon", "Maliyet/enerji muhasebesi", r"energy|cost_estimate|kwh", "Kullanım maliyeti"),
    ("Operasyon", "Yapılandırma sayfası (env değerleri güvenli düzenleme)", r"config_editor|settings.*env|admin.*config", "Yönetici ayarları"),
    ("Operasyon", "Günlük görüntüleyici (arayüz)", r"log_viewer|logs.*stream|/api/admin/logs", "Günlük sayfası"),
    ("Operasyon", "Yedek zamanlama arayüzü", r"backup.*(schedule|cron)|backup_ui", "Yedek ayarı"),
    ("Operasyon", "Model indirme/silme arayüzü (Ollama pull)", r"api/pull|ollama.*pull|pull_model", "Model yönetimi"),
    ("Operasyon", "Sağlık sihirbazı otomatik düzeltme", r"auto_fix|fix_it|remediate", "Tek tıkla düzeltme"),
    ("Operasyon", "Sürüm/güncelleme denetimi", r"check_update|latest_version|updater", "Güncelleme denetimi"),
    ("Operasyon", "Çok dilli arayüz (en az 3 dil)", r"'de'|'fr'|'es'|locale.*(de|fr|es)", "TR/EN dışında dil"),
    ("Operasyon", "Telemetri/analitik (yerel) kullanım pano", r"usage_analytics|analytics", "Kullanım analitiği"),
    ("Operasyon", "Uyarı kanalları (e-posta/Telegram/Discord)", r"smtp|telegram|discord|slack_webhook", "Uyarı gönderimi"),
    ("Operasyon", "Yük dengeleyici/çoklu master", r"leader_election|failover|ha_master", "Yüksek erişilebilirlik"),
    ("Operasyon", "Veri tabanı bakım arayüzü (vacuum/doctor)", r"db-doctor", "DB bakım sayfası"),
    ("Operasyon", "Terraform/Compose dağıtım betikleri", r"docker-compose\.ya?ml|compose\.ya?ml", "Dağıtım dosyaları"),
    # --- security / privacy
    ("Güvenlik", "İki aşamalı doğrulama (TOTP)", r"totp|pyotp|otpauth", "2FA"),
    ("Güvenlik", "Parola gücü denetimi", r"zxcvbn|password_strength|min_length.*password", "Parola politikası"),
    ("Güvenlik", "Oturum listesi ve uzaktan çıkış", r"list_sessions|sessions.*revoke_all", "Oturum yönetimi"),
    ("Güvenlik", "Hesap kilitleme ve bildirim", r"account_lock|locked_until|lockout", "Hesap kilidi"),
    ("Güvenlik", "API anahtarı üretimi (kullanıcı için)", r"api_key.*(create|generate)|personal_access_token", "Kişisel API anahtarı"),
    ("Güvenlik", "Güvenlik başlıkları (CSP, HSTS)", r"Content-Security-Policy", "CSP"),
    ("Güvenlik", "Gizlilik/veri kullanım sayfası", r"privacy|gizlilik", "Gizlilik sayfası"),
    ("Güvenlik", "Veri silme isteği arayüzü (hesap silme)", r"delete_account|deleteAccount|erase_user", "Hesap silme düğmesi"),
    ("Güvenlik", "IP izin listesi", r"ip_allowlist|allowed_ips", "IP kısıtı"),
    ("Güvenlik", "Dosya antivirüs taraması", r"clamd|clamav", "Antivirüs"),
    ("Güvenlik", "Gizli bilgi tespiti yüklemelerde (anahtar sızıntısı)", r"detect_secrets|gitleaks|secret_scan", "Sır taraması"),
    ("Güvenlik", "Denetim izi arayüzü", r"audit.*(table|ui|viewer)|auditViewer", "Denetim görüntüleyici"),
    # --- integrations
    ("Entegrasyon", "Takvim (.ics) dışa aktarma", r"\.ics|icalendar|VEVENT", "Takvim dosyası"),
    ("Entegrasyon", "E-posta taslağı gönderme (mailto/SMTP)", r"mailto:|smtplib", "E-posta entegrasyonu"),
    ("Entegrasyon", "Notion/Obsidian içe-dışa aktarma", r"notion|obsidian", "Not uygulaması bağlantısı"),
    ("Entegrasyon", "Telegram/WhatsApp botu", r"telegram|whatsapp|python-telegram-bot", "Mesajlaşma botu"),
    ("Entegrasyon", "Tarayıcı eklentisi", r"manifest\.json.*extension|chrome\.runtime", "Tarayıcı eklentisi"),
    ("Entegrasyon", "Komut satırı istemcisi (CLI)", r"argparse.*assistant|cli_client|dadp-cli", "CLI"),
    ("Entegrasyon", "OpenAI uyumlu API uç noktası", r"/v1/chat/completions", "OpenAI uyumlu API"),
    ("Entegrasyon", "Python/JS SDK", r"sdk/|client_sdk", "SDK"),
    ("Entegrasyon", "Mobil uygulama/PWA manifest", r"manifest\.webmanifest|serviceWorker|service-worker", "PWA"),
    ("Entegrasyon", "Masaüstü uygulaması (Electron/Tauri)", r"electron|tauri", "Masaüstü paket"),
    ("Entegrasyon", "Webhook ile dış sisteme bildirim", r"outgoing_webhook|post_webhook", "Giden webhook"),
    ("Entegrasyon", "Sosyal medya/metin biçimleri (tweet, LinkedIn)", r"linkedin|tweet", "Platforma özel yazım"),
    # --- accessibility / i18n / UX
    ("Erişilebilirlik", "Klavye kısayol haritası ekranı", r"shortcuts.*(modal|help)|keyboardShortcuts", "Kısayol listesi"),
    ("Erişilebilirlik", "Yüksek kontrast teması", r"high-contrast|highContrast|data-theme=.contrast", "Yüksek kontrast"),
    ("Erişilebilirlik", "Yazı boyutu ayarı", r"fontScale|font-size.*setting|text-size", "Yazı boyutu"),
    ("Erişilebilirlik", "Ekran okuyucu için canlı bölge (aria-live)", r"aria-live", "Canlı bölge"),
    ("Erişilebilirlik", "Hareketi azalt (prefers-reduced-motion)", r"prefers-reduced-motion", "Hareket azaltma"),
    ("Erişilebilirlik", "Sağdan sola dil desteği (RTL)", r"dir=.rtl|rtl", "RTL"),
    ("Erişilebilirlik", "Çevrimdışı mod (service worker)", r"serviceWorker", "Çevrimdışı çalışma"),
    ("Erişilebilirlik", "Yükleme iskeletleri (skeleton)", r"skeleton", "İskelet yükleme"),
    ("Erişilebilirlik", "Boş durum yönlendirmeleri", r"empty-state|emptyState", "Boş durum"),
    ("Erişilebilirlik", "Onboarding turu", r"onboarding|tour|walkthrough", "İlk kullanım turu"),
    ("Erişilebilirlik", "Bağlam yardım ipuçları (tooltip sistemi)", r"tooltip", "İpucu sistemi"),
    ("Erişilebilirlik", "Toast bildirim sistemi", r"toast", "Bildirim sistemi"),
    # --- education
    ("Eğitim", "Alıştırma/test üretimi ve puanlama", r"quiz|exam_generate|generate_questions", "Test üretimi"),
    ("Eğitim", "Aralıklı tekrar kartları (flashcards)", r"flashcard|spaced_repetition|anki", "Bilgi kartları"),
    ("Eğitim", "Adım adım problem çözümü (matematik)", r"step_by_step|sympy", "Adım adım çözüm"),
    ("Eğitim", "Müfredat/ders planı üretimi", r"lesson_plan|curriculum", "Ders planı"),
    ("Eğitim", "Öğrenme ilerleme takibi", r"learning_progress|mastery|progress_tracker", "İlerleme takibi"),
    ("Eğitim", "Kod ödevi otomatik değerlendirme", r"autograder|grade_submission", "Ödev değerlendirme"),
    ("Eğitim", "Dil öğrenme modu (telaffuz/çeviri)", r"language_learning|pronunciation", "Dil öğrenme"),
    ("Eğitim", "Konu haritası/zihin haritası", r"mindmap|mind_map|markmap", "Zihin haritası"),
    # --- domains
    ("Alan", "Hukuk: mevzuat veri tabanı (madde atıflı)", r"mevzuat|kanun_no|resmi_gazete", "Mevzuat arama"),
    ("Alan", "Sağlık: ilaç/etkileşim veri tabanı", r"drug_interaction|ilac_etkilesim|atc_code", "İlaç bilgisi"),
    ("Alan", "Finans: canlı kur/hisse verisi", r"exchange_rate|fx_rate|tcmb", "Kur verisi"),
    ("Alan", "Mühendislik: malzeme veri tabanı", r"material_db|materials_table|steel_grades", "Malzeme özellikleri"),
    ("Alan", "Mimari/inşaat: metraj hesapları", r"metraj|quantity_takeoff|bill_of_quantities", "Metraj"),
    ("Alan", "Elektronik: devre şeması/Spice", r"spice|ngspice|schematic", "Devre simülasyonu"),
    ("Alan", "Kimya: formül/denklem dengeleme", r"balance_equation|chem|molar_mass", "Kimya araçları"),
    ("Alan", "Biyoloji: dizi analizi", r"biopython|fasta|sequence_align", "Biyoinformatik"),
    ("Alan", "Takvim/vergi/hesaplayıcılar (Türkiye)", r"vergi|income_tax|gelir_vergisi", "Vergi hesaplayıcı"),
    ("Alan", "Seyahat planı üretimi (rota/bütçe)", r"itinerary|trip_plan", "Seyahat planlayıcı"),
    ("Alan", "Tarif/beslenme hesabı", r"recipe|nutrition|kalori", "Tarif/besin değeri"),
    ("Alan", "Spor/antrenman planı", r"workout|training_plan", "Antrenman planı"),
]


def corpus():
    spec = json.load(urllib.request.urlopen("http://127.0.0.1:8099/openapi.json"))
    text = [json.dumps(list(spec["paths"].keys()))]
    for base, pats in ((M, ("*.py",)), (M / "static", ("*.js", "*.html", "*.css", "*.json"))):
        for pat in pats:
            for p in base.rglob(pat):
                if any(x in p.parts for x in ("venv", ".venv", "tests", "__pycache__", "data", "node_modules")):
                    continue
                text.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(text)


if __name__ == "__main__":
    body = corpus()
    rows = []
    for category, feature, pattern, build in F:
        hits = len(re.findall(pattern, body, re.I))
        rows.append({"category": category, "feature": feature, "pattern": pattern, "hits": hits, "present": hits > 0, "build": build})
    Path(sys.argv[1]).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    absent = [r for r in rows if not r["present"]]
    print(len(rows), "özellik,", len(absent), "bulunamadı")
    import collections

    print(collections.Counter(r["category"] for r in absent).most_common())
