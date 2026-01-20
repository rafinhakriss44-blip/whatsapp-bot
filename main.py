from fastapi import FastAPI, Request
import os
import httpx

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE", "")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "")

@app.get("/")
def home():
    return {"status": "ok", "message": "bot rodando"}

@app.post("/zapi")
async def zapi_webhook(request: Request):
    payload = await request.json()

    print("ZAPI payload recebido")

    data = payload.get("data") or {}

    phone = (
        payload.get("phone")
        or payload.get("from")
        or data.get("phone")
        or data.get("from")
    )

    text = (
        payload.get("message")
        or payload.get("text")
        or data.get("message")
        or data.get("text")
    )

    print("PHONE:", phone)
    print("TEXT:", text)

    if not phone or not text:
        print("SEM PHONE OU TEXT")
        return {"ok": True}

    reply = await generate_reply(text)
    await send_zapi_text(phone, reply)

    return {"ok": True}

async def generate_reply(user_text: str) -> str:
    if not OPENAI_API_KEY:
        return "Tô sem sistema agora 😕 tenta de novo em alguns minutos."

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": (
            "Você é uma atendente humana no WhatsApp. "
            "Responda curto, natural e em português do Brasil.\n\n"
            f"Cliente: {user_text}"
        ),
    }

    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            json=payload,
        )
        data = r.json()

    resposta = ""
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                resposta += c.get("text", "")

    resposta = resposta.strip()
    return resposta or "Me conta um pouquinho melhor 😉"

async def send_zapi_text(phone: str, text: str):
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        print("FALTANDO ZAPI_INSTANCE OU ZAPI_TOKEN")
        return

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

    body = {
        "phone": str(phone),
        "message": str(text),
    }

    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(url, json=body)
        print("ZAPI STATUS:", resp.status_code)
        print("ZAPI BODY:", resp.text)
