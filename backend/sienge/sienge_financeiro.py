import requests
import logging
from base64 import b64encode
from datetime import datetime

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 1.2 do sienge_financeiro.py (rotas corrigidas e logs detalhados)")

# ============================================================
# 🔐 CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE
# ============================================================
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}


# ============================================================
# 💰 RESUMO FINANCEIRO GERAL
# ============================================================
def resumo_financeiro():
    """Calcula o total de contas a pagar e a receber."""
    try:
        logging.info("📊 Consultando resumo financeiro (contas a pagar e receber)...")

        url_pagar = f"{BASE_URL}/accounts-payable/payable-bills"
        url_receber = f"{BASE_URL}/accounts-receivable/receivable-bills"

        r_pagar = requests.get(url_pagar, headers=json_headers, timeout=40)
        r_receber = requests.get(url_receber, headers=json_headers, timeout=40)

        logging.info(f"➡️ GET {url_pagar} -> {r_pagar.status_code}")
        logging.info(f"➡️ GET {url_receber} -> {r_receber.status_code}")

        if r_pagar.status_code != 200 or r_receber.status_code != 200:
            logging.error("Erro nas requisições financeiras")
            return {"erro": "❌ Erro ao buscar dados financeiros no Sienge."}

        contas_pagar = r_pagar.json().get("results", [])
        contas_receber = r_receber.json().get("results", [])

        logging.info(f"📦 {len(contas_pagar)} títulos a pagar | {len(contas_receber)} a receber")

        # Função auxiliar para extrair o valor corretamente
        def extrair_valor(item):
            for campo in ["amount", "value", "billValue", "totalValue"]:
                if campo in item:
                    return float(item[campo] or 0)
            return 0.0

        total_pagar = sum(extrair_valor(i) for i in contas_pagar)
        total_receber = sum(extrair_valor(i) for i in contas_receber)
        lucro = total_receber - total_pagar

        logging.info(f"💸 A pagar: {total_pagar}")
        logging.info(f"💰 A receber: {total_receber}")
        logging.info(f"📈 Lucro: {lucro}")

        return {
            "periodo": "Geral",
            "a_pagar": total_pagar,
            "a_receber": total_receber,
            "lucro": lucro,
        }

    except Exception as e:
        logging.exception("Erro ao calcular resumo financeiro:")
        return {"erro": str(e)}


# ============================================================
# 🏗️ GASTOS POR OBRA
# ============================================================
def gastos_por_obra():
    """Agrupa os valores de contas a pagar por obra."""
    try:
        url = f"{BASE_URL}/accounts-payable/payable-bills"
        logging.info(f"🏗️ Consultando gastos por obra: {url}")
        r = requests.get(url, headers=json_headers, timeout=40)
        logging.info(f"➡️ Status: {r.status_code}")

        if r.status_code != 200:
            return {"erro": f"Erro ao consultar obras ({r.status_code})"}

        dados = r.json().get("results", [])
        logging.info(f"📦 {len(dados)} registros retornados.")

        obras = {}
        for item in dados:
            obra = item.get("unitName") or item.get("unitId") or "Sem obra"
            valor = float(item.get("amount") or item.get("value") or 0)
            obras[obra] = obras.get(obra, 0) + valor

        for nome, val in obras.items():
            logging.info(f"🏗️ {nome}: {val}")

        return [{"obra": k, "valor": v} for k, v in obras.items()]

    except Exception as e:
        logging.exception("Erro ao buscar gastos por obra:")
        return {"erro": str(e)}


# ============================================================
# 🧩 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    """Agrupa os valores de contas a pagar por centro de custo."""
    try:
        url = f"{BASE_URL}/accounts-payable/payable-bills"
        logging.info(f"🏢 Consultando gastos por centro de custo: {url}")
        r = requests.get(url, headers=json_headers, timeout=40)
        logging.info(f"➡️ Status: {r.status_code}")

        if r.status_code != 200:
            return {"erro": f"Erro ao consultar centros de custo ({r.status_code})"}

        dados = r.json().get("results", [])
        logging.info(f"📦 {len(dados)} registros retornados.")

        centros = {}
        for item in dados:
            centro = item.get("costCenterName") or item.get("costCenterId") or "Sem centro de custo"
            valor = float(item.get("amount") or item.get("value") or 0)
            centros[centro] = centros.get(centro, 0) + valor

        for nome, val in centros.items():
            logging.info(f"🏢 {nome}: {val}")

        return [{"centro_custo": k, "valor": v} for k, v in centros.items()]

    except Exception as e:
        logging.exception("Erro ao buscar gastos por centro de custo:")
        return {"erro": str(e)}
