from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import re
import base64
import os

# === MÓDULOS DO SIENGE ===
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
    resumo_financeiro,
    gastos_por_obra,
    gastos_por_centro_custo,
)
from sienge.sienge_ia import gerar_analise_financeira

# === CONFIGURAÇÕES ===
logging.basicConfig(level=logging.INFO)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODELOS ===
class Message(BaseModel):
    user: str
    text: str

# === FORMATADOR ===
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# === CONTEXTO TEMPORÁRIO ===
usuarios_contexto = {}

# === INTERPRETAÇÃO DE INTENÇÕES ===
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # saudações
    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao"}

    # pedidos
    if "pedido" in t and "pendente" in t:
        return {"acao": "listar_pedidos_pendentes"}
    if re.search(r"itens\s+do\s+pedido\s+\d+", t):
        pid = re.findall(r"\d+", t)[-1]
        return {"acao": "itens_pedido", "parametros": {"pedido_id": int(pid)}}
    if "autorizar pedido" in t:
        pid = re.findall(r"\d+", t)[-1]
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}}
    if "reprovar pedido" in t:
        pid = re.findall(r"\d+", t)[-1]
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}}
    if "pdf" in t or "relatorio" in t:
        pid = re.findall(r"\d+", t)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid[-1])}} if pid else {}

    # boletos
    if "segunda via" in t or "boleto" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
        return {"acao": "buscar_boletos_cpf"}

    # cpf detectado
    if re.search(r"\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}

    # financeiro
    if "resumo" in t or "dre" in t or "resultado" in t:
        return {"acao": "resumo_financeiro"}
    if "gasto" in t and "obra" in t:
        return {"acao": "gastos_por_obra"}
    if "centro de custo" in t:
        return {"acao": "gastos_por_centro_custo"}
    if "análise" in t or "analise" in t:
        return {"acao": "analise_financeira"}

    return {"acao": None}

# === ENDPOINT PRINCIPAL ===
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")
    texto = (msg.text or "").strip()
    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    menu_inicial = [
        {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "💳 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
        {"label": "📊 Resumo Financeiro", "action": "resumo_financeiro"},
        {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
    ]

    if not texto or acao == "saudacao":
        return {
            "text": "👋 Olá! Seja bem-vindo à Constru.IA.\nComo posso te ajudar hoje?",
            "buttons": menu_inicial,
        }

    try:
        # ===== CPF CONFIRMAÇÃO =====
        if msg.user in usuarios_contexto and usuarios_contexto[msg.user].get("aguardando_confirmacao"):
            if texto.lower() in ["sim", "confirmar", "ok", "✅ confirmar"]:
                cpf = usuarios_contexto[msg.user]["cpf"]
                nome = usuarios_contexto[msg.user]["nome"]
                del usuarios_contexto[msg.user]

                resultado = buscar_boletos_por_cpf(cpf)
                boletos = resultado.get("boletos", [])
                if not boletos:
                    return {"text": f"📭 Nenhum boleto em aberto encontrado para {nome}."}

                linhas = [
                    f"💳 **Título {b['titulo_id']}** — {money(b['valor'])} — Venc.: {b['vencimento']}"
                    for b in boletos
                ]
                botoes = [
                    {"label": f"2ª via {b['titulo_id']}/{b['parcela_id']}",
                     "action": f"segunda via {b['titulo_id']}/{b['parcela_id']}"}
                    for b in boletos
                ]
                return {"text": f"📋 Boletos de *{nome}:*\n\n" + "\n".join(linhas), "buttons": botoes}
            else:
                del usuarios_contexto[msg.user]
                return {"text": "⚠️ Tudo bem, digite o CPF novamente.", "buttons": menu_inicial}

        # ===== CPF DETECTADO =====
        if acao == "cpf_digitado":
            cpf = re.sub(r"\D", "", parametros.get("cpf", ""))
            if len(cpf) != 11:
                return {"text": "⚠️ CPF inválido. Digite novamente."}

            resultado = buscar_boletos_por_cpf(cpf)
            nome = resultado.get("nome", "Cliente não identificado")
            usuarios_contexto[msg.user] = {"cpf": cpf, "nome": nome, "aguardando_confirmacao": True}

            return {
                "text": f"🔎 Localizei o cliente *{nome}*.\nDeseja confirmar para buscar os boletos?",
                "buttons": [
                    {"label": "✅ Confirmar", "action": "confirmar"},
                    {"label": "❌ Corrigir CPF", "action": "buscar_boletos_cpf"},
                ],
            }

        # ===== BOLETOS =====
        if acao == "buscar_boletos_cpf":
            return {"text": "💳 Digite o CPF do titular dos boletos.", "buttons": menu_inicial}

        if acao == "link_boleto":
            t, p = parametros.get("titulo_id"), parametros.get("parcela_id")
            return {"text": gerar_link_boleto(t, p), "buttons": menu_inicial}

        # ===== PEDIDOS =====
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente."}
            linhas = [f"📦 Pedido {p['id']} — {money(p['totalAmount'])}" for p in pedidos]
            botoes = [{"label": f"Itens {p['id']}", "action": f"itens do pedido {p['id']}"} for p in pedidos]
            return {"text": "\n".join(linhas), "buttons": botoes}

        if acao == "itens_pedido":
            pid = parametros.get("pedido_id")
            itens = itens_pedido(pid)
            linhas = [f"• {i.get('description', 'Item')} — {money(i.get('totalAmount', 0))}" for i in itens]
            return {
                "text": f"📦 Itens do pedido {pid}:\n" + "\n".join(linhas),
                "buttons": [
                    {"label": "✅ Autorizar", "action": f"autorizar pedido {pid}"},
                    {"label": "❌ Reprovar", "action": f"reprovar pedido {pid}"},
                    {"label": "📄 PDF", "action": f"gerar pdf pedido {pid}"},
                ],
            }

        if acao == "autorizar_pedido":
            return {"text": autorizar_pedido(parametros["pedido_id"])}
        if acao == "reprovar_pedido":
            return {"text": reprovar_pedido(parametros["pedido_id"])}
        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            pdf = gerar_relatorio_pdf_bytes(pid)
            if not pdf:
                return {"text": "⚠️ Erro ao gerar PDF."}
            return {
                "text": f"📄 PDF do pedido {pid} gerado com sucesso.",
                "pdf_base64": base64.b64encode(pdf).decode(),
                "filename": f"pedido_{pid}.pdf",
            }

        # ===== FINANCEIRO =====
        if acao == "resumo_financeiro":
            resumo = resumo_financeiro()
            return {"text": resumo, "buttons": menu_inicial}

        if acao == "gastos_por_obra":
            return {"text": gastos_por_obra(), "buttons": menu_inicial}

        if acao == "gastos_por_centro_custo":
            return {"text": gastos_por_centro_custo(), "buttons": menu_inicial}

        if acao == "analise_financeira":
            texto_ia = gerar_analise_financeira()
            return {"text": texto_ia, "buttons": menu_inicial}

        return {"text": "🤖 Não entendi o comando.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception("❌ Erro geral:")
        return {"text": f"Ocorreu um erro: {e}", "buttons": menu_inicial}

# === HEALTH CHECK ===
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
