import requests
from base64 import b64encode
from datetime import datetime

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

# === FUNÇÕES ===

def listar_pedidos_pendentes(data_inicio=None, data_fim=None):
    """Consulta pedidos de compra pendentes, com ou sem filtro de datas"""
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    if data_inicio:
        url += f"&startDate={data_inicio}"
