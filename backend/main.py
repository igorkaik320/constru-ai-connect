import requests
from base64 import b64encode
import logging

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

def listar_pedidos_pendentes():
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    r = requests.get(url, headers=headers)
    logging.info(f"listar_pedidos_pendentes: {url} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        return [p for p in data.get("results", []) if not p.get("authorized", False)]
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

def buscar_empresa(id_):
    if not id_:
        return {}
    url = f"{BASE_URL}/companies/{id_}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_empresa: {url} -> {r.status_code}")
    return r.json() if r.status_code == 200 else {}

def buscar_obra(id_):
    if not id_:
        return {}
    url = f"{BASE_URL}/buildings/{id_}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_obra: {url} -> {r.status_code}")
    return r.json() if r.status_code == 200 else {}

def buscar_centro_custo(id_):
    if not id_:
        return {}
    url = f"{BASE_URL}/cost-centers/{id_}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_centro_custo: {url} -> {r.status_code}")
    return r.json() if r.status_code == 200 else {}

def buscar_fornecedor(id_):
    if not id_:
        return {}
    url = f"{BASE_URL}/suppliers/{id_}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_fornecedor: {url} -> {r.status_code}")
    return r.json() if r.status_code == 200 else {}

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
    return r.content if r.status_code == 200 and r.content else None
