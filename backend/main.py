from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os

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
    return {"message": "🚀 Backend da constru.ia ativado com sucesso!"}

@app.post("/mensagem")
async def message_endpoint(msg: Message):
    print(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")

    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            return {"response": "Erro: chave da OpenAI não configurada."}

        # Nova interface do openai >= 1.0.0
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
