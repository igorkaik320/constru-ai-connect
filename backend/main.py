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
    buscar_pedido_por_id
)

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# === Permitir CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Modelo de mensagem ===
class Message(BaseModel):
    user: str
    text: str

# === Memória de contexto por usuário ===
contexto_usuarios = {}

# === Função auxiliar para formatar tabela ===
def formatar_itens_tabela(itens):
    if not itens:
        return None
    headers = ["Nº", "Código", "Descrição", "Qtd", "Unid", "Valor Unit", "Total"]
    rows = []
    total_geral = 0
    for i, item in enumerate(itens, 1):
        codigo = item.get("resourceCode") or "-"
        desc = item.get("resourceDescription") or item.get("itemDescription") or item.get("description", "Sem descrição")
        qtd = item.get("quantity", 0)
        unid = item.get("unit") or "-"
        valor_unit = item.get("unitPrice") or item.get("totalAmount", 0.0)
        total = qtd * valor_unit
        total_geral += total
        rows.append([i, codigo, desc, qtd, unid, round(valor_unit, 2), round(total, 2)])
    return {"headers": headers, "rows": rows, "total": round(total_geral, 2)}

# === Interpretação da intenção via OpenAI ===
def entender_intencao(texto: str):
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        return {"acao": None, "erro": "Chave OpenAI não configurada."}

    prompt = f"""
Você é uma IA especialista no sistema Sienge.
Dada a mensagem de um usuário, identifique a intenção e retorne em JSON.

Possíveis ações:
- listar_pedidos_pendentes (data_inicio?, data_fim?)
- itens_pedido (pedido_id)
- autorizar_pedido (pedido_id, observacao?)
- reprovar_pedido (pedido_id, observacao?)
- relatorio_pdf (pedido_id)

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

# === Função para obter avisos do pedido ===
def obter_aviso_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)
    if not pedido:
        return None
    avisos = pedido.get("alerts", [])
    if not avisos:
        return None
    return "\n".join([f"- {a.get('message')}" for a in avisos])

# === ENDPOINT PRINCIPAL ===
@app.post("/mensagem")
async def message_endpoint(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    intencao = entender_intencao(msg.text)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {})

    menu_inicial = [
        {"label": "Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "Emitir PDF", "action": "relatorio_pdf"},
        {"label": "Ver Itens do Pedido", "action": "itens_pedido"}
    ]

    if not acao:
        return {"text": "Escolha uma opção:", "buttons": menu_inicial}

    try:
        # === LISTAR PEDIDOS PENDENTES ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "Nenhum pedido pendente encontrado.", "buttons": menu_inicial}

            botoes = [
                {"label": f"Pedido {p['id']} - {p.get('status', 'PENDENTE')}", "action": "itens_pedido", "pedido_id": p["id"]}
                for p in pedidos
            ]
            return {"text": "📋 Pedidos pendentes de autorização:", "buttons": botoes, "type": "pedidos"}

        # === ITENS DO PEDIDO ===
        elif acao == "itens_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")

            if not pid and msg.user in contexto_usuarios:
                pid = contexto_usuarios[msg.user].get("ultimo_pedido")

            if not pid:
                return {"text": "Informe o número do pedido para visualizar os itens.", "buttons": menu_inicial}

            pid = int(pid)
            itens = itens_pedido(pid)
            if not itens:
                return {"text": f"❌ Nenhum item encontrado no pedido {pid}."}

            tabela = formatar_itens_tabela(itens)
            contexto_usuarios[msg.user] = {"ultimo_pedido": pid}

            botoes = [
                {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
                {"label": "Voltar ao Menu", "action": "menu_inicial"}
            ]
            return {"text": f"📦 Itens do pedido {pid}:", "table": tabela, "buttons": botoes, "type": "itens"}

        # === AUTORIZAR PEDIDO ===
        elif acao == "autorizar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            if not pid and msg.user in contexto_usuarios:
                pid = contexto_usuarios[msg.user].get("ultimo_pedido")

            if not pid:
                return {"text": "Qual pedido deseja autorizar?", "buttons": menu_inicial}

            pid = int(pid)
            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"text": f"Pedido {pid} não encontrado.", "buttons": menu_inicial}

            if pedido.get("status") != "PENDING":
                return {"text": f"❌ Não é possível autorizar o pedido {pid}. Status atual: {pedido.get('status')}", "buttons": menu_inicial}

            sucesso = autorizar_pedido(pid)
            if sucesso:
                return {"text": f"✅ Pedido {pid} autorizado com sucesso!", "buttons": menu_inicial}
            return {"text": f"❌ Falha ao autorizar o pedido {pid}.", "buttons": menu_inicial}

        # === REPROVAR PEDIDO ===
        elif acao == "reprovar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            if not pid and msg.user in contexto_usuarios:
                pid = contexto_usuarios[msg.user].get("ultimo_pedido")

            if not pid:
                return {"text": "Qual pedido deseja reprovar?", "buttons": menu_inicial}

            pid = int(pid)
            sucesso = reprovar_pedido(pid)
            if sucesso:
                return {"text": f"🚫 Pedido {pid} reprovado com sucesso!", "buttons": menu_inicial}
            return {"text": f"❌ Falha ao reprovar o pedido {pid}.", "buttons": menu_inicial}

        # === GERAR PDF ===
        elif acao == "relatorio_pdf":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            if not pid and msg.user in contexto_usuarios:
                pid = contexto_usuarios[msg.user].get("ultimo_pedido")

            if not pid:
                return {"text": "Qual pedido deseja gerar o PDF?", "buttons": menu_inicial}

            pid = int(pid)
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if pdf_bytes:
                pdf_base64 = base64.b64encode(pdf_bytes).decode()
                return {"text": f"PDF do pedido {pid} gerado com sucesso!", "pdf_base64": pdf_base64, "filename": f"pedido_{pid}.pdf"}
            return {"text": f"❌ Erro ao gerar PDF do pedido {pid}."}

        else:
            return {"text": f"Ação '{acao}' reconhecida, mas não implementada.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception(f"Erro geral ao processar ação {acao}: {e}")
        return {"text": f"⚠️ Erro ao executar ação {acao}: {str(e)}", "buttons": menu_inicial}
