from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from datetime import datetime
import json

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf
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

@app.get("/")
def root():
    return {"message": "🚀 Backend da Constru.IA ativado com sucesso!"}

# === Função IA para entender intenção natural ===
def entender_intencao(texto: str):
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
    - gerar_boleto (cliente?, titulo?, parcela?)
    - gerar_imposto_renda (cliente?)
    - saldo_devedor (cliente?)
    - relatorio_pdf (pedido_id)

    Se não entender, devolva {{ "acao": null }}

    Mensagem: "{texto}"
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        conteudo = response.choices[0].message.content
        try:
            data = json.loads(conteudo)
            return data
        except:
            return {"acao": None, "erro": "Resposta IA inválida", "detalhes": conteudo}
    except Exception as e:
        return {"acao": None, "erro": str(e)}

# === Processamento direto dos comandos existentes ===
def processar_comando_sienge(texto: str):
    texto = texto.lower().strip()
    try:
        if texto.startswith("pedidos pendentes"):
            pedidos = listar_pedidos_pendentes()
            if pedidos:
                return "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])
            return "Nenhum pedido pendente encontrado."

        elif "itens do pedido" in texto or "pedido" in texto:
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido."
            itens = itens_pedido(int(pid))
            if not itens:
                return "Nenhum item encontrado."
            resposta = "Itens do Pedido Nº | Descrição | Qtd | Valor\n"
            total = 0
            for i in itens:
                desc = i.get("resourceDescription") or i.get("itemDescription") or i.get("description") or "Sem descrição"
                qtd = i.get("quantity", 0)
                val = i.get("unitPrice") or i.get("totalAmount") or 0.0
                total += qtd * val
                resposta += f"{i.get('itemNumber','?')} | {desc} | {qtd} | {val:.2f}\n"
            resposta += f"Total: {total:.2f}"
            return resposta

        elif texto.startswith("autoriza"):
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui
