from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# === CRIAR APP FASTAPI ===
app = FastAPI()

# Permitir CORS se for chamar de frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# === FUNÇÕES INTERNAS (sienge) ===

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
    logging.info(f"autorizar_pedido: {url} -> {r.status_code}")
    return r.status_code in [200, 204]

def reprovar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    logging.info(f"reprovar_pedido: {url} -> {r.status_code}")
    return r.status_code in [200, 204]

def gerar_relatorio_pdf_bytes(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/analysis/pdf"
    r = requests.get(url, headers=headers)
    logging.info(f"gerar_relatorio_pdf_bytes: {url} -> {r.status_code}")
    if r.status_code == 200:
        return r.content
    return None

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

# === ROTAS FASTAPI ===

@app.get("/pedidos/pendentes")
def api_listar_pedidos_pendentes(data_inicio: str = None, data_fim: str = None):
    return listar_pedidos_pendentes(data_inicio, data_fim)

@app.get("/pedidos/{purchase_order_id}/itens")
def api_itens_pedido(purchase_order_id: str):
    return itens_pedido(purchase_order_id)

@app.put("/pedidos/{purchase_order_id}/autorizar")
def api_autorizar_pedido(purchase_order_id: str, observacao: str = None):
    sucesso = autorizar_pedido(purchase_order_id, observacao)
    return {"sucesso": sucesso}

@app.put("/pedidos/{purchase_order_id}/reprovar")
def api_reprovar_pedido(purchase_order_id: str, observacao: str = None):
    sucesso = reprovar_pedido(purchase_order_id, observacao)
    return {"sucesso": sucesso}

@app.get("/pedidos/{purchase_order_id}/pdf")
def api_gerar_pdf(purchase_order_id: str):
    conteudo = gerar_relatorio_pdf_bytes(purchase_order_id)
    if conteudo:
        return {"pdf_bytes": b64encode(conteudo).decode()}  # Retorna base64
    return {"erro": "Não foi possível gerar PDF"}

@app.get("/pedidos/{purchase_order_id}")
def api_buscar_pedido_por_id(purchase_order_id: str):
    pedido = buscar_pedido_por_id(purchase_order_id)
    if pedido:
        return pedido
    return {"erro": "Pedido não encontrado"}

@app.get("/pedidos/usuario/{usuario_nome}")
def api_listar_por_usuario(usuario_nome: str):
    return listar_pedidos_por_usuario(usuario_nome)

@app.get("/pedidos/periodo")
def api_listar_por_periodo(data_inicio: str, data_fim: str):
    return listar_pedidos_por_periodo(data_inicio, data_fim)
