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
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes,
    buscar_pedido_por_id,
    buscar_obra,
    buscar_centro_custo,
    buscar_fornecedor,
)
from sienge.sienge_boletos import gerar_link_boleto, enviar_boleto_email  # 🧾 integração nova

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# ===== CORS =====
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


# ===== Util =====
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def formatar_itens_tabela(itens):
    if not itens:
        return None
    headers = ["Nº", "Código", "Descrição", "Qtd", "Unid", "Valor Unit", "Total"]
    rows = []
    total_geral = 0.0
    for i, item in enumerate(itens, 1):
        codigo = item.get("resourceCode") or "-"
        desc = (
            item.get("resourceDescription")
            or item.get("resourceReference")
            or "Sem descrição"
        )
        qtd = float(item.get("quantity") or 0)
        unid = item.get("unitOfMeasure") or "-"
        valor_unit = float(item.get("unitPrice") or 0)
        total = qtd * valor_unit
        total_geral += total
        rows.append([i, codigo, desc, qtd, unid, round(valor_unit, 2), round(total, 2)])
    return {"headers": headers, "rows": rows, "total": round(total_geral, 2)}


# ===== NLU =====
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # PEDIDOS
    if any(k in t for k in ["pedidos pendentes", "listar pendentes", "listar_pedidos_pendentes"]):
        return {"acao": "listar_pedidos_pendentes", "parametros": {}}

    if t.startswith("itens do pedido"):
        partes = t.split()
        pid = next((p for p in partes if p.isdigit()), None)
        if pid:
            return {"acao": "itens_pedido", "parametros": {"pedido_id": int(pid)}}

    if t.startswith("autorizar_pedido") or "autorizar pedido" in t:
        partes = t.split()
        pid = next((p for p in partes if p.isdigit()), None)
        if pid:
            return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}}

    if t.startswith("reprovar_pedido") or "reprovar pedido" in t:
        partes = t.split()
        pid = next((p for p in partes if p.isdigit()), None)
        if pid:
            return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}}

    if "pdf" in t or "relatório" in t or t.startswith("relatorio_pdf"):
        pid = next((p for p in t.split() if p.isdigit()), None)
        if pid:
            return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid)}}

    # BOLETOS 🧾
    if "enviar boleto" in t:
        nums = [int(n) for n in t.split() if n.isdigit()]
        if len(nums) >= 2:
            return {"acao": "enviar_boleto", "parametros": {"titulo_id": nums[0], "parcela_id": nums[1]}}

    if "link boleto" in t or "segunda via boleto" in t or "gerar link boleto" in t:
        nums = [int(n) for n in t.split() if n.isdigit()]
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": nums[0], "parcela_id": nums[1]}}

    return {"acao": None}


# ===== Avisos =====
def obter_aviso_pedido(pedido_id: int):
    pedido = buscar_pedido_por_id(pedido_id)
    if not pedido:
        return None
    avisos = pedido.get("alerts", []) or []
    if not avisos:
        return None
    return "\n".join([f"- {a.get('message')}" for a in avisos])


# ===== Endpoint principal =====
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info("📩 Mensagem recebida: %s -> %s", msg.user, msg.text)

    intencao = entender_intencao(msg.text or "")
    logging.info("🧠 Interpretação IA -> %s", intencao)

    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    menu_inicial = [
        {"label": "Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "Emitir PDF", "action": "relatorio_pdf"},
        {"label": "Ver Itens do Pedido", "action": "itens_pedido"},
        {"label": "Enviar Boleto", "action": "enviar_boleto"},
        {"label": "Gerar Link Boleto", "action": "link_boleto"},
    ]

    if not acao:
        return {"text": "Escolha uma opção:", "buttons": menu_inicial}

    try:
        # === PEDIDOS ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu_inicial}

            linhas = []
            botoes = []
            for p in pedidos:
                pid = p.get("id")
                total = money(p.get("totalAmount"))
                fornecedor = "Fornecedor não informado"
                linhas.append(f"• Pedido {pid} — {fornecedor} — {total}")
                botoes.append({"label": f"Pedido {pid}", "action": "itens_pedido", "pedido_id": pid})

            return {"text": "📋 Pedidos pendentes de autorização:\n\n" + "\n".join(linhas),
                    "buttons": menu_inicial}

        if acao == "itens_pedido":
            pid = parametros.get("pedido_id")
            if not pid:
                return {"text": "Informe o número do pedido.", "buttons": menu_inicial}

            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"text": f"❌ Pedido {pid} não encontrado.", "buttons": menu_inicial}

            obra = buscar_obra(pedido.get("buildingId"))
            cc = buscar_centro_custo(pedido.get("costCenterId"))
            forn = buscar_fornecedor(pedido.get("supplierId"))

            itens = itens_pedido(pid)
            resumo = (
                f"🧾 Pedido {pid}\n"
                f"🏗️ Obra: {(obra or {}).get('description', '-')}\n"
                f"💰 Centro de Custo: {(cc or {}).get('description', '-')}\n"
                f"🤝 Fornecedor: {(forn or {}).get('name', '-')}\n"
                f"💵 Total: {money(pedido.get('totalAmount'))}\n"
            )
            if itens:
                resumo += "\n📦 Itens:\n" + "\n".join(
                    [f"- {i.get('resourceDescription')} ({i.get('quantity')} {i.get('unitOfMeasure')})"
                     for i in itens]
                )
            botoes = [
                {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
            ]
            return {"text": resumo, "buttons": botoes}

        if acao == "autorizar_pedido":
            pid = parametros.get("pedido_id")
            ok = autorizar_pedido(pid)
            return {"text": "✅ Pedido autorizado!" if ok else "❌ Falha ao autorizar.", "buttons": menu_inicial}

        if acao == "reprovar_pedido":
            pid = parametros.get("pedido_id")
            ok = reprovar_pedido(pid)
            return {"text": "🚫 Pedido reprovado!" if ok else "❌ Falha ao reprovar.", "buttons": menu_inicial}

        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if not pdf_bytes:
                return {"text": "❌ Não foi possível gerar o PDF.", "buttons": menu_inicial}
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            return {"text": f"📄 PDF do pedido {pid} gerado com sucesso!", "pdf_base64": pdf_b64}

        # === BOLETOS ===
        if acao == "enviar_boleto":
            titulo = parametros.get("titulo_id")
            parcela = parametros.get("parcela_id")
            if not titulo or not parcela:
                return {
                    "text": "⚠️ Informe o ID do título e da parcela. Exemplo: enviar boleto 123 1",
                    "buttons": menu_inicial
                }

            msg_envio = enviar_boleto_email(titulo, parcela)
            return {
                "text": msg_envio,
                "buttons": menu_inicial
            }

        if acao == "link_boleto":
            titulo = parametros.get("titulo_id")
            parcela = parametros.get("parcela_id")
            if not titulo or not parcela:
                return {
                    "text": "⚠️ Informe o ID do título e da parcela. Exemplo: link boleto 123 1",
                    "buttons": menu_inicial
                }

            msg_link = gerar_link_boleto(titulo, parcela)

            # Se for um link válido, formata para markdown
            if msg_link.startswith("http"):
                msg_formatado = f"🔗 **Segunda via disponível:** [Clique aqui para abrir o boleto]({msg_link})"
            else:
                msg_formatado = msg_link

            return {
                "text": msg_formatado,
                "buttons": menu_inicial
            }

        return {"text": f"Ação {acao} reconhecida, mas não implementada.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception("Erro geral:")
        return {"text": f"❌ Ocorreu um erro ao processar sua solicitação: {e}", "buttons": menu_inicial}


# ===== Health check =====
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
