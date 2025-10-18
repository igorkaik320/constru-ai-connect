from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import logging
import base64
import openai

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    buscar_pedido_por_id,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes
)

logging.basicConfig(level=logging.INFO)
app = FastAPI()

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODELO DE MENSAGEM ===
class Message(BaseModel):
    user: str
    text: str


# === INTERPRETAÇÃO DA MENSAGEM ===
def entender_intencao(texto: str):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""
Você é uma assistente chamada *Constru.IA*, educada e especialista no sistema Sienge.
Analise a mensagem do usuário e diga o que ele quer fazer.

Responda em JSON no formato:
{{
  "acao": "listar_pedidos_pendentes" | "itens_pedido" | "autorizar_pedido" | "reprovar_pedido" | "relatorio_pdf",
  "parametros": {{ "pedido_id": <número opcional> }}
}}

Mensagem: "{texto}"
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        conteudo = response.choices[0].message.content
        conteudo = conteudo.replace("```json", "").replace("```", "").strip()
        return json.loads(conteudo)
    except Exception as e:
        logging.error(f"Erro IA: {e}")
        return {"acao": None, "erro": str(e)}


# === FORMATAÇÃO DE TABELA DE ITENS ===
def formatar_itens_tabela(itens):
    if not itens:
        return None
    headers = ["Código", "Descrição", "Qtd", "Unid", "Vlr Unit", "Total"]
    rows = []
    total = 0
    for item in itens:
        cod = item.get("resourceCode") or "-"
        desc = item.get("resourceDescription") or item.get("description", "")
        qtd = item.get("quantity", 0)
        unid = item.get("unit", "")
        valor_unit = item.get("unitPrice", 0)
        subtotal = round(qtd * valor_unit, 2)
        total += subtotal
        rows.append([cod, desc, qtd, unid, valor_unit, subtotal])
    return {"headers": headers, "rows": rows, "total": total}


# === ENDPOINT PRINCIPAL ===
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
        return {"text": "Olá 👋! Sou a Constru.IA. Em que posso ajudar hoje?", "buttons": menu}

    try:
        # === LISTAR PEDIDOS PENDENTES ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu}

            texto = "📋 *Pedidos pendentes de autorização:*\n\n"
            botoes = []
            for p in pedidos:
                fornecedor = p.get("supplierName", "Fornecedor não informado")
                valor = p.get("totalAmount", 0)
                texto += f"• Pedido {p['id']} — {fornecedor} — R$ {valor:,.2f}\n"
                botoes.append({
                    "label": f"Pedido {p['id']}",
                    "action": "itens_pedido",
                    "pedido_id": p["id"]
                })
            return {"text": texto.strip(), "buttons": botoes}

        # === MOSTRAR ITENS DO PEDIDO ===
        elif acao == "itens_pedido":
            pid = params.get("pedido_id")
            if not pid:
                return {"text": "Por favor, informe o número do pedido.", "buttons": menu}

            pedido = buscar_pedido_por_id(pid)
            itens = itens_pedido(pid)

            if not pedido:
                return {"text": f"❌ Pedido {pid} não encontrado.", "buttons": menu}
            if not itens:
                return {"text": f"❌ Nenhum item encontrado no pedido {pid}.", "buttons": menu}

            resumo = f"""
📄 *Resumo do Pedido {pid}:*

🏢 Empresa: {pedido.get('enterprise', {}).get('name', 'Não informado')}
🏗️ Obra: {pedido.get('job', {}).get('name', 'Não informado')}
💰 Centro de Custo: {pedido.get('costCenter', {}).get('name', 'Não informado')}
📦 Fornecedor: {pedido.get('supplier', {}).get('corporateName', 'Não informado')} (CNPJ {pedido.get('supplier', {}).get('cnpj', '-')})
🧾 Condição de Pagamento: {pedido.get('paymentCondition', {}).get('description', 'Não informado')}
📝 Observações: {pedido.get('observation', 'Sem observações')}
💵 Valor Total: R$ {pedido.get('totalAmount', 0):,.2f}
"""

            tabela = formatar_itens_tabela(itens)
            botoes = [
                {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
                {"label": "Voltar ao Menu", "action": "menu_inicial"}
            ]
            return {"text": resumo, "table": tabela, "buttons": botoes}

        # === AUTORIZAR ===
        elif acao == "autorizar_pedido":
            pid = params.get("pedido_id")
            if not pid:
                return {"text": "Informe o número do pedido a autorizar.", "buttons": menu}
            sucesso = autorizar_pedido(pid)
            if sucesso:
                return {"text": f"✅ Pedido {pid} autorizado com sucesso!", "buttons": menu}
            return {"text": f"❌ Falha ao autorizar o pedido {pid}.", "buttons": menu}

        # === REPROVAR ===
        elif acao == "reprovar_pedido":
            pid = params.get("pedido_id")
            if not pid:
                return {"text": "Informe o número do pedido a reprovar.", "buttons": menu}
            sucesso = reprovar_pedido(pid)
            if sucesso:
                return {"text": f"🚫 Pedido {pid} reprovado com sucesso!", "buttons": menu}
            return {"text": f"❌ Falha ao reprovar o pedido {pid}.", "buttons": menu}

        # === PDF ===
        elif acao == "relatorio_pdf":
            pid = params.get("pedido_id")
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if pdf_bytes:
                pdf_base64 = base64.b64encode(pdf_bytes).decode()
                return {"text": f"📄 PDF do pedido {pid} gerado com sucesso!", "pdf_base64": pdf_base64}
            return {"text": "❌ Erro ao gerar o PDF.", "buttons": menu}

        else:
            return {"text": "Desculpe, não entendi o que você quis dizer.", "buttons": menu}

    except Exception as e:
        logging.error("Erro geral:", exc_info=e)
        return {"text": f"Ocorreu um erro ao processar sua solicitação: {e}", "buttons": menu}
