from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from datetime import datetime

# Importando funções do módulo Sienge
from sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido
)

app = FastAPI()

# Permitir acesso do frontend
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

# Função para processar comandos do Sienge
def processar_comando_sienge(texto: str):
    texto = texto.lower().strip()

    try:
        # ===== Pedidos pendentes =====
        if texto.startswith("pedidos pendentes"):
            partes = texto.split("de")
            data_inicio, data_fim = None, None
            if len(partes) > 1:
                datas = partes[1].split("a")
                try:
                    data_inicio = datetime.strptime(datas[0].strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
                    data_fim = datetime.strptime(datas[1].strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception as e:
                    return f"❌ Formato de data inválido. Use dd/mm/yyyy. Detalhes: {e}"

            pedidos = listar_pedidos_pendentes(data_inicio, data_fim)
            if pedidos:
                return "\n".join([f"ID: {p['id']} | Status: {p['status']} | Data: {p['date']}" for p in pedidos])
            return "Nenhum pedido pendente encontrado."

        # ===== Itens do pedido =====
        elif texto.startswith("itens do pedido"):
            try:
                pid = int(texto.split()[-1])
            except:
                return "❌ ID do pedido inválido."

            itens = itens_pedido(pid)
            if itens:
                return "\n".join([
                    f"Item {i.get('itemNumber','?')}: {i.get('resourceDescription') or i.get('itemDescription') or i.get('description','Sem descrição')} | Quantidade: {i.get('quantity',0)} | Valor: {i.get('unitPrice') or i.get('totalAmount',0.0)}"
                    for i in itens
                ])
            return "Nenhum item encontrado."

        # ===== Autorizar pedido =====
        elif texto.startswith("autorizar o pedido"):
            parts = texto.split("com observação")
            try:
                pid = int(parts[0].split()[-1])
            except:
                return "❌ ID do pedido inválido."
            obs = parts[1].strip() if len(parts) > 1 else None
            autorizar_pedido(pid, obs)
            return f"✅ Pedido {pid} autorizado com sucesso!"

        # ===== Reprovar pedido =====
        elif texto.startswith("reprovar o pedido"):
            parts = texto.split("com observação")
            try:
                pid = int(parts[0].split()[-1])
            except:
                return "❌ ID do pedido inválido."
            obs = parts[1].strip() if len(parts) > 1 else None
            reprovar_pedido(pid, obs)
            return f"🚫 Pedido {pid} reprovado com sucesso!"

        else:
            return None  # Não é comando Sienge

    except Exception as e:
        return f"❌ Erro ao processar comando Sienge: {e}"

# Endpoint principal de mensagens
@app.post("/mensagem")
async def message_endpoint(msg: Message):
    print(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    # Tentar processar comando Sienge primeiro
    resposta_sienge = processar_comando_sienge(msg.text)
    if resposta_sienge:
        print(f"🤖 Resposta Sienge: {resposta_sienge}")
        return {"response": resposta_sienge}

    # Caso não seja comando Sienge, envia para OpenAI
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            return {"response": "Erro: chave da OpenAI não configurada."}

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente útil e direto."},
                {"role": "user", "content": msg.text},
            ],
            temperature=0.7,
            max_tokens=500
        )

        reply = response.choices[0].message.content
        print(f"🤖 Resposta da IA: {reply}")
        return {"response": reply}

    except Exception as e:
        print("❌ Erro ao chamar a OpenAI:", e)
        return {"response": "Erro ao se comunicar com a IA."}
