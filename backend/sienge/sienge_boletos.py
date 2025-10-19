import requests
import logging
from dotenv import load_dotenv
import os

load_dotenv()

SIENGE_URL = os.getenv("SIENGE_URL")
SIENGE_USER = os.getenv("SIENGE_USER")
SIENGE_PASS = os.getenv("SIENGE_PASS")

# 🔐 Autenticação básica
def auth():
    return (SIENGE_USER, SIENGE_PASS)


# 🔹 Gera link de segunda via de boleto
def gerar_link_boleto(titulo_id: int, parcela_id: int):
    url = f"{SIENGE_URL}/payment-slip-notification"
    params = {"titleId": titulo_id, "installmentId": parcela_id}

    logging.info(f"🔗 Gerando link do boleto: {url} {params}")

    response = requests.get(url, params=params, auth=auth())

    if response.status_code == 200:
        data = response.json()
        link = data.get("link")
        codigo = data.get("digitableLine")
        return f"📄 Link do boleto: {link}\n💳 Código de barras: {codigo}"
    else:
        logging.warning(f"Erro ao gerar link de boleto: {response.status_code} - {response.text}")
        return "⚠️ Não foi possível gerar o link do boleto."


# 🔹 Envia boleto por e-mail
def enviar_boleto_email(titulo_id: int, parcela_id: int):
    url = f"{SIENGE_URL}/payment-slip-notification"
    payload = {"titleId": titulo_id, "installmentId": parcela_id}

    logging.info(f"📧 Enviando boleto por e-mail: {payload}")

    response = requests.post(url, json=payload, auth=auth())

    if response.status_code == 200:
        return "✅ Boleto de segunda via enviado por e-mail com sucesso!"
    else:
        logging.warning(f"Erro ao enviar boleto: {response.status_code} - {response.text}")
        return "⚠️ Falha ao enviar o boleto por e-mail."
