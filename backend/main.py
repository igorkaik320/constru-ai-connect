from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import json
from datetime import datetime

# === Importa funções Sienge já existentes ===
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido
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
            # remove possíveis ```json ... ``` da resposta
            conteudo = conteudo.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(conteudo)
            return data
        except:
            return {"acao": None, "erro": "Resposta IA inválida", "detalhes": conteudo}

    except Exception as e:
        return {"acao": None, "erro": str(e)}

# === Formatação dos itens do pedido ===
def formatar_itens(itens):
    if not itens:
        return "Nenhum item encontrado."
    
    linhas = ["Itens do Pedido | Descrição | Qtd | Valor"]
    total = 0
    for i in itens:
        desc = i.get("resourceDescription") or i.get("itemDescription") or i.get("description") or "Sem descrição"
        qtd = i.get("quantity", 0)
        valor = i.get("unitPrice") or i.get("totalAmount") or 0.0
        linhas.append(f"{i.get('itemNumber','?')} | {desc} | {qtd} | {valor:.2f}")
        total += qtd * valor
    linhas.append(f"Total: {total:.2f}")
    return "\n".join(linhas)

# === Processamento direto dos comandos existentes (opcional) ===
def processar_comando_sienge(texto: str):
    texto = texto.lower().strip()
    try:
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

        elif texto.startswith("itens do pedido"):
            try:
                pid = int(texto.split()[-1])
            except:
                return "❌ ID do pedido inválido."

            itens = itens_pedido(pid)
            return formatar_itens(itens)

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
    parametros = intencao.get("parametros", {})

    if not acao:
        return {"response": "Desculpe, não entendi o que você deseja fazer no Sienge."}

    try:
        # Listar pedidos pendentes
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if pedidos:
                resposta = "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])
            else:
                resposta = "Nenhum pedido pendente encontrado."
            return {"response": resposta}

        # Itens do pedido
        elif acao == "itens_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            itens = itens_pedido(pid)
            resposta = formatar_itens(itens)
            return {"response": resposta}

        # Autorizar pedido
        elif acao == "autorizar_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            obs = parametros.get("observacao") or intencao.get("observacao")
            try:
                autorizar_pedido(pid, obs)
                return {"response": f"✅ Pedido {pid} autorizado com sucesso!"}
            except Exception as e:
                return {"response": f"❌ Erro ao autorizar pedido {pid}: {e}"}

        # Reprovar pedido
        elif acao == "reprovar_pedido":
            pid = int(parametros.get("pedido_id") or intencao.get("pedido_id", 0))
            obs = parametros.get("observacao") or intencao.get("observacao")
            try:
                reprovar_pedido(pid, obs)
                return {"response": f"🚫 Pedido {pid} reprovado com sucesso!"}
            except Exception as e:
                return {"response": f"❌ Erro ao reprovar pedido {pid}: {e}"}

        # Ações futuras
        elif acao in ["gerar_boleto", "gerar_imposto_renda", "saldo_devedor"]:
            return {"response": f"Ação {acao} reconhecida. (⚠️ Implementar chamada à API Sienge aqui)"}

        else:
            return {"response": "Desculpe, ainda não sei executar essa ação no Sienge."}

    except Exception as e:
        print("❌ Erro ao executar ação:", e)
        return {"response": f"Erro ao executar ação {acao}: {e}"}
