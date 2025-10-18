from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import logging
import base64

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    buscar_pedido_por_id,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes
)

logging.basicConfig(level=logging.INFO)
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo
class Message(BaseModel):
    user: str
    text: str

# === IA para entender comandos ===
def entender_intencao(texto: str):
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")

    prompt = f"""
Você é uma assistente inteligente e educada chamada Constru.IA, especialista no sistema Sienge.
Identifique o que o usuário deseja fazer e retorne um JSON com o formato:
{{
  "acao": "...",
  "parametros": {{ ... }}
}}

Ações possíveis:
- listar_pedidos_pendentes
- itens_pedido (pedido_id)
- autorizar_pedido (pedido_id)
- reprovar_pedido (pedido_id)
- relatorio_pdf (pedido_id)

Mensagem do usuário: "{texto}"
"""

    try:
        resposta = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        conteudo = resposta.choices[0].message.content
        conteudo = conteudo.replace("```json", "").replace("```", "").strip()
        return json.loads(conteudo)
    except Exception as e:
        logging.error(f"Erro IA: {e}")
        return {"acao": None, "erro": str(e)}

# === Função para formatar tabela ===
def formatar_itens_tabela(itens):
    if not itens:
        return None
    headers = ["Código", "Descrição", "Qtd", "Unid", "Vlr Unit", "Total"]
    rows = []
    total = 0
    for item in itens:
        cod = item.get("resourceCode") or "-"
        desc = item.get("resourceDescription") or item.get("description")
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
        # === LISTAR PEDIDOS ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu}

            resposta = "📋 *Pedidos pendentes de autorização:*\n\n"
            botoes = []
            for p in pedidos:
                resposta += f"• Pedido {p['id']} — {p.get('supplierName', 'Fornecedor não informado')}\n"
                botoes.append({
                    "label": f"Pedido {p['id']}",
                    "action": "itens_pedido",
                    "pedido_id": p["id"]
                })
            return {"text": resposta.strip(), "buttons": botoes}

        # === ITENS DO PEDIDO ===
        elif acao == "itens_pedido":
            pid = params.get("pedido_id")
            if not pid:
                return {"text": "Por favor, informe o número do pedido.", "buttons": menu}

            pedido = buscar_pedido_por_id(pid)
            itens = itens_pedido(pid)

            if not pedido:
                return {"text": f"❌ Não encontrei o pedido {pid}.", "buttons": menu}
            if not itens:
                logging.warning(f"Nenhum item encontrado no pedido {pid}.")
                return {"text": f"❌ Nenhum item encontrado no pedido {pid}.", "buttons": menu}

            resumo = f"""
Olá 👋! Segue abaixo o resumo do pedido **{pid}**:

🏢 *Empresa:* {pedido.get('enterpriseName', 'Não informado')}
🏗️ *Obra:* {pedido.get('jobName', 'Não informado')}
💰 *Centro de Custo:* {pedido.get('costCenterName', 'Não informado')}
📦 *Fornecedor:* {pedido.get('supplierName', 'Não informado')} (CNPJ {pedido.get('supplierCnpj', '-')})
🧾 *Condição de Pagamento:* {pedido.get('paymentCondition', 'Não informado')}
📝 *Observações:* {pedido.get('observation', 'Sem observações')}
💵 *Valor Total:* R$ {pedido.get('totalAmount', 0):,.2f}
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
            sucesso = autorizar_pedido(pid)
            if sucesso:
                return {"text": f"✅ Pedido {pid} autorizado com sucesso!", "buttons": menu}
            return {"text": f"❌ Não foi possível autorizar o pedido {pid}.", "buttons": menu}

        # === REPROVAR ===
        elif acao == "reprovar_pedido":
            pid = params.get("pedido_id")
            sucesso = reprovar_pedido(pid)
            if sucesso:
                return {"text": f"🚫 Pedido {pid} reprovado com sucesso!", "buttons": menu}
            return {"text": f"❌ Não foi possível reprovar o pedido {pid}.", "buttons": menu}

        # === PDF ===
        elif acao == "relatorio_pdf":
            pid = params.get("pedido_id")
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if pdf_bytes:
                pdf_base64 = base64.b64encode(pdf_bytes).decode()
                return {"text": f"📄 PDF do pedido {pid} gerado com sucesso!", "pdf_base64": pdf_base64}
            return {"text": "❌ Erro ao gerar o PDF.", "buttons": menu}

        return {"text": f"Desculpe, não entendi o comando '{acao}'.", "buttons": menu}

    except Exception as e:
        logging.error("Erro geral:", exc_info=e)
        return {"text": f"Ocorreu um erro ao executar a ação: {e}", "buttons": menu}
