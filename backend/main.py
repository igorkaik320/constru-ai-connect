from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import json

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

# === Função para formatar itens do pedido em tabela ===
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

        # Remove blocos de código Markdown
        conteudo = conteudo.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(conteudo)
            return data
        except Exception:
            return {"acao": None, "erro": "Resposta IA inválida", "detalhes": conteudo}

    except Exception as e:
        return {"acao": None, "erro": str(e)}

# === Endpoint principal de mensagens ===
@app.post("/mensagem")
async def message_endpoint(msg: Message):
    print(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    # Processa sempre via IA
    intencao = entender_intencao(msg.text)
    print("🧠 Interpretação IA:", intencao)

    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {})

    if not acao:
        return {"response": "Desculpe, não entendi o que você deseja fazer no Sienge."}

    try:
        # === Listar pedidos pendentes ===
        if acao == "listar_pedidos_pendentes":
            data_inicio = parametros.get("data_inicio")
            data_fim = parametros.get("data_fim")
            pedidos = listar_pedidos_pendentes(data_inicio, data_fim)
            if not pedidos:
                return {"response": "Nenhum pedido pendente encontrado."}
            resposta = "\n".join([f"ID {p['id']} | {p['status']} | {p['date']}" for p in pedidos])
            return {"response": resposta}

        # === Itens do pedido ===
        elif acao == "itens_pedido":
            # Corrigido: pega do 'parametros' ou direto do 'intencao'
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Não consegui identificar o ID do pedido. Pode informar novamente?"}

            itens = itens_pedido(pid)
            resposta = formatar_itens(itens)
            return {"response": resposta}

        # === Autorizar pedido ===
        elif acao == "autorizar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Qual é o ID do pedido que você quer autorizar?"}
            obs = parametros.get("observacao")
            autorizar_pedido(pid, obs)
            return {"response": f"✅ Pedido {pid} autorizado com sucesso!"}

        # === Reprovar pedido ===
        elif acao == "reprovar_pedido":
            pid = parametros.get("pedido_id") or intencao.get("pedido_id")
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return {"response": "Qual é o ID do pedido que você quer reprovar?"}
            obs = parametros.get("observacao")
            reprovar_pedido(pid, obs)
            return {"response": f"🚫 Pedido {pid} reprovado com sucesso!"}

        # === Outros comandos (placeholders) ===
        elif acao in ["gerar_boleto", "gerar_imposto_renda", "saldo_devedor"]:
            return {"response": f"Ação {acao} reconhecida. (⚠️ Implementar chamada à API Sienge aqui)"}

        else:
            return {"response": f"Desculpe, ainda não sei executar a ação {acao} no Sienge."}

    except Exception as e:
        print("❌ Erro ao executar ação:", e)
        return {"response": f"Erro ao executar ação {acao}: {e}"}
