import requests
import logging
from base64 import b64encode

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# === Auth básico ===
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ===========================================================
# 👤 Função: Buscar cliente por CPF
# ===========================================================

def buscar_cliente_por_cpf(cpf: str):
    """Busca cliente no Sienge pelo CPF"""
    url = f"{BASE_URL}/customers?cpf={cpf}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")

    if r.status_code != 200:
        logging.warning(f"Erro ao buscar cliente: {r.text}")
        return None

    try:
        data = r.json()
        results = data.get("results") or data
        if isinstance(results, list) and len(results) > 0:
            return results[0]
        return None
    except Exception as e:
        logging.exception("Erro ao processar retorno do Sienge:")
        return None
