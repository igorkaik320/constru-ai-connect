import requests
import logging

BASE_URL = "https://api.sienge.com.br/cctcontrol/public/api/v1"
HEADERS = {
    "Authorization": f"Bearer {SEU_TOKEN_AQUI}",
    "Content-Type": "application/json"
}

def buscar_cliente_por_cpf(cpf: str):
    """Busca cliente no Sienge pelo CPF"""
    url = f"{BASE_URL}/customers?cpf={cpf}"
    r = requests.get(url, headers=HEADERS)
    logging.info(f"GET {url} -> {r.status_code}")
    
    if r.status_code != 200:
        return None
    
    data = r.json()
    results = data.get("results") or data
    if isinstance(results, list) and len(results) > 0:
        return results[0]
    return None
