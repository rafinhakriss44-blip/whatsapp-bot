import os
import streamlit as st
from supabase import create_client
from openai import OpenAI

st.set_page_config(page_title="Painel WhatsApp", layout="wide")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

missing = []
if not ADMIN_PASSWORD: missing.append("ADMIN_PASSWORD")
if not SUPABASE_URL: missing.append("SUPABASE_URL")
if not SUPABASE_ANON_KEY: missing.append("SUPABASE_ANON_KEY")
if not OPENAI_API_KEY: missing.append("OPENAI_API_KEY")

if missing:
    st.error("Faltam variáveis no Render: " + ", ".join(missing))
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
oai = OpenAI(api_key=OPENAI_API_KEY)

if "authed" not in st.session_state:
    st.session_state.authed = False

st.title("Painel WhatsApp (só você)")

if not st.session_state.authed:
    pw = st.text_input("Senha do painel", type="password")
    if st.button("Entrar"):
        if pw == ADMIN_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Senha errada")
    st.stop()

st.sidebar.header("Cadastrar nova cliente")

with st.sidebar.form("new_client"):
    name = st.text_input("Nome")
    phone = st.text_input("Telefone (opcional)")
    created = st.form_submit_button("Criar")
    if created:
        if not name.strip():
            st.sidebar.error("Coloque um nome")
        else:
            res = supabase.table("clients").insert({"name": name.strip(), "phone": phone.strip()}).execute()
            client_id = res.data[0]["id"]
            supabase.table("client_settings").insert({"client_id": client_id, "persona": "", "rules": ""}).execute()
            st.sidebar.success("Cliente criado!")
            st.rerun()

clients = supabase.table("clients").select("*").order("created_at", desc=True).execute().data

if not clients:
    st.info("Cadastre a primeira cliente na barra lateral.")
    st.stop()

client_names = [f'{c["name"]}  {"(ativo)" if c["is_active"] else "(pausado)"}' for c in clients]
idx = st.selectbox("Escolha a cliente", range(len(clients)), format_func=lambda i: client_names[i])
client = clients[idx]

settings = supabase.table("client_settings").select("*").eq("client_id", client["id"]).single().execute().data

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Configuração da cliente")
    persona = st.text_area("Jeito de falar (persona)", value=settings.get("persona", ""), height=180)
    rules = st.text_area("Regras e limites", value=settings.get("rules", ""), height=180)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Salvar"):
            supabase.table("client_settings").update({"persona": persona, "rules": rules}).eq("client_id", client["id"]).execute()
            st.success("Salvo!")
    with c2:
        if st.button("Ativar/Desativar"):
            supabase.table("clients").update({"is_active": not client["is_active"]}).eq("id", client["id"]).execute()
            st.rerun()
    with c3:
        if st.button("Excluir cliente"):
            supabase.table("clients").delete().eq("id", client["id"]).execute()
            st.warning("Excluída.")
            st.rerun()

with col2:
    st.subheader("Teste de resposta (simulação)")
    user_msg = st.text_area("Mensagem do cliente (teste)", height=120, placeholder="Ex: Oi, tá disponível hoje?")
    if st.button("Gerar resposta"):
        if not client["is_active"]:
            st.warning("Essa cliente está pausada.")
        elif not user_msg.strip():
            st.error("Escreva uma mensagem para testar.")
        else:
            system = (
                "Você escreve respostas curtas e naturais, em português do Brasil, como se estivesse no WhatsApp. "
                "Seja persuasiva e objetiva. Não use linguagem robótica. "
                "Se faltar informação, faça 1 pergunta curta."
            )

            prompt = f"PERSONA:\n{persona}\n\nREGRAS:\n{rules}\n"

            resp = oai.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {"role": "system", "content": system},
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg.strip()}
                ],
            )

            out = ""
            for item in resp.output:
                for c in item.content:
                    if getattr(c, "type", "") == "output_text":
                        out += c.text

            out = out.strip() or "Me fala só um detalhe pra eu te responder certinho 😉"
            st.markdown("### Resposta sugerida")
            st.write(out)

            supabase.table("messages").insert([
                {"client_id": client["id"], "role": "user", "content": user_msg.strip()},
                {"client_id": client["id"], "role": "assistant", "content": out},
            ]).execute()
                                                    
