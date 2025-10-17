import requests
from base64 import b64encode
from datetime import datetime

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "gTCWxPf3txvQXwOXn65tz1tA9cdOZZlD"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Token de autenticação (Basic Auth)
token = b64encode(f"{usuario}:{senha}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {token}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

# === FUNÇÕES DE PEDIDOS ===

def listar_pedidos_pendentes(data_inicio=None, data_fim=None):
    """Consulta pedidos de compra pendentes"""
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    if data_inicio:
        url += f"&startDate={data_inicio}"
    if data_fim:
        url += f"&endDate={data_fim}"

    r = requests.get(url, headers=HEADERS)

    print("=== DEBUG listar_pedidos_pendentes ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)

    if r.status_code == 200:
        data = r.json()
        pedidos_filtrados = [p for p in data.get("results", []) if not p.get("authorized", False)]
        return pedidos_filtrados
    elif r.status_code == 401:
        print("❌ Autenticação inválida. Verifique usuário/senha.")
        return []
    else:
        print(f"❌ Erro ao buscar pedidos: {r.status_code} - {r.text}")
        return []

def itens_pedido(purchase_order_id):
    """Consulta itens de um pedido"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/items"
    r = requests.get(url, headers=HEADERS)

    print("=== DEBUG itens_pedido ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)

    if r.status_code == 200:
        data = r.json()
        itens = data.get("results") or data.get("data") or []
        return itens
    elif r.status_code == 401:
        print("❌ Autenticação inválida. Verifique usuário/senha.")
        return []
    else:
        print(f"❌ Erro ao buscar itens: {r.status_code} - {r.text}")
        return []

def autorizar_pedido(purchase_order_id, observacao=None):
    """Autoriza pedido de compra (PUT)"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    body = {}
    if observacao:
        body["observation"] = observacao

    r = requests.put(url, headers=HEADERS, json=body)

    print("=== DEBUG autorizar_pedido ===")
    print("URL:", url)
    print("Body:", body)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)

    if r.status_code in [200, 204]:
        print(f"✅ Pedido {purchase_order_id} autorizado com sucesso!")
        return True
    elif r.status_code == 401:
        print("❌ Autenticação inválida.")
        return False
    else:
        print(f"❌ Erro ao autorizar pedido: {r.status_code} - {r.text}")
        return False

def reprovar_pedido(purchase_order_id, observacao=None):
    """Reprova pedido de compra (PUT)"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {}
    if observacao:
        body["observation"] = observacao

    r = requests.put(url, headers=HEADERS, json=body)

    print("=== DEBUG reprovar_pedido ===")
    print("URL:", url)
    print("Body:", body)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)

    if r.status_code in [200, 204]:
        print(f"🚫 Pedido {purchase_order_id} reprovado com sucesso!")
        return True
    elif r.status_code == 401:
        print("❌ Autenticação inválida.")
        return False
    else:
        print(f"❌ Erro ao reprovar pedido: {r.status_code} - {r.text}")
        return False

def gerar_relatorio_pdf(purchase_order_id):
    """Baixa relatório PDF de análise do pedido"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/analysis/pdf"
    r = requests.get(url, headers=HEADERS)

    print("=== DEBUG gerar_relatorio_pdf ===")
    print("URL:", url)
    print("Status Code:", r.status_code)

    if r.status_code == 200:
        filename = f"relatorio_pedido_{purchase_order_id}.pdf"
        with open(filename, "wb") as f:
            f.write(r.content)
        print(f"✅ Relatório salvo: {filename}")
        return filename
    elif r.status_code == 401:
        print("❌ Autenticação inválida.")
        return None
    else:
        print(f"❌ Erro ao gerar relatório: {r.status_code} - {r.text}")
        return None
