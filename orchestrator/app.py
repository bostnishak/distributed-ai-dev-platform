import io
import os
import re
from pathlib import Path

import httpx
from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader

STATIC_DIR = Path(__file__).resolve().parent / "static"

# .env repo kokunde tek bir yerde duruyor (bu dosyadan bir ust dizin) -- kopya tutmuyoruz.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://localhost:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY")

app = FastAPI(title="Coklu-LLM Orkestrator")

# Siniflandirma icin kullanilan model. 2026-09-25: baslangicta en hafif model (uye6-qwen-light,
# 1.7B) kullanildi ama gercek testte hem hakaret tespitinde yanlis pozitif (masum bir kod
# istegini "uygunsuz" isaretledi) hem de kategori tespitinde hata (acik bir "uygulama yap"
# istegini "kod" yerine "genel"e yonlendirdi) verdigi goruldu. uye2-phi4mini (3.8B) de ayni
# testte yanlis "UYGUNSUZ: evet" dedi ve talimatlari tekrarladi. uye1-qwen (Qwen3.5 4B) ayni
# testlerde her seferinde doğru/temiz formatta yanit verdi -- daha yavas (~7sn) ama daha
# guvenilir oldugu icin secildi. Yanlislikla engellemek/yanlis yonlendirmek, birkac saniye
# kaybetmekten daha kotu bir sonuc.
CLASSIFIER_MODEL = "uye1-qwen"

# Gorev tipi -> hangi gateway model_name'ine gidecek + thinking acik/kapali.
# 2026-09-25: kullanici kendi model secmek istemiyor -- siniflandirma otomatik yapiliyor
# (bkz. classify_and_moderate, ayni cagri icinde hakaret/uygunsuzluk kontrolu de yapiyor).
# "genel" icin kullanici bilinci ile sabit bir varsayilan model secildi (5 genel model
# arasinda net bir kalite farki olmadigi icin fan-out+judge yerine basit/hizli yaklasim
# tercih edildi).
#
# ONEMLI (veri gizliligi karari, 2026-09-25): Bu sistem TAMAMEN LOKAL calisir, hicbir bulut
# API'ye (Groq/Gemini/OpenRouter) veri gonderilmez -- plandan tamamen cikarildi. Bu yuzden
# "analiz" (belge/gorsel) gorev tipi icin bulut tabanli bir cozum YOK. PDF/DOCX/metin
# dosyalari gercekten okunup metne cevriliyor (asagida), ama GERCEK GORSEL (foto) analizi
# icin lokal bir vision modeli gerekiyor -- henuz eklenmedi.
#
# ONEMLI: qwen2.5-coder:7b "thinking" desteklemiyor (Qwen3 ailesinin aksine) -- think:true
# gonderilirse Ollama 400 hatasi donuyor (dogrulandi, 2026-09-25). "kod" icin think hep False.
#
# ONEMLI: "analiz" icin think:true idi ama gercek CV/dosya testinde bu, buyukce bir belge
# metniyle birlesince yaniti dakikalarca "dusunme" surecine sokup pratikte donmus gibi
# gorunmesine sebep oldu (dogrulandi, 2026-09-25) -- dosya analizinde think hep False olmali.
TASK_ROUTES = {
    "genel": {"model": "uye1-qwen", "think": False},
    "kod": {"model": "uye5-coder", "think": False},
    "analiz": {"model": "uye1-qwen", "think": False},  # TODO: lokal vision modeli eklenince degistir
}
DEFAULT_TASK = "genel"

MODEL_LABELS = {
    "uye1-qwen": "Üye-1 · Qwen3.5 4B",
    "uye2-phi4mini": "Üye-2 · Phi-4-mini",
    "uye3-llama": "Üye-3 · Llama 3.2",
    "uye4-gemma": "Üye-4 · Gemma 4",
    "uye5-coder": "Üye-5 · Qwen2.5-Coder",
    "uye6-qwen-light": "Üye-6 · Qwen3 1.7B",
}


async def call_gateway(model: str, prompt: str, think: bool) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": think,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            resp = await client.post(
                f"{GATEWAY_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Gateway hatasi: {exc}") from exc
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# LLM siniflandirici (uye1-qwen ile bile) gercek testte acik kod isteklerini bazen "genel"e
# yonlendirdi. Basit bir anahtar kelime kontrolu, bariz durumlarda LLM'in hatasini duzeltmek
# icin bir guvenlik agi olarak eklendi (2026-09-25, kullanicinin talebiyle) -- tam bir cozum
# degil, sadece acik/belirgin ifadeler icin LLM'in ustune yazar.
CODE_KEYWORDS = (
    "python", "javascript", "typescript", "java ", "c++", "c#", " sql",
    "kod yaz", "kodu yaz", "fonksiyon yaz", "script yaz", "program yaz",
    "uygulama yap", "uygulama yaz", "algoritma yaz", "class yaz", "sinif yaz",
    "hata ayikla", "debug et", "kodda hata", "bug'i duzelt", "hesap makinesi",
)


def keyword_category_override(prompt: str) -> str | None:
    lowered = prompt.lower()
    if any(kw in lowered for kw in CODE_KEYWORDS):
        return "kod"
    return None


async def classify_and_moderate(prompt: str) -> tuple[str, bool]:
    """Tek bir siniflandirici model cagrisiyla hem gorev kategorisini hem de mesajin
    hakaret/kufur icerip icermedigini (baglama gore) belirler -- iki ayri cagri yerine.

    NOT (2026-09-25, gercek test batisinda bulundu): kucuk 1.7B model bazen istenen formati
    tam takip etmiyor (bir seferinde sablonu -"kod|analiz|genel"- oldugu gibi kopyaladi) ve
    ayni mesaj icin farkli caliştirmalarda farkli sonuc verebiliyor (kucuk modellerin bilinen
    tutarsizligi). Bu yuzden parse SIKI regex ile yapiliyor ve format taninmazsa "fail-open"
    davraniliyor (UYGUNSUZ degil sayilir) -- yanlislikla engellemek, yanlislikla gecirmekten
    daha kotu bir kullanici deneyimi (dogrulandi: masum kod/dosya istekleri yanlislikla
    engellenmisti)."""
    # NOT (2026-09-25): "analiz" kategorisi burada siniflandiriciya SORULMUYOR -- dosya
    # ekliyse zaten /chat handler'inda forced_task_type="analiz" ile zorlaniyor (dosya yoksa
    # "analiz" kavraminin metin-only bir mesaj icin anlami yok). Bunu siniflandiriciya secenek
    # olarak sormak, genel/duygusal sorularin da yanlislikla "analiz"e dusmesine sebep oluyordu
    # (dogrulandi, 2026-09-25) -- kaynaginda kaldirildi.
    classifier_prompt = (
        "Kullanici mesajini degerlendirip ASAGIDAKI IKI SATIRI BIREBIR bu bicimde yaz "
        "(ornek deger olarak 'kod' ve 'hayir' yazdim, kendi degerlendirmene gore degistir), "
        "baska hicbir aciklama ekleme:\n"
        "KATEGORI: kod\n"
        "UYGUNSUZ: hayir\n\n"
        "KATEGORI icin sadece su ikisinden birini yaz (kod / genel):\n"
        "kod = kod yazma, program/uygulama gelistirme, hata ayiklama istekleri\n"
        "genel = bunlarin disindaki her sey (soru-cevap, sohbet, bilgi edinme, duygusal konular)\n\n"
        "UYGUNSUZ icin sadece evet/hayir yaz:\n"
        "evet = mesaj acikca hakaret/kufur/asagilama iceriyor\n"
        "hayir = icermiyor -- baglami dikkate al: 'mal' kelimesi ticari baglamda (ör. "
        "'3 ton mal') UYGUNSUZ degildir, ama hakaret olarak (ör. 'sen malsin') kullanilirsa "
        "UYGUNSUZDUR\n\n"
        f'Degerlendirilecek mesaj: "{prompt}"'
    )
    try:
        result = await call_gateway(CLASSIFIER_MODEL, classifier_prompt, think=False)
    except HTTPException:
        return DEFAULT_TASK, False
    return parse_classifier_response(result)


def parse_classifier_response(result: str) -> tuple[str, bool]:
    """classify_and_moderate'in gateway'den aldigi ham metni ayristirir. Ayri bir saf
    fonksiyon olarak tutuluyor ki gercek bir model/gateway calismadan test edilebilsin
    (bkz. tests/test_app.py)."""
    # Model bazen kalin yazi (**) veya sablon isaretleri (<>) ekliyor -- once temizle.
    result_clean = result.replace("*", "").replace("<", "").replace(">", "")

    category_match = re.search(r"KATEGORI:\s*(kod|genel)\b", result_clean, re.IGNORECASE)
    category = category_match.group(1).lower() if category_match else DEFAULT_TASK

    inappropriate_match = re.search(r"UYGUNSUZ:\s*(evet|hayir)\b", result_clean, re.IGNORECASE)
    inappropriate = bool(inappropriate_match and inappropriate_match.group(1).lower() == "evet")

    return category, inappropriate


def extract_pdf_text(raw: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(raw: bytes) -> str:
    doc = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs)


class ChatResponse(BaseModel):
    content: str
    used_model: str
    task_type: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def chat_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/chat", response_model=ChatResponse)
async def chat(prompt: str = Form(...), file: UploadFile | None = File(None)):  # noqa: B008 (FastAPI'nin standart deseni)
    file_note = ""
    extracted_text = ""
    forced_task_type = None

    if file is not None and file.filename:
        name = file.filename.lower()
        content_type = file.content_type or ""
        raw = await file.read()

        if content_type.startswith("image/"):
            file_note = (
                f"\n\n[Not: '{file.filename}' bir görsel dosyası. Bu sistemde henüz gerçek "
                "bir görsel analiz modeli yok (veri gizliliği kararıyla bulut vision API'leri "
                "kullanılmıyor, yerel bir vision modeli henüz eklenmedi), bu yüzden içeriği "
                "değerlendirilemedi.]"
            )
            forced_task_type = "analiz"
        elif name.endswith(".pdf"):
            extracted_text = extract_pdf_text(raw)
            forced_task_type = "analiz"
        elif name.endswith(".docx"):
            extracted_text = extract_docx_text(raw)
            forced_task_type = "analiz"
        elif name.endswith(".txt") or content_type.startswith("text/"):
            extracted_text = raw.decode("utf-8", errors="ignore")
            forced_task_type = "analiz"
        else:
            file_note = f"\n\n[Not: '{file.filename}' desteklenmeyen bir dosya türü.]"

    classified_task, inappropriate = await classify_and_moderate(prompt)

    if inappropriate:
        return ChatResponse(
            content=(
                "Bu mesaj hakaret/uygunsuz ifade içerebilecek şekilde değerlendirildi, "
                "bu yüzden bir modele iletilmedi. Lütfen sorunu farklı bir şekilde ifade et."
            ),
            used_model="moderation",
            task_type="engellendi",
        )

    full_prompt = prompt
    if extracted_text:
        full_prompt = f"{prompt}\n\n--- Eklenen dosya içeriği ---\n{extracted_text[:8000]}"
    full_prompt += file_note

    task_type = forced_task_type or keyword_category_override(prompt) or classified_task
    route = TASK_ROUTES[task_type]
    content = await call_gateway(route["model"], full_prompt, route["think"])

    return ChatResponse(content=content, used_model=route["model"], task_type=task_type)
