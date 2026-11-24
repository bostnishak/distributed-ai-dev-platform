"""Builds docs/plan-v3 from measured audit findings (docs/plan-v3/kanit/*.json) plus the roadmap programs.

Usage: python scripts/audit/build_plan.py
Every item that is not an EPK program carries a [DOĞRULANDI: F2xx] tag and a reproduction command in README.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs" / "plan-v3"
KANIT = PLAN / "kanit"
sys.path.insert(0, str(Path(__file__).parent))
from epics import EPICS  # noqa: E402


def load(name):
    path = KANIT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def item(prio, effort, finding, title, sorun, change, accept, deps="-"):
    return {"prio": prio, "effort": effort, "finding": finding, "title": title, "sorun": sorun, "change": change, "accept": accept, "deps": deps}


# ---------------------------------------------------------------- python static analysis (ruff)
RUFF_TEXT = {
    "BLE001": ("P1", "S", "kapsamsız except", "Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.", "`ruff check --select BLE001 {file}` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular."),
    "C901": ("P2", "M", "karmaşık fonksiyon", "Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.", "`ruff check --select C901 {file}` bu fonksiyonu raporlamaz; mevcut testler geçer."),
    "PLR0913": ("P2", "S", "çok parametreli fonksiyon", "Parametreleri veri sınıfına veya ayar nesnesine topla.", "`ruff check --select PLR0913 {file}` bu fonksiyonu raporlamaz; çağıranlar güncellenir."),
    "PLR0912": ("P2", "M", "çok dallı fonksiyon", "Dalları tablo veya strateji nesnelerine indir.", "`ruff check --select PLR0912 {file}` bu fonksiyonu raporlamaz; her dal için test var."),
    "PLR0915": ("P2", "M", "çok uzun fonksiyon", "Aşamalara böl, her aşama ayrı sınanır.", "`ruff check --select PLR0915 {file}` bu fonksiyonu raporlamaz."),
    "S608": ("P1", "S", "dinamik SQL dizesi", "Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.", "`ruff check --select S608 {file}` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez."),
    "ARG001": ("P3", "S", "kullanılmayan argüman", "Argümanı kaldır veya kullan; çağıranları güncelle.", "`ruff check --select ARG001 {file}` bu satırı raporlamaz."),
    "S603": ("P1", "S", "alt süreç çağrısı", "Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.", "`ruff check --select S603 {file}` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir."),
    "S607": ("P1", "S", "kısmi yolla süreç başlatma", "Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.", "`ruff check --select S607 {file}` bu satırı raporlamaz."),
    "S110": ("P1", "S", "try/except/pass", "Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.", "`ruff check --select S110 {file}` bu satırı raporlamaz."),
    "PLW0603": ("P3", "S", "global değişken ataması", "Durumu sınıfa veya modül nesnesine taşı.", "`ruff check --select PLW0603 {file}` bu satırı raporlamaz."),
    "S101": ("P2", "S", "assert kullanımı", "Çalışma zamanı denetimini açık istisnaya çevir (assert -O ile kalkar).", "`ruff check --select S101 {file}` bu satırı raporlamaz."),
    "ERA001": ("P3", "S", "yorum satırına alınmış kod", "Kodu sil veya testlere taşı.", "`ruff check --select ERA001 {file}` bu satırı raporlamaz."),
    "S311": ("P2", "S", "güvenlik amaçlı olmayan rastgelelik", "Güvenlik değeriyse `secrets` kullan; değilse `noqa` gerekçesi yaz.", "`ruff check --select S311 {file}` bu satırı raporlamaz."),
    "T201": ("P3", "S", "print çağrısı", "Günlük kaydına çevir.", "`ruff check --select T201 {file}` bu satırı raporlamaz."),
    "S324": ("P1", "S", "zayıf özet işlevi", "Güvenlik amaçlıysa SHA-256+; değilse `usedforsecurity=False` ve gerekçe.", "`ruff check --select S324 {file}` bu satırı raporlamaz."),
    "S105": ("P1", "S", "sabit parola benzeri dize", "Değeri ortam değişkeni/gizli depodan oku.", "`ruff check --select S105 {file}` bu satırı raporlamaz."),
    "S108": ("P1", "S", "güvensiz geçici dosya yolu", "`tempfile` kullan.", "`ruff check --select S108 {file}` bu satırı raporlamaz."),
}
RUFF_AREAS = {"BLE001": ("BLE", "Python: kapsamsız except"), "C901": ("KMP", "Python: karmaşık fonksiyonlar"), "PLR0913": ("PRM", "Python: çok parametreli fonksiyonlar"),
              "PLR0912": ("DAL", "Python: çok dallı fonksiyonlar"), "PLR0915": ("UZN", "Python: çok uzun fonksiyonlar"), "S608": ("SQL", "Python: dinamik SQL dizeleri")}


def ruff_items():
    by_area: dict[str, list] = {}
    for hit in sorted(load("ruff.json"), key=lambda h: (h["code"], h["filename"], h["location"]["row"])):
        rel = hit["filename"].replace("\\", "/").split("/master/", 1)[-1]
        prio, effort, kind, change, accept = RUFF_TEXT[hit["code"]]
        code, _ = RUFF_AREAS.get(hit["code"], ("STA", "Python: diğer statik analiz bulguları"))
        sorun = f"{rel}:{hit['location']['row']} — {hit['message']} (`{hit['code']}`)."
        by_area.setdefault(code, []).append(item(prio, effort, "F201", f"{rel}:{hit['location']['row']} {kind}", sorun, change, accept.format(file=rel)))
    return by_area


# ---------------------------------------------------------------- frontend static scan
JS_TEXT = {
    "innerHTML-assignment": ("P1", "S", "innerHTML ataması", "Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.", "40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not."),
    "fetch-no-catch-nearby": ("P1", "S", "hata yolu olmayan fetch", "`api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.", "Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test)."),
    "function-over-80-lines": ("P2", "M", "çok uzun JS fonksiyonu", "Fonksiyonu bileşenlere böl.", "Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer."),
    "file-over-400-lines": ("P2", "M", "çok uzun JS modülü", "Modülü sorumluluklarına göre ayır.", "Modül ≤ 400 satır; dışa aktarılan API aynı."),
    "localStorage-direct": ("P2", "S", "doğrudan localStorage", "Depolama yardımcısına (try/catch, şema sürümü) geçir.", "Depolama kapalıyken bu akış çalışır (test)."),
    "focus-outline-removed": ("P1", "S", "odak halkası kaldırılmış", "`outline:none` yerine görünür `:focus-visible` stili ver.", "Klavye odağı bu öğede görünür (axe ve elle)."),
    "double-equals": ("P3", "S", "gevşek eşitlik (==)", "`===` kullan.", "Satır `===` kullanır; davranış testi geçer."),
    "alert-confirm-prompt": ("P2", "S", "engelleyici alert/confirm/prompt", "Erişilebilir modal bileşeniyle değiştir.", "Odak tuzaklı modal kullanılır; klavye ile onaylanır."),
    "addEventListener-on-window-document": ("P2", "S", "temizlenmeyen global dinleyici", "Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.", "Sayfa değişince dinleyici kaldırılır (sızıntı testi)."),
    "inline-style-assignment": ("P3", "S", "cssText ataması", "CSS sınıfına taşı.", "Satır sınıf kullanır."),
    "magic-timeout": ("P3", "S", "sihirli zaman aşımı sayısı", "Adlandırılmış sabite çıkar.", "Sabit adı belgelidir."),
    "button-without-type": ("P2", "S", "type'sız düğme", "`type=\"button\"` ekle.", "Form içinde yanlışlıkla gönderim olmaz."),
    "tiny-font": ("P2", "S", "11px altı yazı", "En az 12px yap.", "Yazı ≥ 12px."),
    "setInterval-no-clear": ("P2", "S", "temizlenmeyen setInterval", "Sayfa kapanınca `clearInterval` çağır.", "Sayfa değişince zamanlayıcı durur."),
    "css-size": ("P3", "S", "çok fazla !important", "Özgüllüğü düzenle.", "!important sayısı ≤ 5."),
    "insertAdjacentHTML": ("P1", "S", "insertAdjacentHTML", "Sanitizer'dan geçir veya DOM API kullan.", "Saldırı örneği çalışmaz."),
    "hardcoded-http-url": ("P3", "S", "sabit http adresi", "Yapılandırmaya taşı.", "Adres yapılandırmadan okunur."),
}
JS_AREAS = {"innerHTML-assignment": "XSS", "fetch-no-catch-nearby": "AGH"}


def js_items():
    by_area: dict[str, list] = {}
    for hit in sorted(load("js.json"), key=lambda h: (h["rule"], h["file"], h["line"])):
        prio, effort, kind, change, accept = JS_TEXT.get(hit["rule"], ("P3", "S", hit["rule"], "Düzelt.", "Tarama bu satırı raporlamaz."))
        area = JS_AREAS.get(hit["rule"], "JSD")
        sorun = f"master/static/{hit['file']}:{hit['line']} — {kind}: `{hit['text'][:90]}`."
        by_area.setdefault(area, []).append(item(prio, effort, "F202", f"{hit['file']}:{hit['line']} {kind}", sorun, change, accept))
    return by_area


# ---------------------------------------------------------------- http probes
def http_items():
    by_area: dict[str, list] = {"SMA": [], "SMB": [], "ACK": [], "ACL": [], "HDR": []}
    schema, desc = [], []
    for hit in load("http.json"):
        rule = hit["rule"]
        if rule == "route-without-response-schema":
            schema.append(item("P1", "S", "F203", f"{hit['where']} yanıt şeması", f"{hit['where']}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.", "Pydantic `response_model` ekle ve alanları belgele.", "OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır."))
        elif rule == "route-without-description":
            desc.append(item("P3", "S", "F203", f"{hit['where']} açıklaması", f"{hit['where']}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.", "Kısa amaç, yetki ve hata durumlarını docstring'e yaz.", "OpenAPI `description` dolu."))
        else:
            fix = {
                "header-missing": ("P1", "Eksik güvenlik başlığını orta katmanda ekle.", "Başlık testi bu başlığı doğrular."),
                "csp-unsafe-inline": ("P1", "Satır içi betik/stilleri taşı, nonce kullan, `unsafe-inline`'ı kaldır.", "CSP `unsafe-inline` içermez; arayüz çalışır."),
                "api-no-cache-control": ("P2", "Hassas ve dinamik API yanıtlarına `Cache-Control: no-store` ekle.", "Başlık testi geçer."),
                "no-rate-limit": ("P1", "Token-bucket orta katmanını (`ratelimit.TokenBucket`) tüm API'ye bağla.", "120 hızlı istekte 429 ve Retry-After döner."),
            }.get(rule, ("P2", "Düzelt.", "Yoklama bu bulguyu üretmez."))
            by_area["HDR"].append(item(fix[0], "S", "F203", f"{hit['where']} {rule}", f"{hit['where']}: {hit['text']}.", fix[1], fix[2]))
    by_area["SMA"], by_area["SMB"] = schema[:99], schema[99:]
    by_area["ACK"], by_area["ACL"] = desc[:99], desc[99:]
    return by_area


def py_items():
    out = []
    for hit in sorted(load("py.json"), key=lambda h: (h["rule"], h["where"])):
        if hit["rule"] == "embedded-long-string":
            out.append(item("P2", "M", "F208", f"{hit['where']} gömülü uzun metin", f"{hit['where']}: {hit['text']}; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.", "Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.", "Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında."))
        else:
            out.append(item("P2", "L", "F208", f"{hit['where']} çok büyük modül", f"{hit['where']}: {hit['text']}; test ve inceleme maliyeti yüksek.", "Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.", "Modül ≤ 600 satır; mevcut testler değişmeden geçer."))
    return out


# ---------------------------------------------------------------- absent features
BIG = ("Monaco", "LSP", "Etkileşimli terminal", "Hata ayıklayıcı", "görsel üretimi", "Video", "Masaüstü", "Ajan/asistan oluşturucu", "Telegram", "Tarayıcı eklentisi", "Sesli sohbet", "Zamanlanmış", "Google Drive", "GitHub depo", "OCR", "El yazısı", "İki aşamalı", "antivirüs", "Spice")
HIGH = ("İki aşamalı", "Hesap kilitleme", "antivirüs", "Gizli bilgi tespiti", "Oturum listesi", "Parola gücü", "IP izin")
CAT_AREA = {"Sohbet": "SOH", "Hafıza": "HAF", "Dosya": "DOS", "Kod": "KOD", "Sunum": "SUN", "Araştırma": "ARS", "Medya": "MED", "Veri": "VER", "Ajan": "AJN", "Operasyon": "OPR", "Güvenlik": "GUV", "Entegrasyon": "ENT", "Erişilebilirlik": "ERI", "Eğitim": "EGT", "Alan": "ALN"}


def feature_items():
    by_area: dict[str, list] = {}
    for row in load("features.json"):
        if row["present"]:
            continue
        big = any(token.lower() in row["feature"].lower() for token in BIG)
        prio = "P0" if any(token.lower() in row["feature"].lower() for token in HIGH) else "P1" if row["category"] in ("Güvenlik", "Erişilebilirlik", "Dosya", "Kod", "Araştırma", "Sohbet") else "P2"
        sorun = f"{row['feature']}: kodda ve OpenAPI'de bu yeteneğe ait hiçbir iz bulunamadı (arama deseni `{row['pattern']}` 0 eşleşme)."
        by_area.setdefault(CAT_AREA[row["category"]], []).append(item(prio, "L" if big else "M", "F204", row["feature"], sorun, row["build"] + " (arayüz + API + test).", f"{row['feature']} uçtan uca çalışır; deseni değil davranışı sınayan test ve e2e senaryosu var."))
    return by_area


# ---------------------------------------------------------------- battery failures
def battery_items():
    out = []
    for row in load("battery.json"):
        if row["ok"]:
            continue
        sorun = f"`{row['id']}` ({row['cat']}) gerçek sohbet isteğinde başarısız: {' '.join(row['why'].split())}. Yanıt başı: «{' '.join(row['text'][:140].split())}»."
        out.append(item("P1", "M", "F205", f"{row['cat']}: {row['id']} isteği başarısız", sorun, "Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.", f"`python scripts/audit/battery.py {row['id']}` bu istek için OK verir; eval kümesinde regresyon testi var."))
    return out


UI = [
    ("P1", "S", "Tüm sayfaların başlığı aynı", "8 rotanın tamamında `document.title` 'Dağıtık YZ Yazılım Geliştirme Platformu'; ekran okuyucu ve sekme geçmişi sayfayı ayıramıyor.", "Rota başına başlık ve sayfa değişiminde duyuru.", "Her rotada başlık farklı ve anlamlı (e2e)."),
    ("P1", "S", "6 sayfada birden çok <h1>", "#/new, #/projects, #/agents, #/studios, #/artifacts, #/files rotalarında 2 adet h1 var.", "Kabuk başlığını h1 olmaktan çıkar, sayfa başlığı tek h1 olsun.", "Her sayfada tam 1 h1 (axe)."),
    ("P0", "M", "Stüdyolar sayfasında 341 etiketsiz form kontrolü", "#/studios sayfasında etiketi (label/aria-label) olmayan 341 input/select/textarea var.", "`hub.js` form üreticisi her kontrole `label for` veya `aria-label` versin.", "axe `label` kuralı 0 ihlal."),
    ("P0", "S", "Asistan ana mesaj kutusunun erişilebilir adı yok", "`#promptInput` textarea'sının label/aria-label'ı yok; ekran okuyucu 'düzenleme alanı' diyor.", "aria-label ekle ve gizli label kullan.", "Kutu 'Mesajınızı yazın' adıyla duyurulur."),
    ("P1", "S", "Kabukta 2 etiketsiz dosya girdisi", "Tüm sayfalarda yükleme için 2 gizli `input[type=file]` etiketsiz.", "aria-label ekle veya düğmeye bağla.", "axe `label` ihlali 0."),
    ("P1", "S", "Dar ekranda küçük dokunma hedefleri", "375px'te her sayfada 2–11 öğe 32px'den küçük (Stüdyolar: 11, Asistan: 8).", "Dokunma hedeflerini ≥ 40px yap.", "Mobil denetimde 32px altı hedef 0."),
    ("P2", "S", "Sayfa değişiminde odak yönetimi belirsiz", "Hash rotası değişince odak ana içeriğe taşınmıyor.", "Rota değişince `main` odaklansın ve başlık duyurulsun.", "Klavye kullanıcısı rota değişiminde bağlamını kaybetmez (e2e)."),
]
MISC = [
    ("P0", "M", "F207", "OCR motoru kurulu değil", "`/api/assistant/config`: ocr.available=false ('Kurulu değil (pip install pytesseract)'); taranmış belgeler okunamıyor.", "Tesseract/PaddleOCR'ı kurulum betiğine ve sağlık sihirbazına ekle, kurulmamışsa yükleme anında uyar.", "Taranmış PDF örneği metne çevrilir; OCR yokken kullanıcıya eyleme dönük mesaj çıkar."),
    ("P0", "M", "F207", "Web araması yapılandırılmamış", "`/api/ux/health-wizard` 4/6: web_search ok=false; SEARXNG_URL tanımlı değil, araştırma internetsiz çalışıyor.", "SearXNG'yi kurulum betiğine dahil et, varsayılan açık yap, kapalıysa yanıtta tarih/kaynak uyarısı.", "Güncel bir soruda kaynaklı yanıt gelir; arama yokken uyarı çıkar."),
    ("P1", "S", "F207", "Hiç ajan bağlı değil durumunun yönlendirmesi", "Sağlık sihirbazı: agents ok=false; sohbet tek düğümde çalışıyor ama kullanıcıya dağıtık özelliğin kapalı olduğu yanıtta söylenmiyor.", "Yanıt meta verisine 'yerel yürütme' rozeti ve ajan ekleme önerisi ekle.", "Ajan yokken yanıtta nedeni gösteren rozet var."),
    ("P1", "M", "F207", "Frontend araç zinciri yok", "frontend/package.json `lint`, `typecheck`, `build`, `e2e` betikleri tanımlı ama devDependencies, eslint/tsconfig/vite/playwright yapılandırması ve node_modules yok; betikler çalışmaz.", "Bağımlılıkları ve yapılandırmayı ekle, CI'da çalıştır.", "`npm run lint`, `typecheck`, `e2e` temiz klonda çalışır."),
    ("P1", "S", "F207", "`npm test` yalnız 1 test dosyasını koşuyor", "package.json `test` betiği yalnız `ui_modules.test.mjs`; `message_tools` ve `undefined_names` testleri çalışmıyor.", "Betiği `node --test tests/` yap.", "`npm test` 3 dosyanın tamamını koşar."),
    ("P1", "S", "F207", "Kapsam aracı dev bağımlılığı değil", "`requirements-dev.txt` yalnız pytest ve ruff; CI `pytest-cov`'u ad hoc kuruyor, yerelde kapsam ölçülemiyor.", "`pytest-cov` ve `diff-cover`'ı dev bağımlılığı yap.", "Yerelde `pytest --cov` çalışır."),
    ("P0", "M", "F207", "Oturumsuz kullanıcı profili oluşturma/üzerine yazma (IDOR)", "`PUT /api/user/zzz-nonexistent/profile` oturumsuz 200 verip profil oluşturdu; `GET /api/user/profiles` tüm kullanıcı kimliklerini listeledi.", "Kimliği oturumdan türet, liste rotasını yöneticiye kısıtla.", "Oturumsuz çağrı 401; başka kimliğe yazma 403 (otomatik üretilmiş test)."),
    ("P0", "M", "F207", "Oturumsuz 8 /api/user/* rotası veri döndürüyor", "profile, stats, memories, conversations, history/search, personalization-preview rotaları oturumsuz 200 verdi.", "Hepsine oturum ve sahiplik bağımlılığı ekle.", "Her rota için A→B sızıntı testi 404/403."),
    ("P1", "S", "F207", "enterprise-status yerel dosya yolu sızdırıyor", "`GET /api/assistant/enterprise-status` yanıtı `llmops.dpo_file` alanında tam yerel yol (C:\\Users\\...) içeriyor.", "Yolları göreli yap veya yöneticiye göster.", "Yanıtta mutlak yol yok."),
    ("P2", "S", "F207", "GET /api/gateway/models 3 sn sürüyor", "İlk çağrı 3.1 sn; her açılışta model listesi arayüzü yavaşlatıyor.", "Sonucu önbellekle ve arka planda yenile.", "Önbellekli çağrı < 100 ms."),
    ("P1", "S", "F207", "İki sanal ortam (`venv` ve `.venv`) master içinde", "`master/venv` ve `master/.venv` birlikte var; hangi Python'un kullanıldığı belirsiz (sunucu sistem Python'uyla başladı).", "Tek ortam kullan, `.gitignore` ve betikler aynı yolu göstersin.", "Tek sanal ortam; betikler ve launch.json aynısını kullanır."),
    ("P1", "M", "F207", "Plan v2 UX-05: prefers-reduced-motion yok", "Plan 'done' dedi ama CSS/JS'de `prefers-reduced-motion` eşleşmesi yok.", "Medya sorgusu ve ayar ekle, testle sabitle.", "Azaltılmış hareketle animasyon yok (test)."),
    ("P1", "M", "F207", "Plan v2 IDE-10: Monaco yerel paketi yok", "Plan 'done' dedi ama `static/vendor` yok, Monaco/CodeMirror eşleşmesi yok.", "Çevrimdışı Monaco paketi ekle.", "IDE Monaco ile açılır (e2e)."),
    ("P1", "M", "F207", "Plan v2 SEC-04: rol matrisi route'lara bağlı değil", "`auth/policy.py` bu oturumda yazıldı; route bağımlılığı olarak uygulanmıyor.", "Router düzeyinde `require_role` uygula.", "Her mutasyon rotası rol testinden geçer."),
    ("P1", "M", "F207", "Plan v2 OPS-09: pytest işaretleri eksik", "`pytest.ini` yalnız `security` işaretini tanımlıyor; unit/contract/integration/e2e/slow yok.", "Altı işareti tanımla, her teste ata.", "İşaretsiz test CI'ı kırar; hızlı küme < 30 sn."),
]


PKT_STEPS = [
    ("Tasarım belgesi ve ADR", "S", "Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.", "ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi."),
    ("Veri modeli ve göç", "M", "Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.", "Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar."),
    ("Çekirdek mantık", "L", "{change}", "Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır."),
    ("API ve yanıt şemaları", "M", "Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.", "Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel."),
    ("Arayüz ve erişilebilirlik", "M", "Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.", "axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır."),
    ("Birim ve sözleşme testleri", "M", "Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.", "Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır."),
    ("Hata enjeksiyonu ve dayanıklılık", "M", "Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.", "Her hata türünde beklenen davranış ve mesaj doğrulanır."),
    ("Güvenlik ve gizlilik incelemesi", "S", "Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.", "Tehdit satırı ve ilgili güvenlik testleri geçer."),
    ("Uçtan uca senaryo ve eval kümesi", "M", "Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.", "e2e CI'da koşar; eval raporu üretilir."),
    ("Ölçüm, belge ve runbook", "M", "Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.", "{accept}"),
]


def package_items(epics):
    out = []
    index = 0
    for number, (prio, _, title, problem, change, accept) in enumerate(epics, 1):
        previous = None
        for step, (name, effort, text, acc) in enumerate(PKT_STEPS, 1):
            area = "PK" + chr(65 + index // 99)
            this_id = f"{area}-{index % 99 + 1:02d}"
            out.append(item(prio, effort, "-", f"EPK-{number:02d} · {name}: {title[:60]}", f"Program EPK-{number:02d} «{title}» iş paketi {step}/{len(PKT_STEPS)}. Bağlam: {problem}", text.format(change=change, accept=accept), acc.format(change=change, accept=accept), deps=previous or "-"))
            previous = this_id
            index += 1
    return out


def build():
    PLAN.mkdir(parents=True, exist_ok=True)
    ruff, js, http, feats = ruff_items(), js_items(), http_items(), feature_items()
    battery = battery_items()
    pyd = py_items()
    ui = [item(p, e, "F206", t, s, c, a) for p, e, t, s, c, a in UI]
    misc = [item(p, e, f, t, s, c, a) for p, e, f, t, s, c, a in MISC]
    epics = [item(p, e, "-", t, s, c, a) for p, e, t, s, c, a in EPICS]
    packages = package_items(EPICS)

    files = [
        ("01-dogrulanmis-eksik-yetenekler.md", "Parça 1 — Doğrulanmış eksik yetenekler (kodda iz bulunamayan özellikler)", [(code, f"Eksik yetenek: {cat}", feats[code]) for cat, code in CAT_AREA.items() if code in feats]),
        ("02-davranis-arayuz-ve-sistem.md", "Parça 2 — Gerçek istek başarısızlıkları, arayüz taraması ve sistem bulguları", [("DAV", "Gerçek sohbet isteğinde başarısız davranışlar", battery), ("ARY", "Tarayıcı taraması: arayüz ve erişilebilirlik", ui), ("ALT", "Doğrulanmış sistem ve altyapı bulguları", misc)]),
        ("03-api-sozlesmesi-ve-guvenlik.md", "Parça 3 — API sözleşmesi, başlıklar ve güvenlik yoklaması", [("HDR", "HTTP başlıkları, hız sınırı ve önbellek", http["HDR"]), ("SMA", "Yanıt şeması eksik route'lar (1)", http["SMA"]), ("SMB", "Yanıt şeması eksik route'lar (2)", http["SMB"]), ("ACK", "Açıklaması eksik route'lar (1)", http["ACK"]), ("ACL", "Açıklaması eksik route'lar (2)", http["ACL"])]),
        ("04-python-statik-1.md", "Parça 4 — Python statik analiz bulguları (1)", [("BLE", "Python: kapsamsız except", ruff.get("BLE", [])), ("KMP", "Python: karmaşık fonksiyonlar", ruff.get("KMP", []))]),
        ("05-python-statik-2.md", "Parça 5 — Python statik analiz bulguları (2)", [("PYD", "Python: gömülü uzun metinler ve büyük modüller", pyd), ("PRM", "Python: çok parametreli fonksiyonlar", ruff.get("PRM", [])), ("DAL", "Python: çok dallı fonksiyonlar", ruff.get("DAL", [])), ("UZN", "Python: çok uzun fonksiyonlar", ruff.get("UZN", [])), ("SQL", "Python: dinamik SQL dizeleri", ruff.get("SQL", [])), ("STA", "Python: diğer statik analiz bulguları", ruff.get("STA", []))]),
        ("06-arayuz-statik.md", "Parça 6 — Arayüz statik tarama bulguları", [("XSS", "JS: innerHTML atamaları", js.get("XSS", [])), ("AGH", "JS: hata yolu olmayan fetch çağrıları", js.get("AGH", [])), ("JSD", "JS/CSS/HTML: diğer bulgular", js.get("JSD", []))]),
        ("07-yol-haritasi-epikler.md", "Parça 7 — Yol haritası programları (öneri)", [("EPK", "Çok aylık programlar", epics)]),
        ("08-yol-haritasi-is-paketleri.md", "Parça 8 — Programların iş paketleri (öneri, WBS)", [("PK" + chr(65 + i), f"İş paketleri ({i + 1})", packages[i * 99:(i + 1) * 99]) for i in range((len(packages) + 98) // 99)]),
    ]
    total = 0
    counts = {}
    for filename, heading, areas in files:
        lines = [f"# {heading}", ""]
        for code, title, items in areas:
            if not items:
                continue
            assert len(items) <= 99, (code, len(items))
            lines += [f"## {code} · {title}", ""]
            for number, it in enumerate(items, 1):
                total += 1
                counts[it["finding"]] = counts.get(it["finding"], 0) + 1
                dep_text = it["deps"]
                tag = f"[DOĞRULANDI: {it['finding']}]" if it["finding"] != "-" else "[ÖNERİ]"
                lines += [f"#### {code}-{number:02d} · {it['title'][:110]}", f"- **Sorun:** {tag} {it['sorun']}", f"- **Değişiklik:** {it['change']}", f"- **Kabul:** {it['accept']}", f"- **Meta:** {it['prio']} · {it['effort']} · Bağ: {dep_text} · Durum: açık", ""]
        (PLAN / filename).write_text("\n".join(lines), encoding="utf-8")
    return total, counts


if __name__ == "__main__":
    total, counts = build()
    print(total, "madde", counts)


README = """# Plan v3 — doğrulanmış eksikler ve yol haritası

**{total} madde.** Bunların **{verified}'i doğrulanmış bulgu** (çalıştırılmış bir yoklama, tarama veya gerçek istek ürettiği kanıta bağlı), **{epics}'i yol haritası** (34 program ve 340 iş paketi; `[ÖNERİ]`, 07 ve 08 numaralı dosyalarda).

Önceki taslak (566 aday öneri) `aday-oneriler/` altında duruyor; orada çoğu madde henüz doğrulanmadı ve sayıya dahil değildir.

## 1. Bu plan nasıl üretildi

Proje bu oturumda izole bir sunucuda (port 8099, geçici veri) gerçekten çalıştırıldı ve beş yolla incelendi:

1. **HTTP yoklaması:** 162 route'a istek, başlık/CORS/hız sınırı/bozuk JSON/yol geçişi/şema kontrolleri.
2. **Gerçek sohbet bataryası:** {battery_total} istek gerçek modele (qwen3.5) gönderildi, yanıtlar makinece denetlendi (olgusal, hesap, talimat, kod çalıştırma, dosya, güvenlik, üretim istekleri).
3. **Eksik yetenek taraması:** ChatGPT/Claude/Gemini sınıfı asistanların sunduğu {feature_total} yetenek için kodda ve OpenAPI'de iz arandı; **hiç iz bulunmayanlar** madde yapıldı.
4. **Statik analiz:** ruff (güvenlik, karmaşıklık, hata yutma, dinamik SQL) ve arayüz kaynak taraması.
5. **Tarayıcı taraması:** 8 sayfa açılıp konsol/ağ/erişilebilirlik ve mobil denetimi yapıldı.

Kanıt dosyaları `kanit/` altındadır; yoklama betikleri `scripts/audit/` altındadır ve yeniden çalıştırılabilir.

## 2. Denetim bulguları (yeniden üretilebilir)

Komutlar repo kökünde çalıştırılır. Sunucu: `$env:DB_PATH="$PWD\.audit_tmp\data\platform.db"; master\venv\Scripts\python.exe -m uvicorn app:app --app-dir master --port 8099`.

| Kod | Bulgu | Yeniden üretme | Durum |
|---|---|---|---|
| F201 | {c201} Python statik analiz bulgusu (kapsamsız except, karmaşık/uzun fonksiyon, dinamik SQL, alt süreç) | `master\venv\Scripts\python.exe -m ruff check master --isolated --select C901,PLR0912,PLR0915,PLR0913,BLE001,S110,S608,S603,S607` | Açık |
| F202 | {c202} arayüz kaynak bulgusu (innerHTML, hata yolu olmayan fetch, uzun fonksiyon, odak halkası) | `master\venv\Scripts\python.exe scripts/audit/scan_js.py out.json` | Açık |
| F203 | {c203} HTTP bulgusu: 188 route'un 200 yanıtında şema yok, 138'inde açıklama yok, eksik güvenlik başlıkları, hız sınırı yok | `master\venv\Scripts\python.exe scripts/audit/probe_http.py out.json` | Açık |
| F204 | {c204} yetenek için kodda ve OpenAPI'de hiç iz yok | `master\venv\Scripts\python.exe scripts/audit/features.py out.json` | Açık |
| F205 | {c205} gerçek sohbet isteği başarısız | `master\venv\Scripts\python.exe scripts/audit/battery.py` | Açık |
| F206 | {c206} tarayıcı bulgusu (aynı başlık, çoklu h1, 341 etiketsiz kontrol, küçük hedefler) | Tarayıcıda 8 rota gezilir (bkz. kanit/ui.md) | Açık |
| F208 | {c208} Python kaynak bulgusu (gömülü uzun prompt/metin, 600 satırı aşan modül) | `master\venv\Scripts\python.exe scripts/audit/scan_py.py out.json` | Açık |
| F207 | {c207} sistem bulgusu (OCR yok, web araması yok, IDOR, frontend araç zinciri yok, plan v2 iddiaları) | Her maddenin 'Sorun' satırındaki komut/endpoint | Açık |

## 3. Dürüstlük notları

- **F204** "bulunamadı", kod okunarak değil desen aranarak belirlendi. Desen 0 eşleşme verdiyse özellik yoktur; ancak özellik farklı adla yazılmışsa yanlış negatif olabilir. Her maddenin Kabul satırı bu yüzden *davranışı* sınayan testi ister.
- **F201/F202** araç bulgularıdır: gerçek ve konumludur, ama her biri hata değildir (ör. bir `innerHTML` sabit metin olabilir). Kabul satırı bunu ayırt etmek için inceleme ister.
- Yoklama izole sunucuda yapıldı; üretim verisine dokunulmadı.
- Sayı, kalite değil kapsamdır. Öncelik: P0 ve P1 maddeleri önce.

## 4. Kurallar

1. `python scripts/plan_tool.py --plan-dir docs/plan-v3 check` yapıyı doğrular.
2. Plan dosyaları yalnız "Durum: açık" der; ilerleme `PROGRESS.json`'dadır.
3. `done` için testin madde kimliğini taşıması, commit ve kabul ölçütünün ölçülmesi gerekir.
4. Düzeltme sonrası ilgili yoklama betiği yeniden çalıştırılır; bulgu kaybolmalıdır.
"""


def write_readme(total, counts):
    feature_total = len(load("features.json"))
    battery_total = len(load("battery.json"))
    verified = sum(v for k, v in counts.items() if k != "-")
    text = README.format(
        total=total, verified=verified, epics=counts.get("-", 0), battery_total=battery_total, feature_total=feature_total,
        c201=counts.get("F201", 0), c202=counts.get("F202", 0), c203=counts.get("F203", 0), c204=counts.get("F204", 0),
        c205=counts.get("F205", 0), c206=counts.get("F206", 0), c207=counts.get("F207", 0), c208=counts.get("F208", 0),
    )
    (PLAN / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    total, counts = build()
    write_readme(total, counts)
    print("README yazıldı:", total)
