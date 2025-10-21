from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import base64
import re

# ====== IMPORTAÇÕES SIENGE ======
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
# 📬 MODELO DE MENSAGEM
# ============================================================
class Message(BaseModel):
    user: str
    text: str

# ============================================================
# 💰 FORMATADOR DE VALORES
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

# ============================================================
# 🧠 INTERPRETAÇÃO DE INTENÇÕES (rápida e robusta)
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # === MENU ===
    if t in ["menu", "início", "inicio"]:
        return {"acao": "menu_inicial"}

    # === PEDIDOS ===
    if "pedidos pendentes" in t:
        return {"acao": "listar_pedidos_pendentes"}

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

    # === SEGUNDA VIA ===
    if any(k in t for k in ["segunda via", "2ª via", "2a via", "boletos", "boleto cpf"]):
        # Caso o texto contenha o formato “420/5” ou “420 5”
        match = re.search(r"(\d{2,})[^\d]+(\d{1,})", t)
        if match:
            titulo_id, parcela_id = match.groups()
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(titulo_id), "parcela_id": int(parcela_id)}}
        # Caso seja apenas o início do fluxo (“segunda via” sem números)
        return {"acao": "iniciar_fluxo_boletos"}

    # === CPF DETECTADO ===
    cpf_match = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})", t)
    if cpf_match:
        cpf = re.sub(r"\D", "", cpf_match.group(1))
        if len(cpf) == 11:
            return {"acao": "buscar_boletos_cpf", "parametros": {"texto": cpf}}

    return {"acao": None}

# ============================================================
# 📨 ENDPOINT PRINCIPAL
# ============================================================
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 {msg.user} -> {msg.text}")
    intencao = entender_intencao(msg.text or "")
    logging.info(f"🧠 Interpretação -> {intencao}")

    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    menu_inicial = [
        {"label": "🧾 Pedidos Pendentes", "action": "pedidos pendentes"},
        {"label": "📄 Gerar PDF", "action": "gerar pdf"},
        {"label": "💳 Segunda Via de Boletos", "action": "segunda via"},
    ]

    try:
        # === MENU ===
        if acao in ["menu_inicial", None] and msg.text.strip() == "":
            return {"text": "👋 Olá! Como posso te ajudar hoje?", "buttons": menu_inicial}

        # === PEDIDOS ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu_inicial}
            linhas = [f"• Pedido {p['id']} — {money(p.get('totalAmount'))}" for p in pedidos]
            return {"text": "📋 Pedidos pendentes:\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        if acao == "autorizar_pedido":
            pid = parametros.get("pedido_id")
            ok = autorizar_pedido(pid)
            return {"text": "✅ Pedido autorizado!" if ok else "❌ Falha ao autorizar.", "buttons": menu_inicial}

        if acao == "reprovar_pedido":
            pid = parametros.get("pedido_id")
            ok = reprovar_pedido(pid)
            return {"text": "🚫 Pedido reprovado!" if ok else "❌ Falha ao reprovar.", "buttons": menu_inicial}

        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if not pdf_bytes:
                return {"text": "❌ Não foi possível gerar o PDF.", "buttons": menu_inicial}
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            return {"text": f"📄 PDF do pedido {pid} gerado com sucesso!", "pdf_base64": pdf_b64}

        # === FLUXO DE BOLETOS ===
        if acao == "iniciar_fluxo_boletos":
            return {
                "text": "👋 Olá! Para localizar seus boletos, por favor digite o CPF do titular.\n"
                        "(Pode digitar com ou sem formatação 😉)",
                "buttons": [{"label": "Voltar ao Menu", "action": "menu"}],
            }

        if acao == "buscar_boletos_cpf":
            cpf = parametros.get("texto", "")
            resultado = buscar_boletos_por_cpf(cpf)
            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu_inicial}

            nome = resultado["nome"]
            boletos = resultado["boletos"]
            if not boletos:
                return {"text": f"⚠️ Nenhum boleto em aberto para {nome}.", "buttons": menu_inicial}

            linhas = []
            botoes = []
            for b in boletos:
                linhas.append(f"💳 **Título {b['titulo_id']}** — {money(b['valor'])} — Venc.: {b['vencimento']}")
                botoes.append({
                    "label": f"2ª via {b['titulo_id']}/{b['parcela_id']}",
                    "action": f"segunda via {b['titulo_id']}/{b['parcela_id']}",
                })

            return {"text": f"📋 Boletos em aberto para **{nome}:**\n\n" + "\n".join(linhas), "buttons": botoes}

        if acao == "link_boleto":
            titulo = parametros.get("titulo_id")
            parcela = parametros.get("parcela_id")
            if not titulo or not parcela:
                return {"text": "⚠️ Informe o título e parcela (ex: 2ª via 267/1)", "buttons": menu_inicial}

            msg_link = gerar_link_boleto(titulo, parcela)
            return {"text": msg_link, "buttons": menu_inicial}

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
