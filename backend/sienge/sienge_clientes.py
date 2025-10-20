import requests
import logging
from base64 import b64encode

# ============================================================
# ⚙️ CONFIGURAÇÕES DE CONEXÃO COM A API SIENGE
# ============================================================

subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Cria o token de autenticação básica (Base64)
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

# Cabeçalhos padrão para requisições JSON
HEADERS = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

# ============================================================
# 👥 FUNÇÃO: Buscar cliente pelo CPF
# ============================================================

def buscar_cliente_por_cpf(cpf: str):
    """
    Busca cliente cadastrado no Sienge pelo CPF.
    Retorna os dados do cliente se encontrado, caso contrário None.

    Exemplo:
        cliente = buscar_cliente_por_cpf("01657831256")
    """
    try:
        # Remove caracteres especiais
        cpf = cpf.replace(".", "").replace("-", "").strip()

        url = f"{BASE_URL}/customers?cpf={cpf}"
        logging.info(f"GET {url}")

        r = requests.get(url, headers=HEADERS, timeout=30)
        logging.info(f"{url} -> {r.status_code}")

        if r.status_code != 200:
            logging.warning(f"Erro ao buscar cliente: {r.text}")
            return None

        data = r.json()
        results = data.get("results") or data

        if isinstance(results, list) and len(results) > 0:
            cliente = results[0]
            logging.info(f"✅ Cliente encontrado: {cliente.get('name')}")
            return cliente

        logging.warning("Nenhum cliente encontrado com esse CPF.")
        return None

    except Exception as e:
        logging.exception("Erro ao buscar cliente por CPF:")
        return None
