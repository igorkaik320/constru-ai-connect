from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import base64
import re
import requests
from twilio.twiml.messaging_response import MessagingResponse

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes,
    buscar_pedido_por_id,
    buscar_obra,
    buscar_centro_custo,
    buscar_fornecedor,
)
from sienge.sienge_boletos import (
    buscar_boletos_por_cpf,
    gerar_link_boleto,
)

# ============================================================
# 🔧 CONFIGURAÇÃO DE LOG
# ============================================================
logging.basicConfig(level=logging.INFO)

# ============================================================
# 🚀 INICIALIZAÇÃO DO FASTAPI
# ============================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 📬 MODELOS
# ============================================================
class Message(BaseModel):
    user: str
    text: str

# ============================================================
# 💰 FUNÇÕES UTILITÁRIAS
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

# ============================================================
# 🧠 MEMÓRIA DE CONVERSAS TEMPORÁRIA
# ============================================================
usuarios_contexto = {}

# ============================================================
# 🧠 INTERPRETAÇÃO DE COMANDOS
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # === COMANDOS GERAIS ===
    if t in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao", "parametros": {}}

    # === PEDIDOS ===
    if any(k in t for k in ["pedidos pendentes", "listar pendentes"]):
        return {"acao": "listar_pedidos_pendentes", "parametros": {}}

    if "autorizar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "reprovar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "itens do pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "itens_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "pdf" in t or "relatório" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid)}} if pid else {}

    # === BOLETOS ===
    if "segunda via" in t or "boleto" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
        else:
            return {"acao": "buscar_boletos_cpf", "parametros": {"texto": t}}

    return {"acao": None}

# ============================================================
# 📨 ENDPOINT PRINCIPAL
# ============================================================
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info("📩 Mensagem recebida: %s -> %s", msg.user, msg.text)

    texto = (msg.text or "").strip()
    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    menu_inicial = [
        {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "📄 Gerar PDF", "action": "relatorio_pdf"},
        {"label": "💳 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
    ]

    # === Saudação inicial ===
    if acao == "saudacao" or texto == "":
        return {
            "text": "👋 Olá! Seja bem-vindo à Constru.IA.\nComo posso te ajudar hoje?",
            "buttons": menu_inicial
        }

    try:
        # === Fluxo do CPF ===
        if msg.user in usuarios_contexto and usuarios_contexto[msg.user].get("aguardando_confirmacao"):
            if texto.lower() in ["sim", "confirmo", "confirmar", "ok"]:
                cpf = usuarios_contexto[msg.user]["cpf"]
                nome = usuarios_contexto[msg.user]["nome"]
                del usuarios_contexto[msg.user]
                return {
                    "text": f"🔎 Buscando boletos para {nome}...",
                    "loading": True
                } | buscar_boletos_por_cpf(cpf)
            else:
                del usuarios_contexto[msg.user]
                return {
                    "text": "⚠️ Tudo bem, digite o CPF correto (com ou sem formatação).",
                    "buttons": [{"label": "Voltar", "action": "buscar_boletos_cpf"}]
                }

        # === Segunda via de boletos ===
        if acao == "buscar_boletos_cpf":
            cpf_match = re.search(r'\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}', texto)
            if not cpf_match:
                return {
                    "text": "💳 Para localizar seus boletos, digite o CPF do titular (com ou sem formatação).",
                    "buttons": [{"label": "🔙 Voltar", "action": "saudacao"}]
                }

            cpf = re.sub(r'\D', '', cpf_match.group(0))
            resultado = buscar_boletos_por_cpf(cpf)

            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu_inicial}

            nome = resultado.get("nome", "Cliente não identificado")
            usuarios_contexto[msg.user] = {"cpf": cpf, "nome": nome, "aguardando_confirmacao": True}

            return {
                "text": f"🔍 Localizei o cliente *{nome}*.\nDeseja confirmar para buscar os boletos?",
                "buttons": [
                    {"label": "✅ Sim, confirmar", "action": "confirmar"},
                    {"label": "❌ Não, digitei errado", "action": "buscar_boletos_cpf"},
                ]
            }

        # === Link do boleto ===
        if acao == "link_boleto":
            titulo = parametros.get("titulo_id")
            parcela = parametros.get("parcela_id")
            if not titulo or not parcela:
                return {"text": "⚠️ Informe o título e parcela (ex: 2ª via 420/5)", "buttons": menu_inicial}

            msg_link = gerar_link_boleto(titulo, parcela)
            return {"text": msg_link, "buttons": menu_inicial}

        # === Pedidos ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu_inicial}

            linhas = [f"• Pedido {p['id']} — {money(p.get('totalAmount'))}" for p in pedidos]
            return {"text": "📋 Pedidos pendentes:\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        return {"text": "🤖 Não entendi o comando.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception("Erro geral:")
        return {"text": f"❌ Ocorreu um erro: {e}", "buttons": menu_inicial}

# ============================================================
# 🩺 HEALTH CHECK
# ============================================================
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
