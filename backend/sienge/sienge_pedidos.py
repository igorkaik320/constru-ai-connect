import requests
from base64 import b64encode
import logging

# === CONFIGURAÇÕES ===
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

def listar_pedidos_pendentes(data_inicio=None, data_fim=None):
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    if data_inicio:
        url += f"&startDate={data_inicio}"
    if data_fim:
        url += f"&endDate={data_fim}"

    r = requests.get(url, headers=headers)
    logging.info(f"listar_pedidos_pendentes: {url} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        pedidos = data.get("results", [])
        # 🔹 Garante que só retorne pedidos realmente pendentes
        return [p for p in pedidos if p.get("status") == "PENDING"]
    logging.error(f"Erro ao listar pedidos: {r.text}")
    return []

def itens_pedido(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}"
    r = requests.get(url, headers=headers)
    logging.info(f"itens_pedido: {url} -> {r.status_code}")
    if r.status_code != 200:
        logging.error(f"Erro ao buscar pedido {purchase_order_id}: {r.text}")
        return []

    data = r.json()
    # 🔹 Pega itens dentro da estrutura correta
    itens = data.get("items") or data.get("purchaseItems") or data.get("orderItems") or []
    if not itens:
        logging.warning(f"Nenhum item encontrado no pedido {purchase_order_id}.")
    return itens

def autorizar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"autorizar_pedido: {url} -> {r.status_code} | body={body}")
    return r.status_code in [200, 204]

def reprovar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"reprovar_pedido: {url} -> {r.status_code} | body={body}")
    return r.status_code in [200, 204]

def gerar_relatorio_pdf_bytes(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/analysis/pdf"
    r = requests.get(url, headers=headers)
    logging.info(f"gerar_relatorio_pdf_bytes: {url} -> {r.status_code}")
    if r.status_code == 200 and r.content:
        return r.content
    logging.warning(f"Falha ao gerar PDF: status={r.status_code}")
    return None

def buscar_pedido_por_id(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_pedido_por_id: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json()
    return None
