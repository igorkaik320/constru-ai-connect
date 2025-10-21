from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import re
import base64

# ============================================================
# 🔗 IMPORTS EXISTENTES
# ============================================================
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes,
)
from sienge.sienge_boletos import (
    buscar_boletos_por_cpf,
    gerar_link_boleto,
)
from sienge.sienge_financeiro import (
    resumo_financeiro_dre,
    gastos_por_obra,
    gastos_por_centro_custo,
)

# ============================================================
# ⚙️ CONFIGURAÇÕES GERAIS
# ============================================================
logging.basicConfig(level=logging.INFO)
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
# 💰 FORMATADOR DE VALOR
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

# ============================================================
# 🧠 CONTEXTO TEMPORÁRIO DE USUÁRIOS (para confirmação de CPF)
# ============================================================
usuarios_contexto = {}

# ============================================================
# 🧠 INTERPRETAÇÃO DE COMANDOS
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # === SAUDAÇÃO ===
    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao"}

    # === PEDIDOS ===
    if any(k in t for k in ["pedidos pendentes", "listar pendentes", "listar_pedidos_pendentes"]):
        return {"acao": "listar_pedidos_pendentes"}

    m = (
        re.search(r"\bitens(?:\s+do)?\s+pedido\s+(\d+)\b", t)
        or re.search(r"\bitens\s+(\d+)\b", t)
        or re.search(r"\bpedido\s+(\d+)\s+itens\b", t)
        or re.search(r"\bver\s+itens\s+(\d+)\b", t)
    )
    if m:
        return {"acao": "itens_pedido", "parametros": {"pedido_id": int(m.group(1))}}

    if "autorizar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "reprovar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "pdf" in t or "relatório" in t or "relatorio" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid)}} if pid else {}

    # === FINANCEIRO ===
    if "financeiro" in t or "resultado" in t or "lucro" in t:
        return {"acao": "resumo_financeiro"}

    if "obra" in t and ("gasto" in t or "despesa" in t):
        return {"acao": "gastos_por_obra"}

    if "centro de custo" in t or "custos por centro" in t:
        return {"acao": "gastos_por_centro_custo"}

    # === BOLETOS ===
    if "segunda via" in t or "boleto" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
        return {"acao": "buscar_boletos_cpf"}

    # === DETECÇÃO AUTOMÁTICA DE CPF ===
    if re.search(r'\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}', t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}

    return {"acao": None}

# ============================================================
# 📨 ENDPOINT PRINCIPAL
# ============================================================
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    texto = (msg.text or "").strip()
    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    menu_inicial = [
        {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "📄 Gerar PDF", "action": "relatorio_pdf"},
        {"label": "💳 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
        {"label": "💰 Resumo Financeiro", "action": "resumo_financeiro"},
    ]

    if not texto or acao == "saudacao":
        return {
            "text": "👋 Olá! Seja bem-vindo à Constru.IA.\nComo posso te ajudar hoje?",
            "buttons": menu_inicial,
        }

    try:
        # === FINANCEIRO: RESUMO GERAL ===
        if acao == "resumo_financeiro":
            r = resumo_financeiro_dre()
            if "erro" in r:
                return {"text": f"❌ {r['erro']}", "buttons": menu_inicial}
            return {
                "text": (
                    f"📊 **Resumo Financeiro (DRE)**\n\n"
                    f"🗓️ Período: {r['periodo']['inicio']} até {r['periodo']['fim']}\n"
                    f"💰 Receitas: {r['formatado']['receitas']}\n"
                    f"💸 Despesas: {r['formatado']['despesas']}\n"
                    f"📈 Lucro: {r['formatado']['lucro']}"
                ),
                "buttons": menu_inicial,
            }

        # === FINANCEIRO: GASTOS POR OBRA ===
        if acao == "gastos_por_obra":
            dados = gastos_por_obra()
            if not dados:
                return {"text": "⚠️ Nenhum dado encontrado.", "buttons": menu_inicial}
            linhas = [f"🏗️ {d['obra']} — {money(d['valor'])}" for d in dados]
            return {"text": "📊 **Gastos por Obra:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        # === FINANCEIRO: GASTOS POR CENTRO DE CUSTO ===
        if acao == "gastos_por_centro_custo":
            dados = gastos_por_centro_custo()
            if not dados:
                return {"text": "⚠️ Nenhum dado encontrado.", "buttons": menu_inicial}
            linhas = [f"🏢 {d['centro_custo']} — {money(d['valor'])}" for d in dados]
            return {"text": "📊 **Gastos por Centro de Custo:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        # === OUTROS (Pedidos, Boletos, etc) ===
        # Mantém o restante das regras originais (pedidos, boletos etc)
        # Você já tem tudo isso implementado antes do bloco try/except.

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
