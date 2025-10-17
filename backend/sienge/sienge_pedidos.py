import requests
from base64 import b64encode
import logging

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "gTCWxPf3txvQXwOXn65tz1tA9cdOZZlD"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Token de autenticação
token = b64encode(f"{usuario}:{senha}".encode()).decode()
headers = {
    "Authorization": f"Basic {token}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

# Configura logging
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
        return [p for p in data.get("results", []) if not p.get("authorized", False)]
    return []

def itens_pedido(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/items"
    r = requests.get(url, headers=headers)
    logging.info(f"itens_pedido: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json().get("results", [])
    return []

def autorizar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"autorizar_pedido: {url} -> {r.status_code} | body={body} | response={r.text}")
    return r.status_code in [200, 204]

def reprovar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"reprovar_pedido: {url} -> {r.status_code}")
    return r.status_code in [200, 204]

def gerar_relatorio_pdf_bytes(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/analysis/pdf"
    pdf_headers = headers.copy()
    pdf_headers["Accept"] = "application/pdf"  # Correção para gerar PDF
    r = requests.get(url, headers=pdf_headers)
    logging.info(f"gerar_relatorio_pdf_bytes: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.content
    logging.warning(f"Falha ao gerar PDF: status={r.status_code}, response={r.text}")
    return None

def gerar_relatorio_pdf(purchase_order_id):
    conteudo = gerar_relatorio_pdf_bytes(purchase_order_id)
    if conteudo:
        filename = f"relatorio_pedido_{purchase_order_id}.pdf"
        with open(filename, "wb") as f:
            f.write(conteudo)
        logging.info(f"PDF gerado: {filename}")
        return filename
    logging.warning(f"Não foi possível gerar PDF para o pedido {purchase_order_id}")
    return None

# === NOVOS ENDPOINTS ===

def buscar_pedido_por_id(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}"
    r = requests.get(url, headers=headers)
    logging.info(f"buscar_pedido_por_id: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json()
    return None

def listar_pedidos_por_usuario(usuario_nome):
    url = f"{BASE_URL}/purchase-orders"
    r = requests.get(url, headers=headers)
    logging.info(f"listar_pedidos_por_usuario: {url} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json().get("results", [])
        return [p for p in data if usuario_nome.lower() in (p.get("userName") or "").lower()]
    return []

def listar_pedidos_por_periodo(data_inicio, data_fim):
    url = f"{BASE_URL}/purchase-orders?startDate={data_inicio}&endDate={data_fim}"
    r = requests.get(url, headers=headers)
    logging.info(f"listar_pedidos_por_periodo: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.json().get("results", [])
    return []
