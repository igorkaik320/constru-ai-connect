import requests
from base64 import b64encode
import logging

# --- Configurações ---
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

# --- Funções ---

def listar_pedidos_pendentes():
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    r = requests.get(url, headers=headers)
    logging.info(f"listar_pedidos_pendentes: {url} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        results = data.get("results", [])
        # filtra apenas pedidos não autorizados e não reprovados
        return [p for p in results if not p.get("authorized") and not p.get("disapproved")]
    return []

def buscar_pedido_por_id(pid):
    url = f"{BASE_URL}/purchase-orders/{pid}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_pedido_por_id: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json()
    return {}

def itens_pedido(pid):
    url = f"{BASE_URL}/purchase-orders/{pid}/items"
    r = requests.get(url, headers=headers)
    logging.info(f"itens_pedido: {url} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        return data.get("results", [])
    return []

def autorizar_pedido(pid, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{pid}/authorize"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"autorizar_pedido: {url} -> {r.status_code}")
    return r.status_code in [200, 204]

def reprovar_pedido(pid, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{pid}/disapprove"
    body = {"observation": observacao} if observacao else {}
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
