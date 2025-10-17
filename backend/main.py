from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import json

from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf
)

app = FastAPI()

# Permite que o frontend acesse
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

# === Função IA para identificar intenção ===
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

# === Processamento de comandos Sienge diretos ===
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

        elif "autorizar" in texto or "autoriza" in texto:
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido."
            autorizar_pedido(int(pid))
            return f"✅ Pedido {pid} autorizado com sucesso!"

        elif "reprovar" in texto or "reprova" in texto:
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido."
            reprovar_pedido(int(pid))
            return f"🚫 Pedido {pid} reprovado com sucesso!"

        elif "relatorio" in texto or "pdf" in texto:
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido para gerar PDF."
            caminho = gerar_relatorio_pdf(int(pid))
            if caminho:
                return f"PDF do pedido {pid} gerado com sucesso: {caminho}"
            return "❌ Erro ao gerar relatório PDF."

        else:
            return "Desculpe, não entendi o que você deseja fazer no Sienge."

    except Exception as e:
        return f"❌ Erro ao processar comando: {e}"

# === Endpoint principal do chat ===
@app.post("/mensagem")
def receber_mensagem(msg: Message):
    # Tenta interpretar via IA
    intencao = entender_intencao(msg.text)

    if intencao.get("acao") == "itens_pedido":
        pedido_id = int(intencao.get("pedido_id", 0))
        if pedido_id:
            itens = itens_pedido(pedido_id)
            if itens:
                resposta = "Itens do Pedido Nº | Descrição | Qtd | Valor\n"
                total = 0
                for i in itens:
                    desc = i.get("resourceDescription") or i.get("itemDescription") or i.get("description") or "Sem descrição"
                    qtd = i.get("quantity", 0)
                    val = i.get("unitPrice") or i.get("totalAmount") or 0.0
                    total += qtd * val
                    resposta += f"{i.get('itemNumber','?')} | {desc} | {qtd} | {val:.2f}\n"
                resposta += f"Total: {total:.2f}"
                return {"resposta": resposta}
            return {"resposta": "Nenhum item encontrado."}
        return {"resposta": "❌ Não consegui identificar o ID do pedido."}

    elif intencao.get("acao") == "autorizar_pedido":
        pedido_id = int(intencao.get("pedido_id", 0))
        if pedido_id:
            autorizar_pedido(pedido_id)
            return {"resposta": f"✅ Pedido {pedido_id} autorizado com sucesso!"}
        return {"resposta": "❌ Não consegui identificar o ID do pedido."}

    elif intencao.get("acao") == "reprovar_pedido":
        pedido_id = int(intencao.get("pedido_id", 0))
        if pedido_id:
            reprovar_pedido(pedido_id)
            return {"resposta": f"🚫 Pedido {pedido_id} reprovado com sucesso!"}
        return {"resposta": "❌ Não consegui identificar o ID do pedido."}

    elif intencao.get("acao") == "relatorio_pdf":
        pedido_id = int(intencao.get("pedido_id", 0))
        if pedido_id:
            caminho = gerar_relatorio_pdf(pedido_id)
            if caminho:
                return {"resposta": f"PDF do pedido {pedido_id} gerado: {caminho}"}
            return {"resposta": "❌ Erro ao gerar PDF."}
        return {"resposta": "❌ Não consegui identificar o ID do pedido."}

    # fallback para comandos diretos
    resposta_direta = processar_comando_sienge(msg.text)
    return {"resposta": resposta_direta}
