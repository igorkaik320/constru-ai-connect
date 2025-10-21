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
    resumo_financeiro,
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
        # === CONFIRMAÇÃO DE CPF ===
        if msg.user in usuarios_contexto and usuarios_contexto[msg.user].get("aguardando_confirmacao"):
            if texto.lower() in ["sim", "confirmo", "ok", "confirmar", "✅ confirmar"]:
                cpf = usuarios_contexto[msg.user]["cpf"]
                nome = usuarios_contexto[msg.user]["nome"]
                del usuarios_contexto[msg.user]

                resultado = buscar_boletos_por_cpf(cpf)
                if "erro" in resultado:
                    return {"text": resultado["erro"], "buttons": menu_inicial}

                boletos = resultado.get("boletos", [])
                if not boletos:
                    return {"text": f"📭 Nenhum boleto em aberto encontrado para {nome}.", "buttons": menu_inicial}

                linhas = []
                botoes = []
                for b in boletos:
                    linhas.append(f"💳 **Título {b['titulo_id']}** — {money(b['valor'])} — Venc.: {b['vencimento']}")
                    botoes.append({
                        "label": f"2ª via {b['titulo_id']}/{b['parcela_id']}",
                        "action": f"segunda via {b['titulo_id']}/{b['parcela_id']}"
                    })

                return {"text": f"📋 Boletos em aberto para **{nome}:**\n\n" + "\n".join(linhas), "buttons": botoes}
            else:
                del usuarios_contexto[msg.user]
                return {"text": "⚠️ Tudo bem! Digite o CPF novamente.", "buttons": menu_inicial}

        # === CPF DIGITADO ===
        if acao == "cpf_digitado":
            cpf = re.sub(r'\D', '', parametros.get("cpf", ""))
            if len(cpf) != 11:
                return {"text": "⚠️ CPF inválido. Digite novamente."}

            resultado = buscar_boletos_por_cpf(cpf)
            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu_inicial}

            nome = resultado.get("nome", "Cliente não identificado")
            usuarios_contexto[msg.user] = {"cpf": cpf, "nome": nome, "aguardando_confirmacao": True}

            return {
                "text": f"🔎 Localizei o cliente *{nome}*.\nDeseja confirmar para buscar os boletos?",
                "buttons": [
                    {"label": "✅ Confirmar", "action": "confirmar"},
                    {"label": "❌ Corrigir CPF", "action": "buscar_boletos_cpf"},
                ],
            }

        # === BUSCAR BOLETOS ===
        if acao == "buscar_boletos_cpf":
            return {
                "text": "💳 Para localizar seus boletos, digite o CPF do titular (com ou sem formatação).",
                "buttons": [{"label": "🔙 Voltar", "action": "saudacao"}],
            }

        # === LINK DE BOLETO ===
        if acao == "link_boleto":
            titulo = parametros.get("titulo_id")
            parcela = parametros.get("parcela_id")
            if not titulo or not parcela:
                return {"text": "⚠️ Informe o título e parcela (ex: 2ª via 420/5)", "buttons": menu_inicial}

            msg_link = gerar_link_boleto(titulo, parcela)
            return {"text": msg_link, "buttons": menu_inicial}

        # === PEDIDOS PENDENTES ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu_inicial}
            linhas = [f"• Pedido {p['id']} — {money(p.get('totalAmount'))}" for p in pedidos]
            botoes = [{"label": f"Itens do pedido {p['id']}", "action": f"itens do pedido {p['id']}"} for p in pedidos]
            return {"text": "📋 Pedidos pendentes:\n\n" + "\n".join(linhas), "buttons": botoes}

        # === ITENS DO PEDIDO ===
        if acao == "itens_pedido":
            pedido_id = parametros.get("pedido_id")
            if not pedido_id:
                return {"text": "⚠️ Informe o número do pedido. Exemplo: itens do pedido 278"}

            itens = itens_pedido(pedido_id)
            if not itens:
                return {"text": f"📭 Nenhum item encontrado para o pedido {pedido_id}."}

            linhas = []
            for i in itens:
                descricao = (
                    i.get("description")
                    or i.get("itemDescription")
                    or i.get("productDescription")
                    or i.get("materialDescription")
                    or i.get("name")
                    or "Item sem descrição"
                )
                quantidade = i.get("quantity", 0)
                unidade = i.get("unit", "")
                valor = i.get("totalAmount", 0)
                linhas.append(f"• {descricao} — {quantidade} {unidade} — {money(valor)}")

            return {
                "text": f"📦 Itens do pedido {pedido_id}:\n\n" + "\n".join(linhas),
                "buttons": [
                    {"label": "✅ Autorizar", "action": f"autorizar pedido {pedido_id}"},
                    {"label": "❌ Reprovar", "action": f"reprovar pedido {pedido_id}"},
                    {"label": "📄 Gerar PDF", "action": f"gerar pdf pedido {pedido_id}"},
                ],
            }

        # === AUTORIZAR PEDIDO ===
        if acao == "autorizar_pedido":
            pid = parametros.get("pedido_id")
            resposta = autorizar_pedido(pid)
            return {"text": resposta, "buttons": menu_inicial}

        # === REPROVAR PEDIDO ===
        if acao == "reprovar_pedido":
            pid = parametros.get("pedido_id")
            resposta = reprovar_pedido(pid)
            return {"text": resposta, "buttons": menu_inicial}

        # === GERAR PDF ===
        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            if not pid:
                return {"text": "⚠️ Informe o número do pedido. Exemplo: gerar pdf pedido 123"}

            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if not pdf_bytes:
                return {"text": "⚠️ Erro ao gerar o PDF do pedido."}

            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {
                "text": f"📄 PDF do pedido {pid} gerado com sucesso!",
                "pdf_base64": pdf_base64,
                "filename": f"pedido_{pid}.pdf",
            }

        # === FINANCEIRO: RESUMO GERAL ===
        if acao == "resumo_financeiro":
            r = resumo_financeiro()
            if "erro" in r:
                return {"text": f"❌ {r['erro']}", "buttons": menu_inicial}
            return {
                "text": (
                    f"📊 **Resumo Financeiro**\n\n"
                    f"🗓️ Período: {r['periodo']}\n"
                    f"💸 A pagar: {money(r['a_pagar'])}\n"
                    f"💰 A receber: {money(r['a_receber'])}\n"
                    f"📈 Lucro: {money(r['lucro'])}"
                ),
                "buttons": menu_inicial,
            }

        # === FINANCEIRO: GASTOS POR OBRA ===
        if acao == "gastos_por_obra":
            dados = gastos_por_obra()
            if "erro" in dados:
                return {"text": f"❌ {dados['erro']}", "buttons": menu_inicial}
            linhas = [f"🏗️ {d['obra']} — {money(d['valor'])}" for d in dados]
            return {"text": "📊 **Gastos por Obra:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        # === FINANCEIRO: GASTOS POR CENTRO DE CUSTO ===
        if acao == "gastos_por_centro_custo":
            dados = gastos_por_centro_custo()
            if "erro" in dados:
                return {"text": f"❌ {dados['erro']}", "buttons": menu_inicial}
            linhas = [f"🏢 {d['centro_custo']} — {money(d['valor'])}" for d in dados]
            return {"text": "📊 **Gastos por Centro de Custo:**\n\n" + "\n".join(linhas), "buttons": menu_inicial}

        # === DEFAULT ===
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
