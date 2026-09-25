import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# .env repo kokunde tek bir yerde duruyor (bu dosyadan bir ust dizin) -- kopya tutmuyoruz.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://localhost:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY")

app = FastAPI(title="Coklu-LLM Orkestrator")

# Gorev tipi -> hangi gateway model_name'ine gidecek + thinking acik/kapali.
# 2026-09-25: uye2..uye6 test edildi ve calistigi dogrulandi -- "kod" -> uye5-coder testi
# gercek dogru Python kodu dondurdu. Arkadaslar kendi makinelerinde calisip gateway'e
# baglandiklarini kullanici kendi dogrulayana kadar bu 5 model bu makinede (staging) kalacak.
#
# ONEMLI (veri gizliligi karari, 2026-09-25): Bu sistem TAMAMEN LOKAL calisir, hicbir bulut
# API'ye (Groq/Gemini/OpenRouter) veri gonderilmez -- plandan tamamen cikarildi. Bu yuzden
# "analiz" (belge/gorsel) gorev tipi icin bulut tabanli bir cozum YOK. Gercek dosya/gorsel
# analizi icin ileride kucuk bir LOKAL vision modeli (ör. Moondream2, Qwen2.5-VL-3B) eklenmesi
# gerekiyor -- henuz eklenmedi, bu yuzden "analiz" simdilik metin-only Uye-1'e dusuyor ve
# gercekte gorsel/PDF isleyemez (bunu varsayimla "calisiyor" gibi gostermiyoruz).
#
# ONEMLI: qwen2.5-coder:7b "thinking" desteklemiyor (Qwen3 ailesinin aksine) -- think:true
# gonderilirse Ollama 400 hatasi donuyor (dogrulandi, 2026-09-25). "kod" icin think hep False.
TASK_ROUTES = {
    "genel": {"model": "uye1-qwen", "think": False},
    "kod": {"model": "uye5-coder", "think": False},
    "analiz": {"model": "uye1-qwen", "think": True},  # TODO: lokal vision modeli eklenince degistir
}
DEFAULT_TASK = "genel"


class ChatRequest(BaseModel):
    prompt: str
    task_type: str | None = None


class ChatResponse(BaseModel):
    content: str
    used_model: str
    task_type: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    task_type = req.task_type if req.task_type in TASK_ROUTES else DEFAULT_TASK
    route = TASK_ROUTES[task_type]

    payload = {
        "model": route["model"],
        "messages": [{"role": "user", "content": req.prompt}],
        "think": route["think"],
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
    content = data["choices"][0]["message"]["content"]

    return ChatResponse(content=content, used_model=route["model"], task_type=task_type)
