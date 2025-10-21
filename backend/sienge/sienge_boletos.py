import requests
import logging
from base64 import b64encode
from functools import lru_cache

# 🚀 Identificação da versão atual
logging.warning("🚀 Rodando versão 1.3 do sienge_boletos.py (com verificação de segunda via)")

# ============================================================
# 🔐 CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE
# ============================================================
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ============================================================
# 👤 CLIENTE
# ============================================================
def buscar_cliente_por_cpf(cpf: str):
    """Busca cliente no Sienge pelo CPF."""
    url = f"{BASE_URL}/customers?cpf={cpf}"
    logging.info(f"GET {url}")
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"{url} -> {r.status_code}")
