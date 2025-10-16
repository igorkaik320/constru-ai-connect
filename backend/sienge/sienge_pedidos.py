import requests
from base64 import b64encode
import json
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
    """Consulta pedidos de compra pendentes"""
    url = f"{BASE_URL}/purchase-orders?status=PENDING"
    if data_inicio:
        url += f"&startDate={data_inicio}"
    if data_fim:
        url += f"&endDate={data_fim}"

    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        pedidos_filtrados = [
            p for p in data["results"] if not p["authorized"]
        ]
        print(f"\n🔎 {len(pedidos_filtrados)} pedidos pendentes e não autorizados encontrados.\n")
        for pedido in pedidos_filtrados:
            print(f"🆔 ID: {pedido['id']} | Status: {pedido['status']} | Data: {pedido['date']} | Autorizado: {pedido['authorized']}")
        return pedidos_filtrados
    else:
        print(f"❌ Erro ao buscar pedidos: {r.status_code} - {r.text}")
        return []

def itens_pedido(purchase_order_id):
    """Consulta itens de um pedido"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/items"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        print(f"\nItens do pedido {purchase_order_id}:")
        for item in data.get("results", []):
            # Usando get() para evitar KeyError
            descricao = item.get("itemDescription") or item.get("description") or "Sem descrição"
            quantidade = item.get("quantity", 0)
            valor = item.get("totalAmount", 0.0)
            print(f"Item {item.get('itemNumber', '?')}: {descricao} | Quantidade: {quantidade} | Valor: {valor}")
        return data.get("results", [])
    else:
        print(f"❌ Erro ao buscar itens: {r.status_code} - {r.text}")
        return []

def autorizar_pedido(purchase_order_id, observacao=None):
    """Autoriza pedido"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    body = {}
    if observacao:
        body["observation"] = observacao
        method = requests.patch
    else:
        method = requests.post

    r = method(url, headers=headers, json=body)
    if r.status_code in [200, 204]:
        print(f"✅ Pedido {purchase_order_id} autorizado com sucesso!")
    else:
        print(f"❌ Erro ao autorizar pedido: {r.status_code} - {r.text}")

def reprovar_pedido(purchase_order_id, observacao=None):
    """Reprova pedido"""
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    body = {}
    if observacao:
        body["observation"] = observacao
        method = requests.patch
    else:
        method = requests.post

    r = method(url, headers=headers, json=body)
    if r.status_code in [200, 204]:
        print(f"🚫 Pedido {purchase_order_id} reprovado com sucesso!")
    else:
        print(f"❌ Erro ao reprovar pedido: {r.status_code} - {r.text}")

# === INTERPRETAÇÃO DE COMANDOS ===
def interpretar_comando(comando):
    comando = comando.lower().strip()

    if comando.startswith("pedidos pendentes"):
        # extrair datas se houver
        partes = comando.split("de")
        data_inicio, data_fim = None, None
        if len(partes) > 1:
            try:
                datas = partes[1].split("a")
                data_inicio = datetime.strptime(datas[0].strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
                data_fim = datetime.strptime(datas[1].strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
            except:
                pass
        listar_pedidos_pendentes(data_inicio, data_fim)

    elif comando.startswith("itens do pedido"):
        try:
            pid = int(comando.split()[-1])
            itens_pedido(pid)
        except:
            print("❌ Comando inválido. Ex: 'Itens do pedido 285'")

    elif comando.startswith("autorizar o pedido"):
        try:
            parts = comando.split("com observação")
            pid = int(parts[0].split()[-1])
            obs = parts[1].strip() if len(parts) > 1 else None
            autorizar_pedido(pid, obs)
        except:
            print("❌ Comando inválido. Ex: 'Autorizar o pedido 285 com observação Teste'")

    elif comando.startswith("reprovar o pedido"):
        try:
            parts = comando.split("com observação")
            pid = int(parts[0].split()[-1])
            obs = parts[1].strip() if len(parts) > 1 else None
            reprovar_pedido(pid, obs)
        except:
            print("❌ Comando inválido. Ex: 'Reprovar o pedido 281'")

    elif comando in ["sair", "exit"]:
        print("Encerrando...")
        exit()

    else:
        print("❌ Comando não reconhecido.")

def processar_comandos(comandos):
    for cmd in comandos:
        interpretar_comando(cmd)

# === LOOP PRINCIPAL ===
if __name__ == "__main__":
    print("Bem-vindo ao sistema IA-Sienge Avançado!")
    print("Digite um comando ou 'sair' para encerrar. Ex.:")
    print("- Pedidos pendentes de 01/07/2025 a 31/08/2025")
    print("- Itens do pedido 285")
    print("- Autorizar o pedido 285 com observação Teste")
    print("- Reprovar o pedido 281")

    while True:
        comandos = input("\n> ").split(";")  # permite múltiplos comandos separados por ;
        processar_comandos([c.strip() for c in comandos])
