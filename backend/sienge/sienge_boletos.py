import requests
import logging
import json
from base64 import b64encode

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Auth básico
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ==============================================================
# 🔍 BUSCAR CLIENTE POR CPF
# ==============================================================

def buscar_cliente_por_cpf(cpf: str):
    url = f"{BASE_URL}/customers?cpf={cpf}"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return None

    data = r.json()
    results = data.get("results") or data
    if isinstance(results, list) and len(results) > 0:
        return results[0]
    return None


# ==============================================================
# 🧾 BOLETOS
# ==============================================================

def listar_boletos_por_cliente(cliente_id: int):
    """Busca boletos em aberto por cliente"""
    url = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return []

    data = r.json()
    boletos = data.get("results") or []
    return boletos


def listar_parcelas(titulo_id: int):
    """Busca as parcelas de um título (necessário para gerar boleto)"""
    url = f"{BASE_URL}/accounts-receivable/receivable-bills/{titulo_id}/installments"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return []
    return r.json().get("results") or []


def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    """Gera link de segunda via do boleto"""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    logging.info(f"GET {url} -> params={params}")
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info(f"{url} -> {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        results = data.get("results") or data.get("data") or []
        if results and isinstance(results, list):
            result = results[0]
            link = result.get("urlReport")
            linha_digitavel = result.get("digitableNumber")
            if link:
                return (
                    f"📄 **Segunda via gerada com sucesso!**\n"
                    f"🔗 [Clique aqui para abrir o boleto]({link})\n"
                    f"💳 **Linha digitável:** `{linha_digitavel}`"
                )
    return f"❌ Erro ao gerar boleto ({r.status_code})."


# ==============================================================
# 🔗 BUSCAR BOLETOS POR CPF COMPLETO
# ==============================================================

def buscar_boletos_por_cpf(cpf: str):
    """Busca boletos e parcelas reais a partir do CPF"""
    cliente = buscar_cliente_por_cpf(cpf)
    if not cliente:
        return {"erro": "❌ Nenhum cliente encontrado com esse CPF."}

    nome = cliente.get("name")
    cid = cliente.get("id")
    logging.info(f"✅ Cliente encontrado: {nome} (ID {cid})")

    boletos = listar_boletos_por_cliente(cid)
    if not boletos:
        return {"erro": f"📭 Nenhum boleto encontrado para {nome}."}

    lista = []
    for b in boletos:
        titulo_id = b.get("id")
        valor = b.get("amount") or (b.get("billReceivable") or {}).get("amount")
        desc = b.get("description") or (b.get("billReceivable") or {}).get("description") or "-"
        parcelas = listar_parcelas(titulo_id)

        for p in parcelas:
            parcela_id = p.get("id")
            venc = p.get("dueDate")
            valor_parcela = p.get("amount") or valor or 0.0

            lista.append({
                "titulo_id": titulo_id,
                "parcela_id": parcela_id,
                "descricao": desc,
                "valor": valor_parcela,
                "vencimento": venc,
            })

    if not lista:
        return {"erro": f"📭 Nenhuma parcela em aberto para {nome}."}

    return {
        "nome": nome,
        "boletos": lista
    }
