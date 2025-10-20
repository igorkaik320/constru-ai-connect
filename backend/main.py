from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import base64
import re

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
from sienge.sienge_boletos import (
    buscar_boletos_por_cpf,
    gerar_link_boleto,
)

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


# ===== Utils =====
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


# ===== NLU =====
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    # PEDIDOS
    if any(k in t for k in ["pedidos pendentes", "listar pendentes", "listar_pedidos_pendentes"]):
        return {"acao": "listar_pedidos_pendentes", "parametros": {}}

    if "autorizar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "reprovar pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "itens do pedido" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "itens_pedido", "parametros": {"pedido_id": int(pid)}} if pid else {}

    if "pdf" in t or "relatório" in t:
        pid = next((p for p in t.split() if p.isdigit()), None)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid)}} if pid else {}

    # BOLETOS (CPF ou 2ª via)
    if "segunda via cpf" in t or "boleto cpf" in t:
        return {"acao": "buscar_boletos_cpf", "parametros": {"texto": t}}

    if "gerar boleto" in t or "2ª via" in t or "segunda via" in t:
        nums = [int(n) for n in re.findall(r"\d+", t)]
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": nums[0], "parcela_id": nums[1]}}

    return {"acao": None}


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
        {"label": "Gerar PDF", "action": "relatorio_pdf"},
        {"label": "Consultar Boletos por CPF", "action": "buscar_boletos_cpf"},
    ]

    try:
        # === PEDIDOS ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu_inicial}

            linhas = [f"• Pedido {p['id']} — {money(p.get('totalAmount'))}" for p in pedidos]
            return {"text": "📋 Pedidos pendentes:\n\n" + "\n".join(linhas), "buttons": menu_inicial}

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

            resumo = (
                f"🧾 Pedido {pid}\n"
                f"🏗️ Obra: {(obra or {}).get('description', '-')}\n"
                f"💰 Centro de Custo: {(cc or {}).get('description', '-')}\n"
                f"🤝 Fornecedor: {(forn or {}).get('name', '-')}\n"
                f"💵 Total: {money(pedido.get('totalAmount'))}\n"
            )
            return {"text": resumo, "buttons": menu_inicial}

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
        if acao == "buscar_boletos_cpf":
            texto = parametros.get("texto", "")
            cpf_match = re.search(r'\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}', texto)
            if not cpf_match:
                return {"text": "🧾 Informe um CPF válido (ex: 123.456.789-00)."}

            cpf = re.sub(r'\D', '', cpf_match.group(0))
            resultado = buscar_boletos_por_cpf(cpf)
            if "erro" in resultado:
                return {"text": resultado["erro"]}

            nome = resultado["nome"]
            boletos = resultado["boletos"]

            linhas = []
            botoes = []
            for b in boletos:
                linhas.append(f"💳 **Título {b['titulo_id']}** — {money(b['valor'])} — Venc.: {b['vencimento']}")
                botoes.append({
                    "label": f"2ª via {b['titulo_id']}/{b['parcela_id']}",
                    "action": "link_boleto",
                    "titulo_id": b["titulo_id"],
                    "parcela_id": b["parcela_id"]
                })

            return {"text": f"📋 Boletos em aberto para **{nome}:**\n\n" + "\n".join(linhas), "buttons": botoes}

        if acao == "link_boleto":
            titulo = parametros.get("titulo_id")
            parcela = parametros.get("parcela_id")
            if not titulo or not parcela:
                return {"text": "⚠️ Informe o título e parcela (ex: 2ª via 267 1)", "buttons": menu_inicial}

            msg_link = gerar_link_boleto(titulo, parcela)
            return {"text": msg_link, "buttons": menu_inicial}

        return {"text": "🤖 Não entendi o comando.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception("Erro geral:")
        return {"text": f"❌ Ocorreu um erro: {e}", "buttons": menu_inicial}


# ===== Health check =====
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
