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

# CORS liberado
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

    # === Listar pedidos pendentes ===
    if "pendente" in texto:
        pedidos = listar_pedidos_pendentes()
        if not pedidos:
            return {"text": "📭 Nenhum pedido pendente de autorização encontrado."}
        resposta = "📋 *Pedidos pendentes de autorização:*\n\n"
        for p in pedidos:
            resposta += f"• Pedido {p['id']} — {p.get('supplierName', 'Fornecedor não informado')} — {fmt(p.get('totalAmount', 0))}\n"
        return {"text": resposta.strip()}

    # === Itens do pedido ===
    if "item" in texto or "itens" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Por favor, informe o número do pedido."}

        pedido = buscar_pedido_por_id(pid)
        empresa = buscar_empresa(pedido.get("companyId")) if pedido.get("companyId") else {}
        obra = buscar_obra(pedido.get("buildingId")) if pedido.get("buildingId") else {}
        centro = buscar_centro_custo(pedido.get("costCenterId")) if pedido.get("costCenterId") else {}
        forn = buscar_fornecedor(pedido.get("supplierId")) if pedido.get("supplierId") else {}

        itens = itens_pedido(pid)
        linhas = "\n".join([
            f"🔹 {i.get('resourceDescription')} ({i.get('quantity')} {i.get('unitOfMeasure')}) — {fmt(i.get('unitPrice'))}"
            for i in itens
        ])

        texto_resumo = f"""
🧾 *Resumo do Pedido {pid}:*
🗓️ Data: {pedido.get('date', 'Não informado')}
🏢 Empresa: {empresa.get('name', 'Não informado')}
🏗️ Obra: {obra.get('name', 'Não informado')}
💰 Centro de Custo: {centro.get('description', 'Não informado')}
🤝 Fornecedor: {forn.get('name', 'Não informado')} (CNPJ {forn.get('taxpayerId', '-')})
💳 Condição de Pagamento: {pedido.get('paymentCondition', 'Não informada')}
📝 Observações: {pedido.get('notes', 'Sem observações')}
💵 Valor Total: {fmt(pedido.get('totalAmount', 0))}

📦 *Itens:*
{linhas if linhas else 'Nenhum item encontrado.'}
        """.strip()

        botoes = [
            {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
            {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
            {"label": "Voltar ao Menu", "action": "menu_inicial"}
        ]
        return {"text": texto_resumo, "buttons": botoes}

    # === Autorizar pedido ===
    if "autorizar" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Informe o número do pedido para autorizar."}
        sucesso = autorizar_pedido(pid)
        return {"text": "✅ Pedido autorizado!" if sucesso else "❌ Falha ao autorizar."}

    # === Reprovar pedido ===
    if "reprovar" in texto:
        pid = "".join(filter(str.isdigit, texto))
        if not pid:
            return {"text": "Informe o número do pedido para reprovar."}
        sucesso = reprovar_pedido(pid)
        return {"text": "🚫 Pedido reprovado!" if sucesso else "❌ Falha ao reprovar."}

    return {"text": "Desculpe, não entendi sua solicitação."}
