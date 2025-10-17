from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from datetime import datetime
import json

# === Importa funções Sienge ===
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pedido
)

# === Configuração base ===
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
    - relatorio_pedido (pedido_id)

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

# === Processamento direto dos comandos ===
def processar_comando_sienge(texto: str):
    texto = texto.lower().strip()
    try:
        if texto.startswith("pedidos pendentes"):
            pedidos = listar_pedidos_pendentes()
            if pedidos:
                return "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])
            return "Nenhum pedido pendente encontrado."

        elif texto.startswith("itens do pedido"):
            try:
                pid = int(texto.split()[-1])
            except:
                return "❌ ID do pedido inválido."
            itens = itens_pedido(pid)
            if itens:
                resposta = "\n".join([
                    f"{i.get('itemNumber','?')} | {i.get('resourceDescription') or i.get('itemDescription') or i.get('description','Sem descrição')} | Qtd: {i.get('quantity',0)} | Valor: {i.get('unitPrice') or i.get('totalAmount',0.0)}"
                    for i in itens
                ])
                total = sum(i.get('unitPrice') or i.get('totalAmount') or 0.0 for i in itens)
                resposta += f"\nTotal: {total:.2f}"
                return resposta
            return "Nenhum item encontrado."

        elif texto.startswith("autorizar o pedido"):
            try:
                pid = int(texto.split()[-1])
            except:
                return "❌ ID do pedido inválido."
            sucesso = autorizar_pedido(pid)
            return f"✅ Pedido {pid} autorizado!" if sucesso else f"❌ Falha ao autorizar pedido {pid}."

        elif texto.startswith("reprovar o pedido"):
            try:
                pid = int(texto.split()[-1])
            except:
                return "❌ ID do pedido inválido."
            sucesso = reprovar_pedido(pid)
            return f"🚫 Pedido {pid} reprovado!" if sucesso else f"❌ Falha ao reprovar pedido {pid}."

        return None
    except Exception as e:
        return f"❌ Erro ao processar comando Sienge: {e}"

# === Endpoint principal ===
@app.post("/mensagem")
async def message_endpoint(msg: Message):
    print(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    resposta_sienge = processar_comando_sienge(msg.text)
    if resposta_sienge:
        return {"response": resposta_sienge}

    intencao = entender_intencao(msg.text)
    print("🧠 Interpretação IA:", intencao)

    acao = intencao.get("acao")
    parametros = intencao.get("parametros") or {}

    if not acao:
        return {"response": "Desculpe, não entendi o que você deseja fazer no Sienge."}

    try:
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            return {"response": "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])}

        elif acao == "itens_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            itens = itens_pedido(pid)
            if not itens:
                return {"response": "Nenhum item encontrado."}
            resposta = "\n".join([
                f"{i.get('itemNumber','?')} | {i.get('resourceDescription') or i.get('itemDescription') or i.get('description','Sem descrição')} | Qtd: {i.get('quantity',0)} | Valor: {i.get('unitPrice') or i.get('totalAmount',0.0)}"
                for i in itens
            ])
            total = sum(i.get('unitPrice') or i.get('totalAmount') or 0.0 for i in itens)
            resposta += f"\nTotal: {total:.2f}"
            return {"response": resposta}

        elif acao == "autorizar_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            obs = parametros.get("observacao")
            sucesso = autorizar_pedido(pid, obs)
            return {"response": f"✅ Pedido {pid} autorizado!" if sucesso else f"❌ Falha ao autorizar pedido {pid}."}

        elif acao == "reprovar_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            obs = parametros.get("observacao")
            sucesso = reprovar_pedido(pid, obs)
            return {"response": f"🚫 Pedido {pid} reprovado!" if sucesso else f"❌ Falha ao reprovar pedido {pid}."}

        elif acao == "relatorio_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            caminho_pdf = gerar_relatorio_pedido(pid)
            if caminho_pdf:
                return {"response": f"✅ Relatório do pedido {pid} gerado com sucesso.", "pdf": caminho_pdf}
            else:
                return {"response": f"❌ Não foi possível gerar o relatório do pedido {pid}."}

        else:
            return {"response": "Desculpe, ainda não sei executar essa ação no Sienge."}

    except Exception as e:
        print("❌ Erro ao executar ação:", e)
        return {"response": f"Erro ao executar ação {acao}: {e}"}
