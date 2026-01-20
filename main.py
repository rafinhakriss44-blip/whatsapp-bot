from fastapi import FastAPI, Request
import os
import httpx

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")

@app.get("/")
def home():
    return {"status": "ok", "message": "bot rodando"}

@app.post("/zapi")
async def zapi_webhook(request: Request):
    payload = await request.json()

    print("ZAPI payload:", payload)

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

    print("ZAPI phone:", phone)
    print("ZAPI text:", text)

    if not phone or not text:
        return {"ok": True}

    reply = await generate_reply(text)
    await send_zapi_message(phone, reply)

    return {"ok": True}

async def generate_reply(user_text: str) -> str:
    if not OPENAI_API_KEY:
        return "Tô sem sistema agora, tenta de novo já já 🙏"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": (
            "Responda como uma pessoa real no WhatsApp, curto, educado e natural, em português.\n\n"
            f"Cliente: {user_text}"
        )
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            json=payload
        )
        data = response.json()

    texto = ""
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                texto += c.get("text", "")

    return texto.strip() or "Me fala só um detalhe pra eu te responder certinho 😉"

async def send_zapi_message(phone: str, text: str):
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        print("FALTANDO ZAPI_INSTANCE ou ZAPI_TOKEN")
        return

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/sendText"

    body = {"phone": phone, "message": text}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body)
        print("ZAPI send status:", resp.status_code)
        print("ZAPI send body:", resp.text)
