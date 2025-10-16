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

# === FUNÇÕES DE PEDIDOS ===

def listar_pedidos_pendentes(data_inicio=None, data_fim=None):
    """Consulta pedidos de compra pendentes, com ou sem filtro de datas"""
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    if data_inicio:
        url += f"&startDate={data_inicio}"
    if data_fim:
        url += f"&endDate={data_fim}"

    r = requests.get(url, headers=headers)
    
    # DEBUG completo da resposta
    print("=== DEBUG listar_pedidos_pendentes ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    
    if r.status_code == 200:
        data = r.json()
        pedidos_filtrados = [p for p in data.get("results", []) if not p.get("authorized", False)]
        print(f"\n🔎 {len(pedidos_filtrados)} pedidos pendentes e não autorizados encontrados.\n")
        for pedido in pedidos_filtrados:
            print(f"🆔 ID: {pedido.get('id')} | Status: {pedido.get('status')} | Data: {pedido.get('date')} | Autorizado: {pedido.get('authorized')}")
        return pedidos_filtrados
    else:
        print(f"❌ Erro ao buscar pedidos: {r.status_code} - {r.text}")
        return []

def itens_pedido(purchase_order_id):
    """Consulta itens de um pedido"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/items"
    r = requests.get(url, headers=headers)
    
    # DEBUG completo da resposta
    print("=== DEBUG itens_pedido ===")
    print("URL:", url)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    
    if r.status_code == 200:
        data = r.json()
        print(f"\nItens do pedido {purchase_order_id}:")
        for item in data.get("results", []):
            # Usa resourceDescription primeiro, depois itemDescription e description
            descricao = item.get("resourceDescription") or item.get("itemDescription") or item.get("description") or "Sem descrição"
            quantidade = item.get("quantity", 0)
            valor = item.get("unitPrice") or item.get("totalAmount") or 0.0
            print(f"Item {item.get('itemNumber', '?')}: {descricao} | Quantidade: {quantidade} | Valor: {valor}")
        return data.get("results", [])
    else:
        print(f"❌ Erro ao buscar itens: {r.status_code} - {r.text}")
        return []

def autorizar_pedido(purchase_order_id, observacao=None):
    """Autoriza pedido de compra"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    body = {}
    method = requests.post
    if observacao:
        body["observation"] = observacao
        method = requests.patch

    r = method(url, headers=headers, json=body)

    # DEBUG completo
    print("=== DEBUG autorizar_pedido ===")
    print("URL:", url)
    print("Body:", body)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    
    if r.status_code in [200, 204]:
        print(f"✅ Pedido {purchase_order_id} autorizado com sucesso!")
    else:
        print(f"❌ Erro ao autorizar pedido: {r.status_code} - {r.text}")

def reprovar_pedido(purchase_order_id, observacao=None):
    """Reprova pedido de compra"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {}
    method = requests.post
    if observacao:
        body["observation"] = observacao
        method = requests.patch

    r = method(url, headers=headers, json=body)

    # DEBUG completo
    print("=== DEBUG reprovar_pedido ===")
    print("URL:", url)
    print("Body:", body)
    print("Status Code:", r.status_code)
    print("Response Text:", r.text)
    
    if r.status_code in [200, 204]:
        print(f"🚫 Pedido {purchase_order_id} reprovado com sucesso!")
    else:
        print(f"❌ Erro ao reprovar pedido: {r.status_code} - {r.text}")
