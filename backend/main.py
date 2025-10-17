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
            return json.loads(conteudo)
        except:
            return {"acao": None, "erro": "Resposta IA inválida", "detalhes": conteudo}
    except Exception as e:
        return {"acao": None, "erro": str(e)}

# === Processamento direto dos comandos existentes ===
def processar_comando_sienge(texto: str):
    texto = texto.lower().strip()
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

    elif "autorizar" in texto or texto.startswith("autoriza"):
        pid = ''.join(filter(str.isdigit, texto))
        if not pid:
            return "❌ Não consegui identificar o ID do pedido."
        sucesso = autorizar_pedido(int(pid))
        return f"✅ Pedido {pid} autorizado com sucesso!" if sucesso else f"❌ Falha ao autorizar pedido {pid}."

    elif "reprovar" in texto or texto.startswith("reprova"):
        pid = ''.join(filter(str.isdigit, texto))
        if not pid:
            return "❌ Não consegui identificar o ID do pedido."
        sucesso = reprovar_pedido(int(pid))
        return f"🚫 Pedido {pid} reprovado com sucesso!" if sucesso else f"❌ Falha ao reprovar pedido {pid}."

    elif "relatorio" in texto or "pdf" in texto:
        pid = ''.join(filter(str.isdigit, texto))
        if not pid:
            return "❌ Não consegui identificar o ID do pedido para gerar PDF."
        arquivo = gerar_relatorio_pdf(int(pid))
        return f"📄 PDF gerado: {arquivo}" if arquivo else "❌ Falha ao gerar PDF."

    return "Desculpe, não entendi o que você deseja fazer no Sienge."

# === Endpoint principal de mensagens ===
@app.post("/mensagem")
def mensagem(msg: Message):
    interpretacao = entender_intencao(msg.text)
    resposta = None

    # Tenta executar ação via IA
    acao = interpretacao.get("acao")
    if acao:
        if acao == "itens_pedido":
            pid = interpretacao.get("pedido_id")
            if pid:
                itens = itens_pedido(int(pid))
                if not itens:
                    resposta = "Nenhum item encontrado."
                else:
                    total = 0
                    resposta = "Itens do Pedido Nº | Descrição | Qtd | Valor\n"
                    for i in itens:
                        desc = i.get("resourceDescription") or i.get("itemDescription") or i.get("description") or "Sem descrição"
                        qtd = i.get("quantity", 0)
                        val = i.get("unitPrice") or i.get("totalAmount") or 0.0
                        total += qtd * val
                        resposta += f"{i.get('itemNumber','?')} | {desc} | {qtd} | {val:.2f}\n"
                    resposta += f"Total: {total:.2f}"
        elif acao == "autorizar_pedido":
            pid = interpretacao.get("pedido_id")
            if pid:
                sucesso = autorizar_pedido(int(pid))
                resposta = f"✅ Pedido {pid} autorizado!" if sucesso else f"❌ Falha ao autorizar pedido {pid}."
        elif acao == "reprovar_pedido":
            pid = interpretacao.get("pedido_id")
            if pid:
                sucesso = reprovar_pedido(int(pid))
                resposta = f"🚫 Pedido {pid} reprovado!" if sucesso else f"❌ Falha ao reprovar pedido {pid}."
        elif acao == "relatorio_pdf":
            pid = interpretacao.get("pedido_id")
            if pid:
                arquivo = gerar_relatorio_pdf(int(pid))
                resposta = f"📄 PDF gerado: {arquivo}" if arquivo else "❌ Falha ao gerar PDF."

    # Se não entendeu ou ação falhou, tenta comando direto
    if not resposta:
        resposta = processar_comando_sienge(msg.text)

    return {"resposta": resposta or "❌ Sem resposta da IA."}
