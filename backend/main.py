from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    buscar_pedido_por_id,
    itens_pedido,
    buscar_obra,
    buscar_centro_custo,
    buscar_fornecedor,
    buscar_totalizacao,
    autorizar_pedido,
    reprovar_pedido,
    gerar_pdf_pedido_base64
)

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

logging.basicConfig(level=logging.INFO)

@app.get("/")
def root():
    return {"message": "🚀 Constru.IA backend ativo!"}


@app.post("/mensagem")
def mensagem(msg: Message):
    texto = msg.text.lower().strip()
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {texto}")

    try:
        # --- Pedidos pendentes ---
        if "pedidos pendentes" in texto:
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"resposta": "📭 Nenhum pedido pendente de autorização encontrado."}

            resposta = "📋 Pedidos pendentes de autorização:\n\n"
            for p in pedidos:
                resposta += f"• Pedido {p.get('id')} — Fornecedor não informado — R$ {p.get('totalAmount', 0):,.2f}\n"
            return {"resposta": resposta}

        # --- Itens do pedido ---
        if "itens" in texto and "pedido" in texto:
            numero = [t for t in texto.split() if t.isdigit()]
            if not numero:
                return {"resposta": "Por favor, informe o número do pedido."}

            pedido_id = numero[0]
            pedido = buscar_pedido_por_id(pedido_id)
            if not pedido:
                return {"resposta": f"❌ Pedido {pedido_id} não encontrado."}

            itens = itens_pedido(pedido_id)
            totalizacao = buscar_totalizacao(pedido_id)
            obra = buscar_obra(pedido.get("buildingId"))
            cc = buscar_centro_custo(pedido.get("costCenterId"))
            fornecedor = buscar_fornecedor(pedido.get("supplierId"))

            resumo = (
                f"🧾 Resumo do Pedido {pedido.get('id')}: "
                f"🗓️ Data: {pedido.get('date', '-')}\n"
                f"🏗️ Obra: {obra}\n"
                f"💰 Centro de Custo: {cc}\n"
                f"🤝 Fornecedor: {fornecedor}\n"
                f"👤 Comprador: {pedido.get('buyerId', '-')}\n"
                f"💳 Condição de Pagamento: {pedido.get('paymentCondition', '-')}\n"
                f"🧮 Valor Total: R$ {pedido.get('totalAmount', 0):,.2f}\n"
            )

            if pedido.get("notes"):
                resumo += f"📝 Observações: {pedido.get('notes')}\n"

            resumo += "\n📦 Itens:\n"
            for item in itens:
                resumo += f"🔹 {item.get('resourceDescription', 'Item')} ({item.get('quantity')} {item.get('unitOfMeasure')}) — R$ {item.get('unitPrice', 0):,.2f}\n"

            return {"resposta": resumo}

        # --- Autorizar pedido ---
        if texto.startswith("autorizar_pedido"):
            pedido_id = texto.split()[-1]
            status = autorizar_pedido(pedido_id)
            return {"resposta": "✅ Pedido autorizado!" if status == 200 else "❌ Falha ao autorizar o pedido."}

        # --- Reprovar pedido ---
        if texto.startswith("reprovar_pedido"):
            pedido_id = texto.split()[-1]
            status = reprovar_pedido(pedido_id)
            return {"resposta": "🚫 Pedido reprovado!" if status == 200 or status == 204 else "❌ Falha ao reprovar o pedido."}

        # --- Gerar PDF ---
        if "emitir pdf" in texto or "gerar pdf" in texto:
            numero = [t for t in texto.split() if t.isdigit()]
            if not numero:
                return {"resposta": "Por favor, informe o número do pedido para gerar o PDF."}

            pedido_id = numero[0]
            pedido = buscar_pedido_por_id(pedido_id)
            if not pedido:
                return {"resposta": f"❌ Pedido {pedido_id} não encontrado."}

            itens = itens_pedido(pedido_id)
            totalizacao = buscar_totalizacao(pedido_id)
            pdf_base64 = gerar_pdf_pedido_base64(pedido, itens, totalizacao)
            return {
                "resposta": f"📄 PDF do pedido {pedido_id} gerado com sucesso!",
                "pdf_base64": pdf_base64
            }

        # --- Caso não entenda ---
        return {"resposta": "Desculpe, não entendi sua solicitação."}

    except Exception as e:
        logging.error("Erro geral:", exc_info=True)
        return {"resposta": f"Ocorreu um erro: {str(e)}"}
