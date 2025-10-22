from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import re
import pandas as pd

# ============================================================
# 🔗 IMPORTS DOS MÓDULOS EXISTENTES
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
    gerar_relatorio_json,
)
from sienge.sienge_ia import gerar_analise_financeira

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
# 🧠 INTERPRETAÇÃO DE COMANDOS
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # === SAUDAÇÃO ===
    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao"}

    # === PEDIDOS ===
    if any(k in t for k in ["pedidos pendentes", "listar pendentes"]):
        return {"acao": "listar_pedidos_pendentes"}

    m = re.search(r"\bitens(?:\s+do)?\s+pedido\s+(\d+)\b", t)
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

    # === FINANCEIRO / IA ===
    if "analisar" in t or "relatório completo" in t or "inteligente" in t:
        return {"acao": "analise_financeira"}

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
        {"label": "🧠 Análise Inteligente", "action": "analise_financeira"},
    ]

    # === SAUDAÇÃO ===
    if not texto or acao == "saudacao":
        return {
            "text": "👋 Olá! Seja bem-vindo à Constru.IA.\nComo posso te ajudar hoje?",
            "buttons": menu_inicial,
        }

    try:
        # === PEDIDOS ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "✅ Nenhum pedido pendente encontrado.", "buttons": menu_inicial}
            linhas = [f"📦 Pedido {p['id']} — {p['supplierName']} — {money(p['totalAmount'])}" for p in pedidos]
            return {"text": "📋 **Pedidos Pendentes:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        if acao == "itens_pedido":
            itens = itens_pedido(parametros["pedido_id"])
            linhas = [f"🧱 {i['itemDescription']} — {i['quantity']} {i['unit']} — {money(i['total'])}" for i in itens]
            return {"text": f"📦 **Itens do Pedido {parametros['pedido_id']}:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        if acao == "autorizar_pedido":
            autorizar_pedido(parametros["pedido_id"])
            return {"text": f"✅ Pedido {parametros['pedido_id']} autorizado com sucesso.", "buttons": menu_inicial}

        if acao == "reprovar_pedido":
            reprovar_pedido(parametros["pedido_id"])
            return {"text": f"🚫 Pedido {parametros['pedido_id']} reprovado.", "buttons": menu_inicial}

        if acao == "relatorio_pdf":
            pdf_bytes = gerar_relatorio_pdf_bytes(parametros["pedido_id"])
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {
                "text": f"📄 Relatório do Pedido {parametros['pedido_id']} gerado com sucesso!",
                "file": pdf_base64,
                "filename": f"pedido_{parametros['pedido_id']}.pdf",
                "buttons": menu_inicial,
            }

        # === BOLETOS ===
        if acao == "buscar_boletos_cpf":
            return {"text": "🔎 Informe o CPF para buscar os boletos."}

        if acao == "cpf_digitado":
            cpf = parametros.get("cpf")
            boletos = buscar_boletos_por_cpf(cpf)
            if not boletos:
                return {"text": f"⚠️ Nenhum boleto encontrado para CPF {cpf}.", "buttons": menu_inicial}
            linhas = [f"💳 {b['descricao']} — Venc: {b['vencimento']} — {money(b['valor'])}" for b in boletos]
            return {"text": f"📄 **Boletos encontrados para {cpf}:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        if acao == "link_boleto":
            url = gerar_link_boleto(parametros["titulo_id"], parametros["parcela_id"])
            return {"text": f"🔗 Link para o boleto:\n{url}", "buttons": menu_inicial}

        # === FINANCEIRO ===
        if acao == "resumo_financeiro":
            r = resumo_financeiro_dre()
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

        if acao == "gastos_por_obra":
            dados = gastos_por_obra()
            if not dados:
                return {"text": "⚠️ Nenhum gasto encontrado por obra.", "buttons": menu_inicial}
            linhas = [f"🏗️ {d['obra']} — {money(d['valor'])}" for d in dados]
            return {"text": "📊 **Gastos por Obra:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        if acao == "gastos_por_centro_custo":
            dados = gastos_por_centro_custo()
            if not dados:
                return {"text": "⚠️ Nenhum gasto encontrado por centro de custo.", "buttons": menu_inicial}
            linhas = [f"🏢 {d['centro_custo']} — {money(d['valor'])}" for d in dados]
            return {"text": "📊 **Gastos por Centro de Custo:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        if acao == "analise_financeira":
            logging.info("🧠 Gerando análise financeira via OpenAI...")
            relatorio = gerar_relatorio_json()
            df = pd.DataFrame(relatorio["todas_despesas"])
            analise = gerar_analise_financeira("Relatório Completo", df)
            return {"text": analise, "buttons": menu_inicial}

        # === PADRÃO ===
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
