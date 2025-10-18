from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import base64
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    buscar_pedido_por_id,
    buscar_empresa,
    buscar_obra,
    buscar_centro_custo,
    buscar_fornecedor,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes
)

logging.basicConfig(level=logging.INFO)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    user: str
    text: str

def fmt(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

@app.post("/mensagem")
async def mensagem(msg: Message):
    texto = msg.text.lower().strip()
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {texto}")

    botoes_iniciais = [
        {"label": "Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "Emitir PDF", "action": "relatorio_pdf"},
        {"label": "Ver Itens do Pedido", "action": "itens_pedido"}
    ]

    if any(p in texto for p in ["menu", "voltar", "início", "inicio"]):
        return {"text": "Escolha uma opção abaixo 👇", "buttons": botoes_iniciais}

    # === LISTAR PEDIDOS ===
    if "pendente" in texto:
        pedidos = listar_pedidos_pendentes()
        if not pedidos:
            return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": botoes_iniciais}
        resposta = "📋 *Pedidos pendentes de autorização:*\n\n"
        for p in pedidos:
            resposta += f"• Pedido {p['id']} — {p.get('supplierName', 'Fornecedor não informado')} — {fmt(p.get('totalAmount', 0))}\n"
        return {"text": resposta.strip(), "buttons": botoes_iniciais}

    # === ITENS DO PEDIDO ===
    if "item" in texto or "itens" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Por favor, informe o número do pedido.", "buttons": botoes_iniciais}

        pedido = buscar_pedido_por_id(pid)
        if not pedido:
            return {"text": f"❌ Pedido {pid} não encontrado.", "buttons": botoes_iniciais}

        empresa = buscar_empresa(pedido.get("companyId")) or {}
        obra = buscar_obra(pedido.get("buildingId")) or {}
        centro = buscar_centro_custo(pedido.get("costCenterId")) or {}
        forn = buscar_fornecedor(pedido.get("supplierId")) or {}

        nome_empresa = empresa.get("name") or pedido.get("companyName", "Não informado")
        nome_obra = obra.get("name") or f"Obra {pedido.get('buildingId', 'Não informada')}"
        nome_cc = centro.get("description", "Não informado")
        nome_forn = forn.get("name") or pedido.get("supplierName", "Não informado")
        cnpj_forn = forn.get("taxpayerId", "-")

        itens = itens_pedido(pid)
        linhas = "\n".join([
            f"🔹 {i.get('resourceDescription')} ({i.get('quantity')} {i.get('unitOfMeasure')}) — {fmt(i.get('unitPrice'))}"
            for i in itens
        ]) or "Nenhum item encontrado."

        observacoes = pedido.get("notes", "Sem observações").replace("\\r\\n", "\n")

        texto_resumo = f"""
🧾 *Resumo do Pedido {pid}:*
🗓️ Data: {pedido.get('date', 'Não informado')}
🏢 Empresa: {nome_empresa}
🏗️ Obra: {nome_obra}
💰 Centro de Custo: {nome_cc}
🤝 Fornecedor: {nome_forn} (CNPJ {cnpj_forn})
💳 Condição de Pagamento: {pedido.get('paymentCondition', 'Não informada')}
📝 Observações: {observacoes}
💵 Valor Total: {fmt(pedido.get('totalAmount', 0))}

📦 *Itens:*
{linhas}
        """.strip()

        botoes = [
            {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
            {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
            {"label": "Voltar ao Menu", "action": "menu_inicial"}
        ]
        return {"text": texto_resumo, "buttons": botoes}

    # === AUTORIZAR ===
    if "autorizar" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Informe o número do pedido para autorizar.", "buttons": botoes_iniciais}
        sucesso = autorizar_pedido(pid)
        return {"text": "✅ Pedido autorizado!" if sucesso else "❌ Falha ao autorizar.", "buttons": botoes_iniciais}

    # === REPROVAR ===
    if "reprovar" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Informe o número do pedido para reprovar.", "buttons": botoes_iniciais}
        sucesso = reprovar_pedido(pid)
        return {"text": "🚫 Pedido reprovado!" if sucesso else "❌ Falha ao reprovar.", "buttons": botoes_iniciais}

    # === EMITIR PDF ===
    if "pdf" in texto or "relatorio" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Por favor, informe o número do pedido para gerar o PDF.", "buttons": botoes_iniciais}

        pdf_bytes = gerar_relatorio_pdf_bytes(pid)
        if not pdf_bytes:
            return {"text": f"❌ Não foi possível gerar o PDF do pedido {pid}.", "buttons": botoes_iniciais}

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        link = f"data:application/pdf;base64,{pdf_base64}"
        return {
            "text": f"📄 PDF do Pedido {pid} gerado com sucesso!\n\n[🔗 Clique aqui para visualizar o relatório]({link})",
            "buttons": botoes_iniciais
        }

    return {"text": "Desculpe, não entendi sua solicitação.", "buttons": botoes_iniciais}
