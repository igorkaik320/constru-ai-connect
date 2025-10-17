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
                return "❌ Não consegui identificar o ID do pedido."
            autorizar_pedido(int(pid))
            return f"✅ Pedido {pid} autorizado com sucesso!"

        elif texto.startswith("reprova"):
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido."
            reprovar_pedido(int(pid))
            return f"🚫 Pedido {pid} reprovado com sucesso!"

        elif "relatorio" in texto or "pdf" in texto:
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido para gerar o relatório."
            pdf_bytes = gerar_relatorio_pdf(int(pid))
            if not pdf_bytes:
                return "❌ Não foi possível gerar o relatório."
            filename = f"relatorio_pedido_{pid}.pdf"
            with open(filename, "wb") as f:
                f.write(pdf_bytes)
            return f"📄 Relatório gerado: {filename}"

        return None
    except Exception as e:
        return f"❌ Erro ao processar comando Sienge: {e}"

# === Endpoint principal de mensagens ===
@app.post("/mensagem")
async def message_endpoint(msg: Message):
    print(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    # 1️⃣ Tenta processar como comando direto
    resposta_sienge = processar_comando_sienge(msg.text)
    if resposta_sienge:
        print(f"🤖 Resposta direta Sienge: {resposta_sienge}")
        return {"response": resposta_sienge}

    # 2️⃣ Caso contrário, tenta entender a intenção natural
    intencao = entender_intencao(msg.text)
    print("🧠 Interpretação IA:", intencao)

    acao = intencao.get("acao")

    if not acao:
        return {"response": "Desculpe, não entendi o que você deseja fazer no Sienge."}

    # 3️⃣ Executa conforme a intenção reconhecida
    try:
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            return {"response": "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])}

        elif acao == "itens_pedido":
            pid = int(intencao["parametros"].get("pedido_id", 0))
            itens = itens_pedido(pid)
            if not itens:
                return {"response": "Nenhum item encontrado."}
            resposta = "Itens do Pedido Nº | Descrição | Qtd | Valor\n"
            total = 0
            for i in itens:
                desc = i.get("resourceDescription") or i.get("itemDescription") or i.get("description") or "Sem descrição"
                qtd = i.get("quantity", 0)
                val = i.get("unitPrice") or i.get("totalAmount") or 0.0
                total += qtd * val
                resposta += f"{i.get('itemNumber','?')} | {desc} | {qtd} | {val:.2f}\n"
            resposta += f"Total: {total:.2f}"
            return {"response": resposta}

        elif acao == "autorizar_pedido":
            pid = int(intencao["parametros"].get("pedido_id", 0))
            obs = intencao["parametros"].get("observacao")
            autorizar_pedido(pid, obs)
            return {"response": f"✅ Pedido {pid} autorizado com sucesso!"}

        elif acao == "reprovar_pedido":
            pid = int(intencao["parametros"].get("pedido_id", 0))
            obs = intencao["parametros"].get("observacao")
            reprovar_pedido(pid, obs)
            return {"response": f"🚫 Pedido {pid} reprovado com sucesso!"}

        elif acao == "relatorio_pdf":
            pid = int(intencao["parametros"].get("pedido_id", 0))
            pdf_bytes = gerar_relatorio_pdf(pid)
            if not pdf_bytes:
                return {"response": "❌ Não foi possível gerar o relatório."}
            filename = f"relatorio_pedido_{pid}.pdf"
            with open(filename, "wb") as f:
                f.write(pdf_bytes)
            return {"response": f"📄 Relatório gerado: {filename}"}

        else:
            return {"response": "Desculpe, ainda não sei executar essa ação no Sienge."}

    except Exception as e:
        print("❌ Erro ao executar ação:", e)
        return {"response": f"Erro ao executar ação {acao}: {e}"}
