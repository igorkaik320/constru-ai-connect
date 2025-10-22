from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# === Importações dos módulos do Sienge ===
from sienge.sienge_pedidos import listar_pedidos_pendentes, itens_pedido, autorizar_pedido, reprovar_pedido
from sienge.sienge_boletos import buscar_boletos_por_cpf
from sienge.sienge_financeiro import resumo_financeiro_dre, gastos_por_obra, gastos_por_centro_custo
from sienge.sienge_ia import gerar_analise_financeira

# ============================================================
# ⚙️ CONFIGURAÇÕES GERAIS
# ============================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

class Message(BaseModel):
    user: str
    text: str


def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


# ============================================================
# 🚀 ENDPOINT PRINCIPAL
# ============================================================
@app.get("/")
def root():
    return {"message": "🚀 Backend da Constru.IA ativo com sucesso!"}


@app.post("/mensagem")
def mensagem(msg: Message):
    texto = msg.text.lower().strip()
    user = msg.user

    logging.info(f"📩 Mensagem recebida: {user} -> {texto}")

    try:
        # ============================================================
        # 🧠 ANÁLISE FINANCEIRA INTELIGENTE (IA)
        # ============================================================
        if "analisar finanças" in texto or "gerar análise" in texto:
            logging.info("🧠 Gerando análise financeira via OpenAI...")
            return {"text": gerar_analise_financeira()}

        # ============================================================
        # 💰 RESUMO FINANCEIRO / DRE
        # ============================================================
        elif "resumo financeiro" in texto or "dre" in texto:
            dre = resumo_financeiro_dre()
            resposta = (
                f"📊 **Resumo Financeiro (últimos 30 dias)**\n\n"
                f"💵 Receitas: {dre['formatado']['receitas']}\n"
                f"💸 Despesas: {dre['formatado']['despesas']}\n"
                f"📈 Lucro: {dre['formatado']['lucro']}"
            )
            return {
                "text": resposta,
                "buttons": [
                    {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
                    {"label": "🏢 Centro de Custo", "action": "gastos_por_centro_custo"},
                ],
            }

        # ============================================================
        # 🏗️ GASTOS POR OBRA
        # ============================================================
        elif "gastos por obra" in texto:
            obras = gastos_por_obra()
            if not obras:
                return {"text": "⚠️ Nenhum gasto encontrado por obra no período."}

            linhas = [f"🏗️ {o.get('obra', 'Sem nome')} — {money(o.get('valor', 0))}" for o in obras]
            resposta = "📊 **Gastos por Obra:**\n\n" + "\n".join(linhas)
            return {"text": resposta}

        # ============================================================
        # 🏢 GASTOS POR CENTRO DE CUSTO
        # ============================================================
        elif "gastos por centro" in texto or "centro de custo" in texto:
            centros = gastos_por_centro_custo()
            if not centros:
                return {"text": "⚠️ Nenhum gasto encontrado por centro de custo."}

            linhas = [f"🏢 {c.get('centro_custo', 'Sem nome')} — {money(c.get('valor', 0))}" for c in centros]
            resposta = "📊 **Gastos por Centro de Custo:**\n\n" + "\n".join(linhas)
            return {"text": resposta}

        # ============================================================
        # 💳 SEGUNDA VIA DE BOLETOS POR CPF
        # ============================================================
        elif "segunda via" in texto or "cpf" in texto:
            cpf = texto.replace("segunda via", "").replace("cpf", "").strip()
            if not cpf:
                return {"text": "⚠️ Por favor, informe o CPF para buscar boletos."}

            boletos = buscar_boletos_por_cpf(cpf)

            if isinstance(boletos, str):
                resposta = boletos
            elif isinstance(boletos, list) and boletos:
                linhas = [
                    f"💳 {b.get('descricao', 'Sem descrição')} — "
                    f"Venc: {b.get('vencimento', 'Sem data')} — "
                    f"{money(b.get('valor', 0))}"
                    for b in boletos
                ]
                resposta = "\n".join(linhas)
            else:
                resposta = "⚠️ Nenhum boleto disponível para esse CPF."

            return {
                "text": resposta,
                "buttons": [
                    {"label": "📋 Pedidos Pendentes", "action": "pedidos_pendentes"},
                    {"label": "💰 Resumo Financeiro", "action": "resumo_financeiro"},
                ],
            }

        # ============================================================
        # 📋 PEDIDOS PENDENTES
        # ============================================================
        elif "pedidos pendentes" in texto:
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "⚠️ Nenhum pedido pendente encontrado."}

            linhas = []
            for p in pedidos:
                fornecedor = p.get("fornecedor") or p.get("supplierName") or "Fornecedor não informado"
                valor = p.get("valor_total") or p.get("totalValue") or 0
                linhas.append(f"📦 Pedido {p.get('id')} — {fornecedor} — {money(valor)}")

            resposta = "📋 **Pedidos Pendentes:**\n\n" + "\n".join(linhas)
            return {
                "text": resposta,
                "buttons": [
                    {"label": "Ver Itens do Pedido", "action": "itens_pedido"},
                    {"label": "Autorizar Pedido", "action": "autorizar_pedido"},
                ],
            }

        # ============================================================
        # 🔍 ITENS DO PEDIDO
        # ============================================================
        elif texto.startswith("itens do pedido"):
            try:
                pedido_id = int(texto.replace("itens do pedido", "").strip())
                itens = itens_pedido(pedido_id)
                if not itens:
                    return {"text": f"⚠️ Nenhum item encontrado para o pedido {pedido_id}."}
                linhas = [
                    f"🔹 {i['descricao']} — {i['quantidade']} {i['unidade']} — {money(i['valor_unitario'])}"
                    for i in itens
                ]
                return {"text": f"🧾 **Itens do Pedido {pedido_id}:**\n\n" + "\n".join(linhas)}
            except:
                return {"text": "❌ Informe o número do pedido corretamente (ex: itens do pedido 123)."}

        # ============================================================
        # ✅ AUTORIZAR PEDIDO
        # ============================================================
        elif texto.startswith("autorizar pedido"):
            pedido_id = int(texto.replace("autorizar pedido", "").strip())
            r = autorizar_pedido(pedido_id)
            return {"text": f"✅ Pedido {pedido_id} autorizado com sucesso!" if r else f"❌ Erro ao autorizar pedido {pedido_id}."}

        # ============================================================
        # 🚫 REPROVAR PEDIDO
        # ============================================================
        elif texto.startswith("reprovar pedido"):
            pedido_id = int(texto.replace("reprovar pedido", "").strip())
            r = reprovar_pedido(pedido_id)
            return {"text": f"🚫 Pedido {pedido_id} reprovado com sucesso!" if r else f"❌ Erro ao reprovar pedido {pedido_id}."}

        # ============================================================
        # 🤖 PADRÃO (MENU PRINCIPAL)
        # ============================================================
        else:
            return {
                "text": (
                    "👋 Olá! Sou a **Constru.IA**, sua assistente integrada ao Sienge.\n\n"
                    "Posso te ajudar com:\n"
                    "📋 Pedidos Pendentes\n"
                    "💳 Segunda Via de Boletos\n"
                    "💰 Resumo Financeiro\n"
                    "🏗️ Gastos por Obra\n"
                    "🏢 Gastos por Centro de Custo\n"
                    "🤖 Análise Financeira Inteligente\n\n"
                    "Digite o comando desejado 👇"
                ),
                "buttons": [
                    {"label": "📋 Pedidos Pendentes", "action": "pedidos_pendentes"},
                    {"label": "💰 Resumo Financeiro", "action": "resumo_financeiro"},
                    {"label": "💳 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
                    {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
                    {"label": "🤖 Analisar Finanças", "action": "analisar_finanças"},
                ],
            }

    except Exception as e:
        logging.error(f"Erro geral: {e}", exc_info=True)
        return {"text": f"❌ Erro interno: {e}"}
