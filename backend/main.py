from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import logging
from base64 import b64encode
import requests

# Importar funções Sienge
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf,
    buscar_pedido_por_id
)

# === CONFIGURAÇÕES ===
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

# === Formatar itens do pedido para exibir no chat ===
def formatar_itens(itens):
    if not itens:
        return "Nenhum item encontrado."
    linhas = ["Itens do Pedido"]
    header = f"{'Nº':<4} | {'Descrição':<35} | {'Qtd':<6} | {'Valor':<10}"
    linhas.append(header)
    linhas.append("-" * len(header))
    total = 0
    for i, item in enumerate(itens, 1):
        desc = item.get("resourceDescription") or item.get("itemDescription") or item.get("description","Sem descrição")
        qtd = item.get("quantity",0)
        valor = item.get("unitPrice") or item.get("totalAmount",0.0)
        total += valor * qtd
        linhas.append(f"{i:<4} | {desc:<35} | {qtd:<6} | {valor:<10.2f}")
    linhas.append("-" * len(header))
    linhas.append(f"Total: {total:.2f}")
    return "\n".join(linhas)

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
            data = json.loads(conteudo)
            return data
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
    print(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    intencao = entender_intencao(msg.text)
    print("🧠 Interpretação IA:", intencao)

    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {})

    if not acao:
        return {"response": "Desculpe, não entendi o que você deseja fazer no Sienge."}

    try:
        if acao == "listar_pedidos_pendentes":
            data_inicio = parametros.get("data_inicio")
            data_fim = parametros.get("data_fim")
            pedidos = listar_pedidos_pendentes(data_inicio, data_fim)
            if not pedidos:
                return {"response": "Nenhum pedido pendente encontrado."}
            resposta = "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])
            return {"response": resposta}

        elif acao == "itens_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Não consegui identificar o ID do pedido. Pode informar novamente?"}
            itens = itens_pedido(pid)
            resposta = formatar_itens(itens)
            return {"response": resposta}

        elif acao == "autorizar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            obs = parametros.get("observacao")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Qual é o ID do pedido que você quer autorizar?"}

            # Verifica status do pedido
            pedido = buscar_pedido_por_id(pid)
            if not pedido:
                return {"response": f"Pedido {pid} não encontrado."}
            status_atual = pedido.get("status")
            if status_atual != "PENDING":
                return {"response": f"❌ Não é possível autorizar o pedido {pid}. Status atual: {status_atual}"}

            # Tenta autorizar
            sucesso = autorizar_pedido(pid, obs)
            if sucesso:
                return {"response": f"✅ Pedido {pid} autorizado com sucesso!"}
            else:
                avisos = obter_aviso_pedido(pid)
                msg_avisos = f"\nAvisos do pedido:\n{avisos}" if avisos else ""
                return {"response": f"❌ Falha ao autorizar o pedido {pid}.{msg_avisos}"}

        elif acao == "reprovar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            obs = parametros.get("observacao")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Qual é o ID do pedido que você quer reprovar?"}
            sucesso = reprovar_pedido(pid, obs)
            if sucesso:
                return {"response": f"🚫 Pedido {pid} reprovado com sucesso!"}
            else:
                avisos = obter_aviso_pedido(pid)
                msg_avisos = f"\nAvisos do pedido:\n{avisos}" if avisos else ""
                return {"response": f"❌ Falha ao reprovar o pedido {pid}.{msg_avisos}"}

        elif acao == "relatorio_pdf":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Não consegui identificar o ID do pedido para gerar PDF."}
            caminho = gerar_relatorio_pdf(pid)
            if caminho:
                return {"response": f"PDF do pedido {pid} gerado: {caminho}"}
            return {"response": "❌ Erro ao gerar PDF."}

        else:
            return {"response": f"Ação {acao} reconhecida, mas ainda não implementada."}

    except Exception as e:
        print("❌ Erro ao executar ação:", e)
        return {"response": f"Erro ao executar ação {acao}: {e}"}
