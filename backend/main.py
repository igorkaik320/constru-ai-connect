from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import re
import base64

# ============ IMPORTS DOS MÓDULOS ============
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
# opcional: análise IA (só se o arquivo existir)
try:
    from sienge.sienge_ia import gerar_analise_financeira
    HAVE_IA = True
except Exception:
    HAVE_IA = False

# ============ FASTAPI / CORS ============
logging.basicConfig(level=logging.INFO)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ MODELOS ============
class Message(BaseModel):
    user: str
    text: str

# ============ HELPERS ============
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def menu():
    return [
        {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "💰 Resumo Financeiro", "action": "resumo_financeiro"},
        {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
        {"label": "🏢 Gastos por Centro de Custo", "action": "gastos_por_centro_custo"},
        {"label": "🧾 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
        {"label": "🧠 Analisar Finanças", "action": "analisar_financas"},
    ]

# contexto por usuário (para o fluxo de CPF)
usuarios_contexto = {}  # { user_email: { "aguardando_cpf": True, "nome": "...", "cpf": "..." } }

# ============ NLP SIMPLES ============
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # saudações
    if t in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"}:
        return {"acao": "saudacao"}

    # botões / comandos curtos
    mapping_simples = {
        "listar_pedidos_pendentes": "listar_pedidos_pendentes",
        "pedidos pendentes": "listar_pedidos_pendentes",
        "resumo_financeiro": "resumo_financeiro",
        "resumo financeiro": "resumo_financeiro",
        "gastos_por_obra": "gastos_por_obra",
        "gastos por obra": "gastos_por_obra",
        "gastos_por_centro_de_custo": "gastos_por_centro_custo",
        "gastos por centro de custo": "gastos_por_centro_custo",
        "buscar_boletos_cpf": "buscar_boletos_cpf",
        "segunda via de boletos": "buscar_boletos_cpf",
        "analisar_financas": "analisar_financas",
        "analisar finanças": "analisar_financas",
    }
    if t in mapping_simples:
        return {"acao": mapping_simples[t]}

    # itens do pedido <id>
    m = (re.search(r"\bitens(?:\s+do)?\s+pedido\s+(\d+)\b", t)
         or re.search(r"\bitens\s+(\d+)\b", t)
         or re.search(r"\bpedido\s+(\d+)\s+itens\b", t)
         or re.search(r"\bver\s+itens\s+(\d+)\b", t))
    if m:
        return {"acao": "itens_pedido", "parametros": {"pedido_id": int(m.group(1))}}

    # autorizar / reprovar
    if "autorizar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {"acao": "autorizar_pedido"}
    if "reprovar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {"acao": "reprovar_pedido"}

    # gerar pdf <id>
    if "pdf" in t or "relatório" in t or "relatorio" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid)}} if pid else {"acao": "relatorio_pdf"}

    # "segunda via 420/5" -> link boleto
    if "segunda" in t and "via" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}

    # CPF (11 dígitos ou com pontuação)
    if re.search(r"\b\d{11}\b", t) or re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}

    return {"acao": None}

# ============ ENDPOINT ============
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    texto = (msg.text or "").strip()
    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    # mensagem inicial
    if not texto or acao == "saudacao":
        return {
            "text": (
                "👋 **Olá! Sou a Constru.IA**, sua assistente integrada ao Sienge.\n\n"
                "Posso te ajudar com:  \n"
                "• **Pedidos Pendentes**  \n"
                "• **Segunda Via de Boletos**  \n"
                "• **Resumo Financeiro**  \n"
                "• **Gastos por Obra**  \n"
                "• **Gastos por Centro de Custo**  \n"
                "• **Análise Financeira Inteligente**  \n\n"
                "Digite o comando desejado 👇"
            ),
            "buttons": menu(),
        }

    try:
        # ========== FLUXO DE CONFIRMAÇÃO/ESPERA DE CPF ==========
        # Se este usuário está no fluxo aguardando CPF
        ctx = usuarios_contexto.get(msg.user)
        if ctx and ctx.get("aguardando_cpf"):
            # só aceitaremos uma mensagem que contenha 11 dígitos
            cpf_raw = re.sub(r"\D", "", texto)
            if len(cpf_raw) != 11:
                return {
                    "text": "⚠️ CPF inválido. Envie apenas os 11 dígitos (com ou sem pontuação).",
                    "buttons": [{"label": "🔙 Voltar", "action": "saudacao"}],
                }

            # consulta boletos válidos para 2ª via
            resultado = buscar_boletos_por_cpf(cpf_raw)
            # encerra o modo de espera de CPF
            usuarios_contexto.pop(msg.user, None)

            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu()}

            nome = resultado.get("nome", "Cliente")
            boletos = resultado.get("boletos", [])

            if not boletos:
                return {"text": f"📭 Nenhum boleto disponível para segunda via de **{nome}**.", "buttons": menu()}

            linhas = []
            botoes = []
            for b in boletos:
                linhas.append(f"💳 **Título {b['titulo_id']}** — Parcela {b['parcela_id']} — {money(b['valor'])} — Venc.: {b['vencimento']}")
                botoes.append({
                    "label": f"2ª via {b['titulo_id']}/{b['parcela_id']}",
                    "action": f"segunda via {b['titulo_id']}/{b['parcela_id']}"
                })

            return {
                "text": f"📋 Boletos disponíveis para **{nome}:**\n\n" + "\n".join(linhas),
                "buttons": botoes or menu(),
            }

        # ========== AÇÕES ==========
        # BOLETOS: iniciar fluxo pedindo CPF
        if acao == "buscar_boletos_cpf":
            usuarios_contexto[msg.user] = {"aguardando_cpf": True}
            return {
                "text": "💳 Para localizar seus boletos, digite o **CPF do titular** (com ou sem pontuação).",
                "buttons": [{"label": "🔙 Voltar", "action": "saudacao"}],
            }

        # BOLETOS: usuário digitou CPF fora do fluxo (aceitamos também)
        if acao == "cpf_digitado":
            cpf_raw = re.sub(r"\D", "", parametros.get("cpf", ""))
            if len(cpf_raw) != 11:
                return {"text": "⚠️ CPF inválido. Envie os 11 dígitos.", "buttons": menu()}

            resultado = buscar_boletos_por_cpf(cpf_raw)
            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu()}

            nome = resultado.get("nome", "Cliente")
            boletos = resultado.get("boletos", [])
            if not boletos:
                return {"text": f"📭 Nenhum boleto disponível para segunda via de **{nome}**.", "buttons": menu()}

            linhas = []
            botoes = []
            for b in boletos:
                linhas.append(f"💳 **Título {b['titulo_id']}** — Parcela {b['parcela_id']} — {money(b['valor'])} — Venc.: {b['vencimento']}")
                botoes.append({
                    "label": f"2ª via {b['titulo_id']}/{b['parcela_id']}",
                    "action": f"segunda via {b['titulo_id']}/{b['parcela_id']}"
                })

            return {
                "text": f"📋 Boletos disponíveis para **{nome}:**\n\n" + "\n".join(linhas),
                "buttons": botoes or menu(),
            }

        # BOLETOS: gerar link de uma 2ª via específica
        if acao == "link_boleto":
            titulo = int(parametros.get("titulo_id"))
            parcela = int(parametros.get("parcela_id"))
            msg_link = gerar_link_boleto(titulo, parcela)
            return {"text": msg_link, "buttons": menu()}

        # PEDIDOS: pendentes
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes() or []
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização.", "buttons": menu()}

            linhas = []
            botoes = []
            for p in pedidos:
                pid = p.get("id") or p.get("orderId") or p.get("purchaseOrderId")
                fornecedor = (
                    p.get("fornecedor")
                    or p.get("supplierName")
                    or p.get("creditorName")
                    or p.get("supplier")
                    or "Fornecedor não informado"
                )
                total = p.get("valor_total") or p.get("totalAmount") or p.get("amount") or 0.0
                linhas.append(f"• Pedido {pid} — {fornecedor} — {money(total)}")
                botoes.append({"label": f"📦 Itens do pedido {pid}", "action": f"itens do pedido {pid}"})

            return {"text": "📋 **Pedidos pendentes:**\n\n" + "\n".join(linhas), "buttons": botoes or menu()}

        # PEDIDOS: itens
        if acao == "itens_pedido":
            pedido_id = parametros.get("pedido_id")
            if not pedido_id:
                return {"text": "⚠️ Informe o número do pedido. Ex.: `itens do pedido 278`", "buttons": menu()}

            itens = itens_pedido(pedido_id) or []
            if not itens:
                return {"text": f"📭 Nenhum item encontrado para o pedido {pedido_id}.", "buttons": menu()}

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
                unidade = i.get("unit") or i.get("unity") or ""
                valor = i.get("totalAmount") or i.get("amount") or i.get("price") or 0
                linhas.append(f"• {descricao} — {quantidade} {unidade} — {money(valor)}")

            return {
                "text": f"📦 **Itens do pedido {pedido_id}:**\n\n" + "\n".join(linhas),
                "buttons": [
                    {"label": "✅ Autorizar", "action": f"autorizar pedido {pedido_id}"},
                    {"label": "❌ Reprovar", "action": f"reprovar pedido {pedido_id}"},
                    {"label": "📄 Gerar PDF", "action": f"gerar pdf pedido {pedido_id}"},
                ],
            }

        # PEDIDOS: autorizar / reprovar
        if acao == "autorizar_pedido":
            pid = parametros.get("pedido_id")
            if not pid:  # pode ter vindo sem número
                pid = next((p for p in texto.split() if p.isdigit()), None)
            if not pid:
                return {"text": "⚠️ Informe o número do pedido. Ex.: `autorizar pedido 278`", "buttons": menu()}
            resposta = autorizar_pedido(int(pid))
            return {"text": resposta, "buttons": menu()}

        if acao == "reprovar_pedido":
            pid = parametros.get("pedido_id")
            if not pid:
                pid = next((p for p in texto.split() if p.isdigit()), None)
            if not pid:
                return {"text": "⚠️ Informe o número do pedido. Ex.: `reprovar pedido 278`", "buttons": menu()}
            resposta = reprovar_pedido(int(pid))
            return {"text": resposta, "buttons": menu()}

        # PEDIDOS: PDF
        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            if not pid:
                pid = next((p for p in texto.split() if p.isdigit()), None)
            if not pid:
                return {"text": "⚠️ Informe o número do pedido. Ex.: `gerar pdf pedido 278`", "buttons": menu()}

            pdf_bytes = gerar_relatorio_pdf_bytes(int(pid))
            if not pdf_bytes:
                return {"text": "❌ Erro ao gerar o PDF do pedido.", "buttons": menu()}

            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {
                "text": f"📄 PDF do pedido {pid} gerado com sucesso!",
                "pdf_base64": pdf_base64,
                "filename": f"pedido_{pid}.pdf",
                "buttons": menu(),
            }

        # FINANCEIRO
        if acao == "resumo_financeiro":
            r = resumo_financeiro_dre()
            if not r or "periodo" not in r:
                return {"text": "❌ Não foi possível carregar o DRE agora.", "buttons": menu()}
            return {
                "text": (
                    f"📊 **Resumo Financeiro (DRE)**\n\n"
                    f"🗓️ Período: {r['periodo']['inicio']} até {r['periodo']['fim']}\n"
                    f"💰 Receitas: {r['formatado']['receitas']}\n"
                    f"💸 Despesas: {r['formatado']['despesas']}\n"
                    f"📈 Lucro: {r['formatado']['lucro']}"
                ),
                "buttons": menu(),
            }

        if acao == "gastos_por_obra":
            dados = gastos_por_obra() or []
            if not dados:
                return {"text": "⚠️ Nenhum dado encontrado para obras no período.", "buttons": menu()}
            linhas = [f"🏗️ {d.get('obra','(sem nome)')} — {money(d.get('valor',0))}" for d in dados]
            return {"text": "📊 **Gastos por Obra:**\n\n" + "\n".join(linhas), "buttons": menu()}

        if acao == "gastos_por_centro_custo":
            dados = gastos_por_centro_custo() or []
            if not dados:
                return {"text": "⚠️ Nenhum dado encontrado por centro de custo no período.", "buttons": menu()}
            linhas = [f"🏢 {d.get('centro_custo','(não informado)')} — {money(d.get('valor',0))}" for d in dados]
            return {"text": "📊 **Gastos por Centro de Custo:**\n\n" + "\n".join(linhas), "buttons": menu()}

        # ANÁLISE IA (opcional)
        if acao == "analisar_financas":
            if not HAVE_IA:
                return {
                    "text": "🧠 O módulo de análise IA não está ativo neste deploy. "
                            "Adicione o arquivo `sienge_ia.py` e a variável de ambiente `OPENAI_API_KEY`.",
                    "buttons": menu(),
                }
            try:
                texto_ia = gerar_analise_financeira()
                return {"text": texto_ia, "buttons": menu()}
            except Exception as e:
                logging.exception("Erro análise IA:")
                return {"text": f"❌ Erro na análise IA: {e}", "buttons": menu()}

        # fallback
        return {"text": "🤖 Não entendi o comando. Use os botões ou digite um dos comandos do menu.", "buttons": menu()}

    except Exception as e:
        logging.exception("Erro geral:")
        return {"text": f"❌ Ocorreu um erro: {e}", "buttons": menu()}

# ============ HEALTH ============
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
