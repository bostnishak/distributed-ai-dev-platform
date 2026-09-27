"""Assistant tab: the chat assistant that existed before the platform pivot.

It still talks to the models through the LiteLLM gateway. Sprint 3 moves it onto the agent
infrastructure (PB-36); until then its behaviour is intentionally unchanged.
"""

import re

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

import config
from extract import extract_docx_text, extract_pdf_text

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# Classifier model. Verified on 2026-09-25: the 1.7B model flagged harmless code requests as
# insulting and misrouted an explicit "build an app" request; phi4-mini also echoed the
# instructions. Qwen3.5 4B answered cleanly every time. It is slower (~7 s), but a wrong block
# or wrong route costs the user more than a few seconds.
CLASSIFIER_MODEL = "uye1-qwen"

# Task type -> gateway model name + thinking on/off. The user does not pick a model; the
# classifier decides. Verified constraints:
# - qwen2.5-coder:7b does not support thinking; think:true returns HTTP 400.
# - With think:true, file analysis spent minutes "thinking" on long documents and looked frozen.
TASK_ROUTES = {
    "genel": {"model": "uye1-qwen", "think": False},
    "kod": {"model": "uye5-coder", "think": False},
    "analiz": {"model": "uye1-qwen", "think": False},
}
DEFAULT_TASK = "genel"

# The UI can render Markdown tables and ```svg blocks; the model only uses them if told so.
# Kept out of the classifier call so it cannot disturb the classifier's strict output format.
ANSWER_SYSTEM_PROMPT = (
    "Yanit verirken uygun oldugunda bicimlendirme kullan: karsilastirma/liste gibi "
    "yapili bilgiler icin Markdown tablosu (| basli | basli |\\n|---|---|\\n| hucre | hucre |), "
    "kume/diyagram/sema gibi gorsel bir anlatim daha faydali olacaksa ```svg ile baslayan "
    "bir SVG kod blogu (basit sekiller, dogrudan cizim olarak gosterilecek). Zorunlu degil, "
    "sadece gercekten faydali oldugunda kullan."
)

# The LLM classifier occasionally routed explicit code requests to "genel". These keywords
# act as a safety net that overrides the classifier for obvious cases only.
CODE_KEYWORDS = (
    "python", "javascript", "typescript", "java ", "c++", "c#", " sql",
    "kod yaz", "kodu yaz", "fonksiyon yaz", "script yaz", "program yaz",
    "uygulama yap", "uygulama yaz", "algoritma yaz", "class yaz", "sinif yaz",
    "hata ayikla", "debug et", "kodda hata", "bug'i duzelt", "hesap makinesi",
)


async def call_gateway(model: str, prompt: str, think: bool, system_prompt: str | None = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "think": think}
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            resp = await client.post(
                f"{config.GATEWAY_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {config.LITELLM_MASTER_KEY}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Gateway hatasi: {exc}") from exc
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def keyword_category_override(prompt: str) -> str | None:
    lowered = prompt.lower()
    if any(kw in lowered for kw in CODE_KEYWORDS):
        return "kod"
    return None


async def classify_and_moderate(prompt: str) -> tuple[str, bool]:
    """One classifier call decides both the task category and whether the message is insulting.

    Small models do not always follow the format and can answer differently for the same
    message, so parsing is strict and fails open: an unrecognised answer counts as not
    inappropriate. Wrongly blocking a harmless request was the worse outcome in testing.
    "analiz" is not offered to the classifier: attachments already force it, and offering it
    pulled plain questions into "analiz".
    """
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
    """Parse the classifier's raw answer; a pure function so it is testable without a model."""
    # Models sometimes add bold markers (**) or template brackets (<>).
    result_clean = result.replace("*", "").replace("<", "").replace(">", "")

    category_match = re.search(r"KATEGORI:\s*(kod|genel)\b", result_clean, re.IGNORECASE)
    category = category_match.group(1).lower() if category_match else DEFAULT_TASK

    inappropriate_match = re.search(r"UYGUNSUZ:\s*(evet|hayir)\b", result_clean, re.IGNORECASE)
    inappropriate = bool(inappropriate_match and inappropriate_match.group(1).lower() == "evet")

    return category, inappropriate


class ChatResponse(BaseModel):
    content: str
    used_model: str
    task_type: str


@router.post("/chat", response_model=ChatResponse)
async def chat(prompt: str = Form(...), file: UploadFile | None = File(None)):  # noqa: B008 (standard FastAPI pattern)
    file_note = ""
    extracted_text = ""
    forced_task_type = None

    if file is not None and file.filename:
        name = file.filename.lower()
        content_type = file.content_type or ""
        raw = await file.read()

        if content_type.startswith("image/"):
            file_note = (
                f"\n\n[Not: '{file.filename}' bir görsel dosyası. Görsel analizi henüz "
                "bağlanmadı; Sprint 3'te görseller, görsel anlayabilen ajanlara (Qwen3.5 4B, "
                "Gemma 4 E4B) yönlendirilecek. Bu yüzden içeriği değerlendirilemedi.]"
            )
            forced_task_type = "analiz"
        elif name.endswith(".pdf"):
            extracted_text = extract_pdf_text(raw)
            forced_task_type = "analiz"
        elif name.endswith(".docx"):
            extracted_text = extract_docx_text(raw)
            forced_task_type = "analiz"
        elif name.endswith((".txt", ".md")) or content_type.startswith("text/"):
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
    content = await call_gateway(route["model"], full_prompt, route["think"], system_prompt=ANSWER_SYSTEM_PROMPT)

    return ChatResponse(content=content, used_model=route["model"], task_type=task_type)
