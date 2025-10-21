import requests
import logging
from base64 import b64encode
from datetime import datetime

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 1.0 do sienge_financeiro.py (consultas financeiras gerais)")

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
# 💰 RESUMO FINANCEIRO GERAL (Entradas x Saídas)
# ============================================================
def resumo_financeiro(periodo_inicio: str = None, periodo_fim: str = None):
    """Calcula o total de contas a pagar e a receber no período informado."""
    try:
        params = {}
        if periodo_inicio and periodo_fim:
            params = {"startDate": periodo_inicio, "endDate": periodo_fim}

        logging.info("📊 Consultando resumo financeiro (contas a pagar e receber)...")

        pagar = requests.get(f"{BASE_URL}/accounts-payable", headers=json_headers, params=params, timeout=30)
        receber = requests.get(f"{BASE_URL}/accounts-receivable", headers=json_headers, params=params, timeout=30)

        if pagar.status_code != 200 or receber.status_code != 200:
            return {"erro": "❌ Erro ao buscar dados financeiros no Sienge."}

        contas_pagar = pagar.json().get("results", [])
        contas_receber = receber.json().get("results", [])

        total_pagar = sum(float(c.get("value", 0)) for c in contas_pagar)
        total_receber = sum(float(c.get("value", 0)) for c in contas_receber)
        lucro = total_receber - total_pagar

        logging.info(f"💸 A pagar: {total_pagar} | 💰 A receber: {total_receber} | Lucro: {lucro}")

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
        logging.info("🏗️ Consultando gastos por obra...")
        r = requests.get(f"{BASE_URL}/accounts-payable", headers=json_headers, timeout=30)
        if r.status_code != 200:
            return {"erro": f"Erro ao consultar obras ({r.status_code})"}

        dados = r.json().get("results", [])
        obras = {}

        for item in dados:
            obra = item.get("unitName") or item.get("unitId") or "Não informado"
            valor = float(item.get("value", 0))
            obras[obra] = obras.get(obra, 0) + valor

        logging.info(f"✅ {len(obras)} obras com lançamentos encontrados.")
        return [{"obra": k, "valor": v} for k, v in obras.items()]

    except Exception as e:
        logging.exception("Erro ao buscar gastos por obra:")
        return {"erro": str(e)}


# ============================================================
# 🧩 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    """Agrupa os valores de contas a pagar por centro de custo (costCenterName)."""
    try:
        logging.info("🏢 Consultando gastos por centro de custo...")
        r = requests.get(f"{BASE_URL}/accounts-payable", headers=json_headers, timeout=30)
        if r.status_code != 200:
            return {"erro": f"Erro ao consultar centros de custo ({r.status_code})"}

        dados = r.json().get("results", [])
        centros = {}

        for item in dados:
            centro = item.get("costCenterName") or item.get("costCenterId") or "Não informado"
            valor = float(item.get("value", 0))
            centros[centro] = centros.get(centro, 0) + valor

        logging.info(f"✅ {len(centros)} centros de custo encontrados.")
        return [{"centro_custo": k, "valor": v} for k, v in centros.items()]

    except Exception as e:
        logging.exception("Erro ao buscar gastos por centro de custo:")
        return {"erro": str(e)}
