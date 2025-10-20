import requests
from base64 import b64encode
import logging
from typing import Optional, Dict, Any

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"  # senha da API

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Auth básico
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

# Cabeçalhos padrão JSON
json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

logging.basicConfig(level=logging.INFO)


# ==========================================================
#  FUNÇÕES PARA BOLETOS (segunda via e link temporário)
# ==========================================================

def gerar_link_boleto(title_id: int, installment_number: int) -> Optional[Dict[str, Any]]:
    """
    Gera o link temporário e linha digitável de um boleto via GET /payment-slip-notification.
    O link expira em 5 minutos.
    """
    url = f"{BASE_URL}/payment-slip-notification"
    params = {
        "titleId": title_id,
        "installmentNumber": installment_number
    }

    try:
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        logging.info(f"GET {url} -> {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            link = data.get("link")
            barcode = data.get("barCode")
            if link:
                return {
                    "success": True,
                    "message": (
                        f"💳 Link do boleto (válido por 5 minutos): {link}\n"
                        f"🏦 Linha digitável: {barcode or '-'}"
                    ),
                    "link": link,
                    "barCode": barcode
                }
            return {
                "success": False,
                "message": "❌ Nenhum link retornado pela API do Sienge."
            }

        logging.warning(f"Falha gerar link boleto ({r.status_code}): {r.text}")
        return {
            "success": False,
            "message": f"❌ Falha ao gerar link do boleto (status {r.status_code})."
        }

    except Exception as e:
        logging.exception("Erro ao gerar link do boleto:")
        return {
            "success": False,
            "message": f"❌ Erro interno ao gerar link do boleto: {e}"
        }


def enviar_boleto_email(title_id: int, installment_number: int) -> Dict[str, Any]:
    """
    Envia o boleto de segunda via por e-mail ao cliente (POST /payment-slip-notification).
    """
    url = f"{BASE_URL}/payment-slip-notification"
    body = {
        "titleId": title_id,
        "installmentNumber": installment_number
    }

    try:
        r = requests.post(url, headers=json_headers, json=body, timeout=30)
        logging.info(f"POST {url} -> {r.status_code}")

        if r.status_code == 200:
            return {"success": True, "message": "📧 Boleto enviado por e-mail com sucesso!"}
        elif r.status_code == 404:
            return {"success": False, "message": "❌ Título ou parcela não encontrados."}
        elif r.status_code == 400:
            return {"success": False, "message": "⚠️ Requisição inválida. Verifique os parâmetros enviados."}

        logging.warning(f"Falha enviar boleto ({r.status_code}): {r.text}")
        return {
            "success": False,
            "message": f"❌ Falha ao enviar boleto (status {r.status_code})."
        }

    except Exception as e:
        logging.exception("Erro ao enviar boleto:")
        return {"success": False, "message": f"❌ Erro interno ao enviar boleto: {e}"}
