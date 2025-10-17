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

# Permitir CORS
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

# === Formatar itens do pedido para tabela ===
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

# === Função IA para entender intenção ===
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

Se algum parâmetro estiver faltando, pergunte ao usuário para confirmar.
Se não entender, devolva {{ "acao": null }}.

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
        try:
            return json.loads(conteudo)
        except Exception:
            return {"acao": None, "erro": "Resposta IA inválida", "detalhes": conteudo}
    except Exception as e:
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

# === Endpoint principal de mensagens ===
@app.post("/mensagem")
async def message_endpoint(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    intencao = entender_intencao(msg.text)
    logging.info("🧠 Interpretação IA:", intencao)

    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {})

    # Botões iniciais
    menu_inicial = [
        {"label": "Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "Emitir PDF", "action": "relatorio_pdf"},
        {"label": "Ver Itens do Pedido", "action": "itens_pedido"}
    ]

    if not acao:
        return {"text": "Escolha uma opção:", "buttons": menu_inicial}

    try:
        # ======================
        # Listar pedidos pendentes
        # ======================
        if acao == "listar_pedidos_pendentes":
            data_inicio = parametros.get("data_inicio")
            data_fim = parametros.get("data_fim")
            pedidos = listar_pedidos_pendentes(data_inicio, data_fim)
            if not pedidos:
                return {"text": "Nenhum pedido pendente encontrado.", "buttons": menu_inicial}
            rows = [{"label": f"ID {p['id']} | {p['status']} | {p['date']}", "action": "itens_pedido", "pedido_id": p['id']} for p in pedidos]
            return {"text": "Pedidos pendentes de autorização:", "buttons": rows}

        # ======================
        # Visualizar itens do pedido
        # ======================
        elif acao == "itens_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try: pid = int(pid)
            except: return {"text": "ID do pedido inválido.", "buttons": menu_inicial}
            itens = itens_pedido(pid)
            tabela = formatar_itens_tabela(itens)
            botoes = [
                {"label": "Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
                {"label": "Voltar ao Menu", "action": "menu_inicial"}
            ]
            return {"text": f"Itens do pedido {pid}:", "table": tabela, "buttons": botoes}

        # ======================
        # Autorizar pedido
        # ======================
        elif acao == "autorizar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            obs = parametros.get("observacao")
            try: pid = int(pid)
            except: return {"text": "ID do pedido inválido.", "buttons": menu_inicial}
            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"text": f"Pedido {pid} não encontrado.", "buttons": menu_inicial}
            if pedido.get("status") != "PENDING":
                return {"text": f"❌ Não é possível autorizar o pedido {pid}. Status atual: {pedido.get('status')}", "buttons": menu_inicial}
            sucesso = autorizar_pedido(pid, obs)
            if sucesso:
                return {"text": f"✅ Pedido {pid} autorizado com sucesso!", "buttons": menu_inicial}
            avisos = obter_aviso_pedido(pid)
            msg_avisos = f"\nAvisos do pedido:\n{avisos}" if avisos else ""
            return {"text": f"❌ Falha ao autorizar o pedido {pid}.{msg_avisos}", "buttons": menu_inicial}

        # ======================
        # Reprovar pedido
        # ======================
        elif acao == "reprovar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            obs = parametros.get("observacao")
            try: pid = int(pid)
            except: return {"text": "ID do pedido inválido.", "buttons": menu_inicial}
            sucesso = reprovar_pedido(pid, obs)
            if sucesso:
                return {"text": f"🚫 Pedido {pid} reprovado com sucesso!", "buttons": menu_inicial}
            avisos = obter_aviso_pedido(pid)
            msg_avisos = f"\nAvisos do pedido:\n{avisos}" if avisos else ""
            return {"text": f"❌ Falha ao reprovar o pedido {pid}.{msg_avisos}", "buttons": menu_inicial}

        # ======================
        # Gerar PDF do pedido
        # ======================
        elif acao == "relatorio_pdf":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try: pid = int(pid)
            except: return {"text": "ID do pedido inválido para gerar PDF.", "buttons": menu_inicial}
            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if pdf_bytes:
                pdf_base64 = base64.b64encode(pdf_bytes).decode()
                return {
                    "text": f"PDF do pedido {pid} gerado com sucesso!",
                    "pdf_base64": pdf_base64,
                    "filename": f"pedido_{pid}.pdf",
                    "buttons": menu_inicial
                }
            return {"text": "❌ Erro ao gerar PDF.", "buttons": menu_inicial}

        else:
            return {"text": f"Ação {acao} reconhecida, mas não implementada.", "buttons": menu_inicial}

    except Exception as e:
        logging.error("Erro ao executar ação:", exc_info=e)
        return {"text": f"Erro ao executar ação {acao}: {e}", "buttons": menu_inicial}
