import requests
import logging
from base64 import b64encode

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Auth básico
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ==============================================================
# 🔍 FUNÇÃO PRINCIPAL — Buscar cliente por CPF
# ==============================================================

def buscar_cliente_por_cpf(cpf: str):
    """Busca cliente no Sienge pelo CPF."""
    cpf_limpo = cpf.replace(".", "").replace("-", "")
    url = f"{BASE_URL}/customers?cpf={cpf_limpo}"
    logging.info(f"GET {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        logging.info(f"{url} -> {r.status_code}")

        if r.status_code != 200:
            logging.warning(f"Erro na API: {r.text}")
            return None

        data = r.json()
        results = data.get("results") or data
        if isinstance(results, list) and len(results) > 0:
            cliente = results[0]
            logging.info(f"✅ Cliente encontrado: {cliente.get('name')}")
            return cliente

        return None

    except Exception as e:
        logging.exception("Erro ao buscar cliente:")
        return None
