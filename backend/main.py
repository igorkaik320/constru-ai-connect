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


# ===== NLU bem simples (mantém seu fluxo) =====
def entender_intencao(texto: str):
    """
    Para não depender 100% do LLM em frases simples, tratamos gatilhos básicos aqui
    e, se não bater, caímos no LLM (quando OPENAI_API_KEY estiver setada).
    """
    t = (texto or "").strip().lower()

    if any(k in t for k in ["pedidos pendentes", "listar pendentes", "listar_pedidos_pendentes"]):
        return {"acao": "listar_pedidos_pendentes", "parametros": {}}

    if t.startswith("itens do pedido"):
        # "itens do pedido 278"
        partes = t.split()
        pid = next((p for p in partes if p.isdigit()), None)
        if pid:
            return {"acao": "itens_pedido", "parametros": {"pedido_id": int(pid)}}
        return {"acao": "itens_pedido", "parametros": {}}

    if t.startswith("itens_pedido"):
        # "itens_pedido 278"
        partes = t.split()
        if len(partes) > 1 and partes[1].isdigit():
            return {"acao": "itens_pedido", "parametros": {"pedido_id": int(partes[1])}}
        return {"acao": "itens_pedido", "parametros": {}}

    if t.startswith("autorizar_pedido"):
        partes = t.split()
        if len(partes) > 1 and partes[1].isdigit():
            return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(partes[1])}}
        return {"acao": "autorizar_pedido", "parametros": {}}

    if t.startswith("reprovar_pedido"):
        partes = t.split()
        if len(partes) > 1 and partes[1].isdigit():
            return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(partes[1])}}
        return {"acao": "reprovar_pedido", "parametros": {}}

    if "pdf" in t or "relatório" in t or t.startswith("relatorio_pdf"):
        # "emitir pdf 278" / "relatorio_pdf 278"
        partes = t.split()
        pid = next((p for p in partes if p.isdigit()), None)
        if pid:
            return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(pid)}}
        return {"acao": "relatorio_pdf", "parametros": {}}

    # fallback: LLM (opcional)
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            return {"acao": None}

        prompt = f"""
Você é uma IA especialista no Sienge.
Interprete a intenção do usuário e retorne JSON.
Ações:
- listar_pedidos_pendentes (data_inicio?, data_fim?)
- itens_pedido (pedido_id)
- autorizar_pedido (pedido_id, observacao?)
- reprovar_pedido (pedido_id, observacao?)
- relatorio_pdf (pedido_id)
Mensagem: "{texto}"
Responda apenas o JSON.
"""
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        conteudo = resp.choices[0].message.content.strip()
        conteudo = conteudo.replace("```json", "").replace("```", "")
        return json.loads(conteudo)
    except Exception:
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
    ]

    # Sem ação -> menu
    if not acao:
        return {"text": "Escolha uma opção:", "buttons": menu_inicial}

    try:
        # LISTAR PENDENTES
        if acao == "listar_pedidos_pendentes":
            data_inicio = parametros.get("data_inicio")
            data_fim = parametros.get("data_fim")
            pedidos = listar_pedidos_pendentes(data_inicio, data_fim)
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

        # ITENS DO PEDIDO + RESUMO
        if acao == "itens_pedido":
            pid = parametros.get("pedido_id")
            if not pid:
                return {"text": "Por favor, informe o número do pedido.", "buttons": menu_inicial}
            try:
                pid = int(pid)
            except Exception:
                return {"text": "ID do pedido inválido.", "buttons": menu_inicial}

            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"text": f"❌ Pedido {pid} não encontrado.", "buttons": menu_inicial}

            # enriquecer
            obra_nome = None
            centro_custo_nome = None
            fornecedor_nome = None
            fornecedor_cnpj = None

            obra = buscar_obra(pedido.get("buildingId"))
            if obra:
                obra_nome = obra.get("description") or obra.get("name")

            cc = buscar_centro_custo(pedido.get("costCenterId"))
            if cc:
                centro_custo_nome = cc.get("description")

            forn = buscar_fornecedor(pedido.get("supplierId"))
            if forn:
                fornecedor_nome = forn.get("name")
                fornecedor_cnpj = forn.get("cnpj") or forn.get("cpf")

            itens = itens_pedido(pid)

            # texto resumo
            resumo = (
                f"🧾 Resumo do Pedido {pid}: "
                f"🗓️ Data: {pedido.get('date') or '-'} "
                f"🏗️ Obra: {obra_nome or 'Não informado'} "
                f"💰 Centro de Custo: {centro_custo_nome or 'Não informado'} "
                f"🤝 Fornecedor: {fornecedor_nome or 'Não informado'} (CNPJ {fornecedor_cnpj or '-'}) "
                f"💳 Condição de Pagamento: {pedido.get('paymentCondition') or '-'} "
                f"📝 Observações: {(pedido.get('notes') or 'Sem observações').strip()} "
                f"💵 Valor Total: {money(pedido.get('totalAmount'))}"
            )

            # itens em uma linha “bonita”
            if itens:
                itens_txt = []
                for it in itens:
                    desc = it.get("resourceDescription") or it.get("resourceReference") or "-"
                    qtd = it.get("quantity") or 0
                    un = it.get("unitOfMeasure") or "-"
                    unit = money(it.get("unitPrice") or 0)
                    itens_txt.append(f"🔹 {desc} ({qtd} {un}) — {unit}")
                resumo += "\n\n📦 Itens:\n" + "\n".join(itens_txt)

            botoes = [
                {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
                {"label": "Voltar ao Menu", "action": "menu_inicial"},
            ]
            return {"text": resumo, "buttons": botoes}

        # AUTORIZAR
        if acao == "autorizar_pedido":
            pid = parametros.get("pedido_id")
            obs = parametros.get("observacao")
            if not pid:
                return {"text": "Informe o número do pedido.", "buttons": menu_inicial}
            try:
                pid = int(pid)
            except Exception:
                return {"text": "ID do pedido inválido.", "buttons": menu_inicial}

            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"text": f"Pedido {pid} não encontrado.", "buttons": menu_inicial}
            if pedido.get("status") != "PENDING" or pedido.get("authorized") is True:
                return {"text": f"❌ Não é possível autorizar o pedido {pid}.", "buttons": menu_inicial}

            ok = autorizar_pedido(pid, obs)
            if ok:
                return {"text": "✅ Pedido autorizado!", "buttons": menu_inicial}
            avisos = obter_aviso_pedido(pid) or ""
            return {"text": f"❌ Falha ao autorizar. {avisos}", "buttons": menu_inicial}

        # REPROVAR
        if acao == "reprovar_pedido":
            pid = parametros.get("pedido_id")
            obs = parametros.get("observacao")
            if not pid:
                return {"text": "Informe o número do pedido.", "buttons": menu_inicial}
            try:
                pid = int(pid)
            except Exception:
                return {"text": "ID do pedido inválido.", "buttons": menu_inicial}

            ok = reprovar_pedido(pid, obs)
            if ok:
                return {"text": "🚫 Pedido reprovado!", "buttons": menu_inicial}
            avisos = obter_aviso_pedido(pid) or ""
            return {"text": f"❌ Falha ao reprovar. {avisos}", "buttons": menu_inicial}

        # GERAR PDF (OFICIAL SIENGE) EM BASE64
        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            if not pid:
                return {"text": "Informe o número do pedido para emitir o PDF.", "buttons": menu_inicial}
            try:
                pid = int(pid)
            except Exception:
                return {"text": "ID do pedido inválido para PDF.", "buttons": menu_inicial}

            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if not pdf_bytes:
                return {"text": f"❌ Não foi possível gerar o PDF do pedido {pid}.", "buttons": menu_inicial}

            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            return {
                "text": f"PDF do pedido {pid} gerado com sucesso!",
                "pdf_base64": pdf_b64,
                "filename": f"pedido_{pid}.pdf",
                "buttons": menu_inicial,
            }

        return {"text": f"Ação {acao} reconhecida, mas não implementada.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception("Erro geral:")
        return {"text": f"Ocorreu um erro ao processar sua solicitação: {e}", "buttons": menu_inicial}


# opcional: raiz para health check
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}
