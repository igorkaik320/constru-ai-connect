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
        # === PEDIDOS PENDENTES ===
        if texto.startswith("pedidos pendentes"):
            pedidos = listar_pedidos_pendentes()
            if pedidos:
                return "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])
            return "Nenhum pedido pendente encontrado."

        # === AUTORIZAR PEDIDO ===
        elif texto.startswith("autoriza") or texto.startswith("autorizar") or texto.startswith("quero autorizar"):
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido."
            autorizar_pedido(int(pid))
            return f"✅ Pedido {pid} autorizado com sucesso!"

        # === REPROVAR PEDIDO ===
        elif texto.startswith("reprova") or texto.startswith("reprovar") or texto.startswith("quero reprovar"):
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido."
            reprovar_pedido(int(pid))
            return f"🚫 Pedido {pid} reprovado com sucesso!"

        # === ITENS DO PEDIDO ===
        elif "itens do pedido" in texto or texto.startswith("pedido"):
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

        # === RELATÓRIO PDF ===
        elif "relatorio" in texto or "pdf" in texto:
            pid = ''.join(filter(str.isdigit, texto))
            if not pid:
                return "❌ Não consegui identificar o ID do pedido para gerar o PDF."
            pdf_bytes = gerar_relatorio_pdf(int(pid))
            if not pdf_bytes:
                return "❌ Não consegui gerar o relatório."
            arquivo_pdf = f"Relatorio_Pedido_{pid}.pdf"
            with open(arquivo_pdf, "wb") as f:
                f.write(pdf_bytes)
            return f"✅ Relatório gerado: {arquivo_pdf}"

        return "❌ Não consegui identificar a ação desejada no Sienge."

    except Exception as e:
        return f"❌ Erro ao processar comando Sienge: {e}"


# === Endpoint principal de mensagens ===
@app.post("/mensagem")
def mensagem(msg: Message):
    # Primeiro tenta interpretar via IA
    interpretacao = entender_intencao(msg.text)
    if interpretacao.get("acao"):
        acao = interpretacao["acao"]
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            return {"resposta": "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])}
        elif acao == "itens_pedido":
            pid = interpretacao.get("pedido_id")
            if pid:
                itens = itens_pedido(int(pid))
                if not itens:
                    return {"resposta": "Nenhum item encontrado."}
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
        elif acao == "autorizar_pedido":
            pid = interpretacao.get("pedido_id")
            if pid:
                autorizar_pedido(int(pid))
                return {"resposta": f"✅ Pedido {pid} autorizado com sucesso!"}
        elif acao == "reprovar_pedido":
            pid = interpretacao.get("pedido_id")
            if pid:
                reprovar_pedido(int(pid))
                return {"resposta": f"🚫 Pedido {pid} reprovado com sucesso!"}
        elif acao == "relatorio_pdf":
            pid = interpretacao.get("pedido_id")
            if pid:
                pdf_bytes = gerar_relatorio_pdf(int(pid))
                if not pdf_bytes:
                    return {"resposta": "❌ Não consegui gerar o relatório."}
                arquivo_pdf = f"Relatorio_Pedido_{pid}.pdf"
                with open(arquivo_pdf, "wb") as f:
                    f.write(pdf_bytes)
                return {"resposta": f"✅ Relatório gerado: {arquivo_pdf}"}

    # Se IA não entendeu, tenta processar direto
    resposta_direta = processar_comando_sienge(msg.text)
    return {"resposta": resposta_direta}
