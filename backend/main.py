from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import logging
import base64
import openai
import random

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes,
    buscar_pedido_por_id
)

# === CONFIGURAÇÕES ===
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

# === Memória de contexto (último pedido do usuário) ===
contexto_usuarios = {}

# === Função auxiliar para formatar tabela ===
def formatar_itens_tabela(itens):
    if not itens:
        return None
    headers = ["Nº", "Código", "Descrição", "Qtd", "Unid", "Valor Unit", "Total"]
    rows, total_geral = [], 0
    for i, item in enumerate(itens, 1):
        codigo = item.get("resourceCode") or "-"
        desc = (
            item.get("resourceDescription")
            or item.get("itemDescription")
            or item.get("description", "Sem descrição")
        )
        qtd = item.get("quantity", 0)
        unid = item.get("unit") or "-"
        valor_unit = item.get("unitPrice") or 0.0
        total = qtd * valor_unit
        total_geral += total
        rows.append([i, codigo, desc, qtd, unid, round(valor_unit, 2), round(total, 2)])
    return {"headers": headers, "rows": rows, "total": round(total_geral, 2)}

# === IA: interpretação da intenção ===
def entender_intencao(texto: str):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        return {"acao": None, "erro": "Chave OpenAI não configurada."}

    prompt = f"""
Você é a assistente *constru.ia*, especializada no sistema Sienge.
Analise a mensagem do usuário e retorne SOMENTE em JSON válido, sem texto extra.

Formato:
{{
  "acao": "<ação>",
  "parametros": {{}}
}}

Ações possíveis:
- listar_pedidos_pendentes
- itens_pedido (pedido_id)
- autorizar_pedido (pedido_id)
- reprovar_pedido (pedido_id)
- relatorio_pdf (pedido_id)

Exemplos:
"pedidos pendentes" -> {{"acao": "listar_pedidos_pendentes"}}
"itens do pedido 298" -> {{"acao": "itens_pedido", "parametros": {{"pedido_id": 298}}}}
"autoriza o pedido 298" -> {{"acao": "autorizar_pedido", "parametros": {{"pedido_id": 298}}}}
"gera o pdf do 290" -> {{"acao": "relatorio_pdf", "parametros": {{"pedido_id": 290}}}}

Mensagem: "{texto}"
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        conteudo = response.choices[0].message.content.strip()
        conteudo = conteudo.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(conteudo)
            logging.info(f"🧠 Interpretação IA -> {parsed}")
            return parsed
        except Exception:
            logging.warning(f"⚠️ Resposta IA não JSON: {conteudo}")
            if "pendente" in texto:
                return {"acao": "listar_pedidos_pendentes"}
            if "item" in texto:
                return {"acao": "itens_pedido"}
            return {"acao": None}
    except Exception as e:
        logging.error(f"Erro IA: {e}")
        return {"acao": None, "erro": str(e)}

# === Função auxiliar para avisos ===
def obter_aviso_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)
    avisos = pedido.get("alerts", []) if pedido else []
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

    # Mensagem de boas-vindas se não entender a ação
    if not acao:
        saudacao = (
            f"Olá {msg.user.split('@')[0].title()}! 😊\n"
            "Sou a *constru.ia*, sua assistente especializada no Sienge.\n"
            "Posso te ajudar a consultar pedidos pendentes, autorizar, reprovar ou emitir PDFs.\n"
            "Por onde gostaria de começar?"
        )
        return {"text": saudacao, "buttons": menu_inicial}

    try:
        # === LISTAR PEDIDOS PENDENTES ===
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente de autorização encontrado.", "buttons": menu_inicial}

            botoes = [
                {"label": f"Pedido {p['id']} - {p.get('status', 'PENDENTE')}", "action": "itens_pedido", "pedido_id": p["id"]}
                for p in pedidos
            ]
            return {"text": "📋 Estes são os pedidos pendentes de autorização:", "buttons": botoes}

        # === ITENS DO PEDIDO ===
        elif acao == "itens_pedido":
            pid = parametros.get("pedido_id") or contexto_usuarios.get(msg.user, {}).get("ultimo_pedido")
            if not pid:
                return {"text": "Por favor, informe o número do pedido.", "buttons": menu_inicial}

            pid = int(pid)
            itens = itens_pedido(pid)
            if not itens:
                return {"text": f"❌ Nenhum item encontrado no pedido {pid}."}

            tabela = formatar_itens_tabela(itens)
            contexto_usuarios[msg.user] = {"ultimo_pedido": pid}

            botoes = [
                {"label": "✅ Autorizar Pedido", "action": "autorizar_pedido", "pedido_id": pid},
                {"label": "🚫 Reprovar Pedido", "action": "reprovar_pedido", "pedido_id": pid},
                {"label": "⬅️ Voltar ao Menu", "action": "menu_inicial"}
            ]
            return {"text": f"📦 Itens do pedido {pid}:", "table": tabela, "buttons": botoes}

        # === AUTORIZAR PEDIDO ===
        elif acao == "autorizar_pedido":
            pid = parametros.get("pedido_id") or contexto_usuarios.get(msg.user, {}).get("ultimo_pedido")
            if not pid:
                return {"text": "Qual pedido você deseja autorizar?"}
            pid = int(pid)

            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"text": f"Pedido {pid} não encontrado."}
            if pedido.get("status") != "PENDING":
                return {"text": f"❌ O pedido {pid} não está pendente. Status atual: {pedido.get('status')}"}

            sucesso = autorizar_pedido(pid)
            if sucesso:
                frases = [
                    "✅ Pedido autorizado com sucesso!",
                    "Tudo certo, o pedido foi liberado 👌",
                    "Perfeito! Pedido autorizado ✅"
                ]
                return {"text": random.choice(frases)}
            return {"text": f"❌ Não foi possível autorizar o pedido {pid}."}

        # === REPROVAR PEDIDO ===
        elif acao == "reprovar_pedido":
            pid = parametros.get("pedido_id") or contexto_usuarios.get(msg.user, {}).get("ultimo_pedido")
            if not pid:
                return {"text": "Qual pedido você deseja reprovar?"}
            pid = int(pid)

            sucesso = reprovar_pedido(pid)
            if sucesso:
                return {"text": f"🚫 Pedido {pid} reprovado com sucesso."}
            return {"text": f"❌ Não foi possível reprovar o pedido {pid}."}

        # === GERAR PDF ===
        elif acao == "relatorio_pdf":
            pid = parametros.get("pedido_id") or contexto_usuarios.get(msg.user, {}).get("ultimo_pedido")
            if not pid:
                return {"text": "Informe o número do pedido para gerar o PDF."}
            pid = int(pid)

            pdf_bytes = gerar_relatorio_pdf_bytes(pid)
            if pdf_bytes:
                pdf_base64 = base64.b64encode(pdf_bytes).decode()
                return {
                    "text": f"📄 PDF do pedido {pid} gerado com sucesso!",
                    "pdf_base64": pdf_base64,
                    "filename": f"pedido_{pid}.pdf"
                }
            return {"text": f"❌ Erro ao gerar PDF do pedido {pid}."}

        else:
            return {"text": f"Ação '{acao}' reconhecida, mas ainda não implementada.", "buttons": menu_inicial}

    except Exception as e:
        logging.exception(f"Erro ao processar ação {acao}: {e}")
        return {"text": f"⚠️ Ocorreu um erro interno: {str(e)}", "buttons": menu_inicial}
