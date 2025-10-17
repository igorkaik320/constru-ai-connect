import requests
from base64 import b64encode

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

# === FUNÇÕES DE PEDIDOS ===

def listar_pedidos_pendentes(data_inicio=None, data_fim=None):
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    if data_inicio:
        url += f"&startDate={data_inicio}"
    if data_fim:
        url += f"&endDate={data_fim}"

    r = requests.get(url, headers=headers)
    print("=== DEBUG listar_pedidos_pendentes ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)

    if r.status_code == 200:
        data = r.json()
        pedidos_filtrados = [p for p in data.get("results", []) if not p.get("authorized", False)]
        return pedidos_filtrados
    return []

def itens_pedido(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/items"
    r = requests.get(url, headers=headers)
    print("=== DEBUG itens_pedido ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    if r.status_code == 200:
        return r.json().get("results", [])
    return []

def autorizar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    print("=== DEBUG autorizar_pedido ===")
    print("URL:", url)
    print("Body:", body)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    return r.status_code in [200, 204]

def reprovar_pedido(purchase_order_id, observacao=None):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {"observation": observacao} if observacao else {}
    r = requests.put(url, headers=headers, json=body)
    print("=== DEBUG reprovar_pedido ===")
    print("URL:", url)
    print("Body:", body)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    return r.status_code in [200, 204]

def gerar_relatorio_pdf(purchase_order_id):
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/analysis/pdf"
    r = requests.get(url, headers=headers)
    print("=== DEBUG gerar_relatorio_pdf ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    if r.status_code == 200:
        filename = f"relatorio_pedido_{purchase_order_id}.pdf"
        with open(filename, "wb") as f:
            f.write(r.content)
        return filename
    return None
