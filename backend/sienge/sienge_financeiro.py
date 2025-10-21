import requests
import logging
from base64 import b64encode
from datetime import datetime

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 1.1 do sienge_financeiro.py (logs detalhados de retorno Sienge)")

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
def resumo_financeiro(periodo_inicio: str = None, periodo_fim: str = None):
    """Calcula o total de contas a pagar e a receber com logs detalhados."""
    try:
        params = {}
        if periodo_inicio and periodo_fim:
            params = {"startDate": periodo_inicio, "endDate": periodo_fim}

        logging.info("📊 Consultando resumo financeiro (contas a pagar e receber)...")

        # Contas a pagar
        url_pagar = f"{BASE_URL}/accounts-payable"
        pagar = requests.get(url_pagar, headers=json_headers, params=params, timeout=40)
        logging.info(f"➡️ GET {url_pagar} -> {pagar.status_code}")

        # Contas a receber
        url_receber = f"{BASE_URL}/accounts-receivable"
        receber = requests.get(url_receber, headers=json_headers, params=params, timeout=40)
        logging.info(f"➡️ GET {url_receber} -> {receber.status_code}")

        if pagar.status_code != 200 or receber.status_code != 200:
            logging.error(f"Erro nas requisições: pagar={pagar.status_code}, receber={receber.status_code}")
            return {"erro": "❌ Erro ao buscar dados financeiros no Sienge."}

        contas_pagar = pagar.json().get("results", [])
        contas_receber = receber.json().get("results", [])

        logging.info(f"📦 Contas a pagar: {len(contas_pagar)} registros")
        logging.info(f"📦 Contas a receber: {len(contas_receber)} registros")

        # Mostra um exemplo do retorno
        if contas_pagar:
            exemplo = contas_pagar[0]
            logging.info(f"🔍 Exemplo contas a pagar: {str(exemplo)[:400]}")
        if contas_receber:
            exemplo = contas_receber[0]
            logging.info(f"🔍 Exemplo contas a receber: {str(exemplo)[:400]}")

        # Soma total (verifica vários campos comuns)
        def extrair_valor(item):
            for campo in ["value", "amount", "billValue", "totalValue", "installmentValue"]:
                if campo in item:
                    return float(item[campo] or 0)
            return 0.0

        total_pagar = sum(extrair_valor(c) for c in contas_pagar)
        total_receber = sum(extrair_valor(c) for c in contas_receber)
        lucro = total_receber - total_pagar

        logging.info(f"💸 Total a pagar: {total_pagar}")
        logging.info(f"💰 Total a receber: {total_receber}")
        logging.info(f"📈 Lucro: {lucro}")

        return {
            "periodo": f"{periodo_inicio or 'início'} até {periodo_fim or 'hoje'}",
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
    """Agrupa os valores de contas a pagar por obra (unitName)."""
    try:
        url = f"{BASE_URL}/accounts-payable"
        logging.info(f"🏗️ Consultando gastos por obra: GET {url}")
        r = requests.get(url, headers=json_headers, timeout=40)
        logging.info(f"➡️ Status: {r.status_code}")

        if r.status_code != 200:
            return {"erro": f"Erro ao consultar obras ({r.status_code})"}

        dados = r.json().get("results", [])
        logging.info(f"📦 {len(dados)} registros retornados.")

        if dados:
            logging.info(f"🔍 Exemplo de item: {str(dados[0])[:400]}")

        obras = {}
        for item in dados:
            obra = item.get("unitName") or item.get("unitId") or "Não informado"
            valor = item.get("value") or item.get("amount") or item.get("totalValue") or 0
            valor = float(valor)
            obras[obra] = obras.get(obra, 0) + valor

        logging.info(f"✅ {len(obras)} obras com lançamentos encontrados.")
        for nome, val in obras.items():
            logging.info(f"🏗️ {nome} -> {val}")

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
        url = f"{BASE_URL}/accounts-payable"
        logging.info(f"🏢 Consultando gastos por centro de custo: GET {url}")
        r = requests.get(url, headers=json_headers, timeout=40)
        logging.info(f"➡️ Status: {r.status_code}")

        if r.status_code != 200:
            return {"erro": f"Erro ao consultar centros de custo ({r.status_code})"}

        dados = r.json().get("results", [])
        logging.info(f"📦 {len(dados)} registros retornados.")

        if dados:
            logging.info(f"🔍 Exemplo de item: {str(dados[0])[:400]}")

        centros = {}
        for item in dados:
            centro = item.get("costCenterName") or item.get("costCenterId") or "Não informado"
            valor = item.get("value") or item.get("amount") or item.get("totalValue") or 0
            valor = float(valor)
            centros[centro] = centros.get(centro, 0) + valor

        logging.info(f"✅ {len(centros)} centros de custo encontrados.")
        for nome, val in centros.items():
            logging.info(f"🏢 {nome} -> {val}")

        return [{"centro_custo": k, "valor": v} for k, v in centros.items()]

    except Exception as e:
        logging.exception("Erro ao buscar gastos por centro de custo:")
        return {"erro": str(e)}
