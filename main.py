from fastapi import FastAPI, Request
import os
import httpx

app = FastAPI()

# Variáveis (ficam no Render -> Environment Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE", "")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN", "")

@app.get("/")
def home():
    return {"status": "ok", "message": "bot rodando"}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/zapi")
async def zapi_webhook(request: Request):
    payload = await request.json()
    print("ZAPI payload:", payload)

    # Tenta pegar telefone e texto em formatos diferentes
    data = payload.get("data") or {}

    phone = (
        payload.get("phone")
        or payload.get("from")
        or payload.get("sender")
        or data.get("phone")
        or data.get("from")
        or data.get("sender")
    )

    text = (
        payload.get("message")
        or payload.get("text")
        or data.get("message")
        or data.get("text")
    )

    print("ZAPI phone:", phone)
    print("ZAPI text:", text)

    # Se não tiver dados, não quebra
    if not phone or not text:
        return {"ok": True, "note": "sem phone/text"}

    # Gera resposta
    reply = await generate_reply(text)

    # Envia resposta
    await send_zapi_text(phone, reply)

    return {"ok": True}

async def generate_reply(user_text: str) -> str:
    # Se não tiver chave da OpenAI, responde algo simples (pra não travar)
    if not OPENAI_API_KEY:
        return "Tô sem sistema agora 😕 tenta de novo em alguns minutos."

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4.1-mini",
        "input": (
            "Você é uma atendente humana no WhatsApp. Responda em português do Brasil, curto, natural e educado. "
            "Se faltar informação, faça 1 pergunta curta.\n\n"
            f"Cliente: {user_text}"
        ),
    }

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        try:
            data = r.json()
        except Exception:
            return "Tive um probleminha aqui 😕 me chama de novo já já."

    # Extrai texto do Responses API
    out = ""
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                out += c.get("text", "")

    out = out.strip()
    return out or "Me fala só um detalhe pra eu te responder certinho 😉"

async def send_zapi_text(phone: str, text: str):
    # Checagens
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        print("FALTANDO ZAPI_INSTANCE ou ZAPI_TOKEN")
        return

    if not ZAPI_CLIENT_TOKEN:
        print("FALTANDO ZAPI_CLIENT_TOKEN")
        return

    # Endpoint certo que você confirmou: send-text
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

    # Corpo padrão (se sua documentação mostrar nomes diferentes, eu ajusto)
    body = {
        "phone": str(phone),
        "message": str(text),
    }

    headers = {
        "Client-Token": ZAPI_CLIENT_TOKEN
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(url, json=body, headers=headers)
        print("ZAPI send status:", resp.status_code)
        print("ZAPI send body:", resp.text)
