from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE", "")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "ok", "message": "bot rodando"}

# --------- TESTE MANUAL (opcional) ----------
@app.post("/chat")
async def chat(req: ChatRequest):
    reply = await generate_reply(req.message)
    return {"reply": reply}

# --------- WEBHOOK DA Z-API ----------
@app.post("/zapi")
async def zapi_webhook(request: Request):
    payload = await request.json()

    # Tenta achar o telefone e a mensagem em vários formatos (porque cada Z-API manda diferente)
    phone = (
        payload.get("phone")
        or payload.get("from")
        or payload.get("sender")
        or (payload.get("data") or {}).get("phone")
        or (payload.get("data") or {}).get("from")
    )

    text = (
        payload.get("message")
        or payload.get("text")
        or (payload.get("data") or {}).get("message")
        or (payload.get("data") or {}).get("text")
    )

    # Se não veio texto, só confirma "ok" (evita quebrar)
    if not phone or not text:
        return {"ok": True, "note": "sem phone/text no payload"}

    # Gera resposta com IA
    reply = await generate_reply(text)

    # Envia resposta pelo Z-API
    await send_zapi_message(phone, reply)

    return {"ok": True}

async def generate_reply(user_text: str) -> str:
    if not OPENAI_API_KEY:
        return "Tô sem sistema agora 😕 tenta de novo já já."

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": (
            "Responda curto, natural e humano, em português do Brasil, como WhatsApp. "
            "Se faltar informação, faça 1 pergunta curta.\n\n"
            f"Cliente: {user_text}"
        )
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        data = r.json()

    texto = ""
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                texto += c.get("text", "")

    texto = texto.strip()
    return texto or "Me diz só um detalhe pra eu te responder certinho 😉"

async def send_zapi_message(phone: str, text: str):
    # Se estiver faltando as variáveis, não quebra
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        return

    # ATENÇÃO: esse endpoint pode variar por conta/plano da Z-API.
    # Se não enviar, a gente ajusta pelo “Postman Collection” que aparece no seu painel.
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    body = {"phone": phone, "message": text}

    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json=body)
