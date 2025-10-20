import requests
import logging
from base64 import b64encode
from typing import Optional, Dict, Any

# ==========================
# 🔧 CONFIGURAÇÕES SIENGE
# ==========================
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Auth básico (Base64)
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

# Cabeçalhos
json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

logging.basicConfig(level=logging.INFO)


# ==========================
# 🧾 FUNÇÕES DE BOLETO
# ==========================

def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    """
    Gera o link para o boleto de segunda via (GET /payment-slip-notification)
    """
    url = f"{BASE_URL}/payment-slip-notification"
    params = {
        "billReceivableId": titulo_id,
        "installmentId": parcela_id,
    }

    logging.info("GET %s -> params=%s", url, params)
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info("GET %s -> %s", url, r.status_code)

    if r.status_code == 200:
        try:
            data = r.json()
            link = data.get("url")
            linha_digitavel = data.get("digitableLine")

            if link:
                return (
                    "💳 **Boleto gerado com sucesso!**\n\n"
                    f"🔗 [Clique aqui para abrir o boleto]({link})\n"
                    f"🏦 Linha digitável: `{linha_digitavel or '-'}`\n\n"
                    "⚠️ O link expira em **5 minutos**."
                )
            else:
                return "⚠️ Boleto gerado, mas o link não foi retornado pela API."

        except Exception as e:
            logging.warning("Erro ao processar resposta do boleto: %s", e)
            return f"❌ Erro ao processar o retorno do boleto: {e}"

    else:
        logging.warning("Falha gerar link boleto (%s): %s", r.status_code, r.text)
        return f"❌ Erro ao gerar boleto ({r.status_code}): {r.text}"


def enviar_boleto_email(titulo_id: int, parcela_id: int) -> str:
    """
    Envia o boleto de segunda via por e-mail (POST /payment-slip-notification)
    """
    url = f"{BASE_URL}/payment-slip-notification"
    body = {
        "billReceivableId": titulo_id,
        "installmentId": parcela_id,
    }

    logging.info("POST %s -> body=%s", url, body)
    r = requests.post(url, headers=json_headers, json=body, timeout=30)
    logging.info("POST %s -> %s", url, r.status_code)

    if r.status_code in (200, 204):
        return "📧 Boleto enviado com sucesso para o e-mail do cliente!"
    else:
        logging.warning("Falha enviar boleto (%s): %s", r.status_code, r.text)
        return f"❌ Falha ao enviar boleto ({r.status_code}): {r.text}"
