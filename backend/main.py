from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import logging
import base64

from sienge_pedidos import (
    listar_pedidos_pendentes,
    buscar_pedido_por_id,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes
)

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelo de mensagem ---
class Message(BaseModel):
    user: str
    text: str

# --- Memória de contexto (simples por usuário) ---
user_context = {}

# --- Função auxiliar para formatação de valores ---
def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Função: formatar tabela de itens ---
def formatar_itens_tabela(itens):
    if not itens:
        return None

    headers = ["Nº", "Descrição", "Qtd", "Unid", "Valor Unit.", "Total"]
    rows = []
    total_geral = 0

    for i, item in enumerate(itens, 1):
        desc = item.get("resourceDescription") or "Sem descrição"
        qtd = item.get("quantity", 0)
        unid = item.get("unitOfMeasure") or "-"
        valor_unit = item.get("unitPrice") or 0.0
        total = qtd * valor_unit
        total_geral += total

        rows.append([
            i,
            desc,
            round(qtd, 2),
            unid,
            fmt(valor_unit),
            fmt(total)
        ])

    return {"headers": headers, "rows": rows, "total": fmt(total_geral)}

# --- Interpretação simples ---
def entender_intencao(texto: str):
    texto = texto.lower().strip()
    if "pedido" in texto and ("item" in texto or "itens" in texto):
        pid = "".join(filter(str.isdigit, texto))
        return {"acao": "itens_pedido", "parametros": {"pedido_id": pid if pid else None}}
    if "autorizar" in texto:
        pid = "".join(filter(str.isdigit, texto))
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": pid if pid else None}}
    if "reprovar" in texto:
        pid = "".join(filter(str.isdigit, texto))
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": pid if pid else None}}
    if "pdf" in texto:
        pid = "".join(filter(str.isdigit, texto))
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": pid if pid else None}}
    if "pendente" in texto or "listar" in texto:
        return {"acao": "listar_pedidos_pendentes", "parametros": {}}
    return {"acao": None, "parametros": {}}

# --- Endpoint principal ---
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    intencao = entender_intencao(msg.text)
    acao = intencao.get("acao")
    params = intencao.get("parametros", {})

    menu = [
        {"label": "Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "Emitir PDF", "action": "relatorio_pdf"},
        {"label": "Ver Itens do Pedido", "action": "itens_pedido"}
    ]

    if not acao:
        return {"text": "Escolha uma opção:", "buttons": menu}

    try:
        # --- Listar pedidos pendentes ---
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu}

            texto = "📋 *Pedidos pendentes de autorização:*\n\n"
            botoes = []
            for p in pedidos:
                texto += f"• Pedido {p['id']} — Fornecedor: {p.get('supplierName', 'não informado')} — {fmt(p.get('totalAmount', 0))}\n"
                botoes.append({"label": f"Pedido {p['id']}", "action": "itens_pedido", "pedido_id": p["id"]})

            return {"text": texto.strip(), "buttons": botoes or menu}

        # --- Itens do pedido ---
        elif acao == "itens_pedido":
            pid = params.get("pedido_id") or user_context.get(msg.user)
            if not pid:
                return {"text": "Por favor, informe o número do pedido.", "buttons": menu}
            pid = int(pid)
            user_context[msg.user] = pid

            pedido = buscar_pedido_por_id(pid)
            itens = itens_pedido(pid)
            tabela = formatar_itens_tabela(itens)

            resumo = f"""🧾 *Resumo do Pedido {pid}:*
🏢 Empresa: Não informado
🏗️ Obra: Não informado
💰 Centro de Custo: Não informado
🤝 Fornecedor: {pedido.get('supplierName', 'Não informado')} (CNPJ -)
🧾 Condição de Pagamento: {pedido.get('paymentCondition', 'Não informada')}
📝 Observações: {pedido.get('notes', 'Sem observações')}
💵 Valor Total: {fmt(pedido.get('totalAmount', 0))}
"""

            botoes = [
                {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
                {"label": "Voltar ao Menu", "action": "menu_inicial"}
            ]

            return {"text": resumo, "table": tabela, "buttons": botoes}

        # --- Autorizar ---
        elif acao == "autorizar_pedido":
            pid = params.get("pedido_id") or user_context.get(msg.user)
            if not pid:
                return {"text": "Informe o número do pedido para autorizar.", "buttons": menu}
            pid = int(pid)
            sucesso = autorizar_pedido(pid)
            if sucesso:
                return {"text": f"✅ Pedido {pid} autorizado com sucesso!", "buttons": menu}
            return {"text": f"❌ Falha ao autorizar o pedido {pid}.", "buttons": menu}

        # --- Reprovar ---
        elif acao == "reprovar_pedido":
            pid = params.get("pedido_id") or user_context.get(msg.user)
            if not pid:
                return {"text": "Informe o número do pedido para reprovar.", "buttons": menu}
            pid = int(pid)
            sucesso = reprovar_pedido(pid)
            if sucesso:
                return {"text": f"🚫 Pedido {pid} reprovado com sucesso!", "buttons": menu}
            return {"text": f"❌ Falha ao reprovar o pedido {pid}.", "buttons": menu}

        # --- PDF ---
        elif acao == "relatorio_pdf":
            pid = params.get("pedido_id") or user_context.get(msg.user)
            if not pid:
                return {"text": "Informe o número do pedido para gerar o PDF.", "buttons": menu}
            pid = int(pid)
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if pdf_bytes:
                pdf_base64 = base64.b64encode(pdf_bytes).decode()
                return {
                    "text": f"📄 PDF do pedido {pid} gerado com sucesso!",
                    "pdf_base64": pdf_base64,
                    "filename": f"pedido_{pid}.pdf",
                    "buttons": menu
                }
            return {"text": "❌ Erro ao gerar o PDF.", "buttons": menu}

        else:
            return {"text": f"Ação '{acao}' não reconhecida.", "buttons": menu}

    except Exception as e:
        logging.error("Erro geral:", exc_info=e)
        return {"text": f"Ocorreu um erro ao processar sua solicitação: {e}", "buttons": menu}
