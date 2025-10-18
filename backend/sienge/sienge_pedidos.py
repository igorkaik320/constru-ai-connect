import requests
import logging
from base64 import b64encode

# === CONFIGURAÇÃO ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"
token = b64encode(f"{usuario}:{senha}".encode()).decode()
headers = {
    "Authorization": f"Basic {token}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

logging.basicConfig(level=logging.INFO)

# === FUNÇÕES ===

def listar_pedidos_pendentes():
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    r = requests.get(url, headers=headers)
    logging.info(f"listar_pedidos_pendentes: {url} -> {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        pedidos = data.get("results", [])
        # Filtrar apenas pedidos realmente pendentes
        pendentes = [
            p for p in pedidos
            if p.get("status") == "PENDING"
            and not p.get("authorized", False)
            and not p.get("disapproved", False)
        ]
        logging.info(f"🧾 {len(pendentes)} pedidos pendentes encontrados.")
        return pendentes
    return []

def buscar_pedido_por_id(pid):
    url = f"{BASE_URL}/purchase-orders/{pid}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_pedido_por_id: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json()
    return None

def itens_pedido(pid):
    url = f"{BASE_URL}/purchase-orders/{pid}/items"
    r = requests.get(url, headers=headers)
    logging.info(f"itens_pedido: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json().get("results", [])
    return []

def autorizar_pedido(pid, obs=None):
    url = f"{BASE_URL}/purchase-orders/{pid}/authorize"
    body = {"observation": obs} if obs else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"autorizar_pedido: {url} -> {r.status_code}")
    return r.status_code in [200, 204]

def reprovar_pedido(pid, obs=None):
    url = f"{BASE_URL}/purchase-orders/{pid}/disapprove"
    body = {"observation": obs} if obs else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"reprovar_pedido: {url} -> {r.status_code}")
    return r.status_code in [200, 204]

def gerar_relatorio_pdf_bytes(pid):
    url = f"{BASE_URL}/purchase-orders/{pid}/analysis/pdf"
    r = requests.get(url, headers=headers)
    logging.info(f"gerar_relatorio_pdf_bytes: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.content
    return None
