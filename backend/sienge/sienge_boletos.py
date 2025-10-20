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
    """Gera o link para boleto de segunda via."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {
        "billReceivableId": titulo_id,
        "installmentId": parcela_id,
    }

    logging.info("GET %s -> params=%s", url, params)
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info("%s -> %s", url, r.status_code)

    if r.status_code == 200:
        try:
            data = r.json()
            # ⚙️ A API retorna algo como {"link": "https://...", "numeroDigitavel": "..."}
            link = data.get("link")
            if link:
                return link  # 🔗 retorna só o link puro para o backend
            else:
                return json.dumps(data, ensure_ascii=False)
        except Exception:
            return r.text

    logging.warning("Falha gerar link boleto (%s): %s", r.status_code, r.text)
    return f"❌ Erro ao gerar boleto ({r.status_code}). {r.text}"



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
