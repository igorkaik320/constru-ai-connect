from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging, re, base64, os
import pandas as pd

# === MÓDULOS LOCAIS ===
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes,
)
from sienge.sienge_boletos import buscar_boletos_por_cpf, gerar_link_boleto
from sienge.sienge_financeiro import (
    resumo_financeiro,
    gastos_por_obra,
    gastos_por_centro_custo,
    gerar_relatorio_json,
)
from sienge.sienge_ia import gerar_analise_financeira
from dashboard_financeiro import gerar_apresentacao_gamma

# ============================================================
# 🚀 CONFIGURAÇÃO DO SERVIDOR FASTAPI
# ============================================================
logging.basicConfig(level=logging.INFO)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# === Pasta para relatórios e arquivos estáticos ===
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# 📩 MODELOS DE DADOS
# ============================================================
class Message(BaseModel):
    user: str
    text: str

# ============================================================
# 🧮 FUNÇÕES AUXILIARES
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

usuarios_contexto = {}

def extrair_periodo(texto: str):
    datas = re.findall(r"\d{4}-\d{2}-\d{2}", texto)
    if len(datas) >= 2:
        return {"startDate": datas[0], "endDate": datas[1]}
    if len(datas) == 1:
        return {"startDate": datas[0]}
    return {}

def extrair_empresa(texto: str):
    m = re.search(r"empresa\s+(\d+)", texto)
    if m:
        return {"enterpriseId": m.group(1)}
    return {}

def filtros_do_usuario(user: str):
    return usuarios_contexto.get(user, {}).get("filtros", {})

def atualizar_filtros(user: str, novos: dict):
    ctx = usuarios_contexto.setdefault(user, {})
    atuais = ctx.get("filtros", {})
    atuais.update({k: v for k, v in novos.items() if v})
    ctx["filtros"] = atuais
    return atuais

# ============================================================
# 🧠 INTERPRETAÇÃO DE INTENÇÃO
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao"}
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
    if "pdf" in t or "relatorio" in t or "relatório" in t:
        nums = re.findall(r"\d+", t)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(nums[-1])}} if nums else {}
    if "segunda via" in t or "boleto" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
        return {"acao": "buscar_boletos_cpf"}
    if re.search(r"\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}
    if "resumo" in t or "dre" in t or "resultado" in t:
        return {"acao": "resumo_financeiro"}
    if "gasto" in t and "obra" in t:
        return {"acao": "gastos_por_obra"}
    if "centro de custo" in t:
        return {"acao": "gastos_por_centro_custo"}
    if "análise" in t or "analise" in t:
        return {"acao": "analise_financeira"}
    if "apresentacao" in t or "slides" in t or "gamma" in t:
        return {"acao": "apresentacao_gamma"}
    if "empresa" in t or re.search(r"\d{4}-\d{2}-\d{2}", t):
        return {"acao": "definir_filtros"}
    return {"acao": None}

# ============================================================
# 💬 ENDPOINT PRINCIPAL DE MENSAGENS
# ============================================================
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")
    texto = (msg.text or "").strip()

    # Atualiza filtros de empresa/período
    if "empresa" in texto.lower() or re.search(r"\d{4}-\d{2}-\d{2}", texto):
        novos = {}
        novos.update(extrair_periodo(texto))
        novos.update(extrair_empresa(texto))
        if novos:
            atualizados = atualizar_filtros(msg.user, novos)
            return {
                "text": "🧭 Filtros definidos.\n"
                        + (f"• Início: {atualizados.get('startDate')}\n" if atualizados.get("startDate") else "")
                        + (f"• Fim: {atualizados.get('endDate')}\n" if atualizados.get("endDate") else "")
                        + (f"• Empresa: {atualizados.get('enterpriseId')}\n" if atualizados.get("enterpriseId") else ""),
                "buttons": [
                    {"label": "📊 Resumo Financeiro", "action": "resumo_financeiro"},
                    {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
                    {"label": "📂 Gastos por Centro de Custo", "action": "gastos_por_centro_custo"},
                ],
            }

    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}
    filtros = filtros_do_usuario(msg.user)

    menu_inicial = [
        {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "💳 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
        {"label": "📊 Resumo Financeiro", "action": "resumo_financeiro"},
        {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
        {"label": "🎬 Gerar Relatório Gamma", "action": "apresentacao_gamma"},
    ]

    if not texto or acao == "saudacao":
        return {
            "text": "👋 Olá! Sou a Constru.IA.\n"
                    "Posso te ajudar com: Pedidos, Boletos, Resumo Financeiro, Gastos e Relatórios com IA.\n"
                    "Dica: defina filtros com: `empresa 1 2024-01-01 a 2024-12-31`",
            "buttons": menu_inicial,
        }

    try:
        # ========================================================
        # 💳 BOLETOS / CPF
        # ========================================================
        if acao == "cpf_digitado":
            cpf = re.sub(r"\D", "", parametros.get("cpf", ""))
            if len(cpf) != 11:
                return {"text": "⚠️ CPF inválido. Digite novamente."}
            resultado = buscar_boletos_por_cpf(cpf)
            nome = resultado.get("nome", "Cliente não identificado")
            usuarios_contexto[msg.user] = {"cpf": cpf, "nome": nome, "aguardando_confirmacao": True}
            return {"text": f"🔎 Localizei o cliente *{nome}*. Confirmar para listar as 2ª vias?",
                    "buttons": [{"label": "✅ Confirmar", "action": "confirmar"},
                                {"label": "❌ Corrigir CPF", "action": "buscar_boletos_cpf"}]}

        if acao == "buscar_boletos_cpf":
            return {"text": "💳 Digite o CPF do titular dos boletos.", "buttons": menu_inicial}

        if acao == "link_boleto":
            t, p = parametros.get("titulo_id"), parametros.get("parcela_id")
            return {"text": gerar_link_boleto(t, p), "buttons": menu_inicial}

        # ========================================================
        # 📦 PEDIDOS DE COMPRA
        # ========================================================
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente."}
            linhas = [f"📦 Pedido {p['id']} — {money(p.get('totalAmount', 0))}" for p in pedidos]
            botoes = [{"label": f"Itens {p['id']}", "action": f"itens do pedido {p['id']}"} for p in pedidos]
            return {"text": "\n".join(linhas), "buttons": botoes}

        if acao == "itens_pedido":
            pid = parametros.get("pedido_id")
            itens = itens_pedido(pid)
            linhas = [f"• {i.get('description', 'Item')} — {money(i.get('totalAmount', 0))}" for i in itens]
            return {"text": f"📦 Itens do pedido {pid}:\n" + "\n".join(linhas),
                    "buttons": [{"label": "✅ Autorizar", "action": f"autorizar pedido {pid}"},
                                {"label": "❌ Reprovar", "action": f"reprovar pedido {pid}"},
                                {"label": "📄 PDF", "action": f"gerar pdf pedido {pid}"}]}

        if acao == "autorizar_pedido":
            return {"text": autorizar_pedido(parametros["pedido_id"])}
        if acao == "reprovar_pedido":
            return {"text": reprovar_pedido(parametros["pedido_id"])}
        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            pdf = gerar_relatorio_pdf_bytes(pid)
            if not pdf:
                return {"text": "⚠️ Erro ao gerar PDF."}
            return {"text": f"📄 PDF do pedido {pid} gerado com sucesso.",
                    "pdf_base64": base64.b64encode(pdf).decode(),
                    "filename": f"pedido_{pid}.pdf"}

        # ========================================================
        # 💰 FINANCEIRO / IA / RELATÓRIO GAMMA
        # ========================================================
        if acao == "resumo_financeiro":
            return {"text": resumo_financeiro(**filtros), "buttons": menu_inicial}

        if acao == "gastos_por_obra":
            return {"text": gastos_por_obra(**filtros), "buttons": menu_inicial}

        if acao == "gastos_por_centro_custo":
            return {"text": gastos_por_centro_custo(**filtros), "buttons": menu_inicial}

        if acao == "analise_financeira":
            rel = gerar_relatorio_json(**filtros)
            df = pd.DataFrame(rel.get("todas_despesas", []))
            if df.empty:
                return {"text": "⚠️ Sem dados para análise."}
            texto_ia = gerar_analise_financeira("Relatório Financeiro", df)
            return {"text": texto_ia, "buttons": menu_inicial}

        if acao == "apresentacao_gamma":
            logging.info("🎬 Iniciando geração de relatório Gamma (HTML)...")
            rel = gerar_relatorio_json(**filtros)
            df = pd.DataFrame(rel.get("todas_despesas", []))
            dre = rel.get("dre", {}).get("formatado", {})
            if df.empty:
                return {"text": "⚠️ Sem dados para gerar relatório."}

            html = gerar_apresentacao_gamma(df, dre)
            caminho_html = f"static/relatorio_gamma_{msg.user}.html"
            with open(caminho_html, "w", encoding="utf-8") as f:
                f.write(html)

            link = f"https://constru-ai-connect.onrender.com/{caminho_html}"
            logging.info(f"✅ Relatório Gamma gerado com sucesso: {link}")
            return {"text": f"🎬 Relatório interativo gerado!\n\n[📊 Abrir no Navegador]({link})", "buttons": menu_inicial}

        # ========================================================
        # DEFAULT
        # ========================================================
        return {"text": "🤖 Não entendi. Dica: `empresa 1 2024-01-01 a 2024-12-31` para definir filtros.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception("❌ Erro geral:")
        return {"text": f"Ocorreu um erro: {e}", "buttons": menu_inicial}

# ============================================================
# 🌐 ROTA DE TESTE FINANCEIRO
# ============================================================
@app.get("/teste-financeiro")
def teste_financeiro():
    filtros = {"startDate": "2024-01-01", "endDate": "2024-12-31", "enterpriseId": "1"}
    rel = gerar_relatorio_json(**filtros)
    return {"resumo": rel.get("dre", {}).get("formatado", {}), "amostra": rel.get("todas_despesas", [])[:5]}

# ============================================================
# 🌍 STATUS
# ============================================================
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
