import requests
import logging
from base64 import b64encode

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 1.3 do sienge_financeiro.py (fallback automático para rotas financeiras)")

# ============================================================
# 🔐 AUTENTICAÇÃO SIENGE
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
# 💰 RESUMO FINANCEIRO GERAL (com fallback automático)
# ============================================================
def resumo_financeiro():
    """Calcula total de contas a pagar e receber com fallback inteligente."""
    try:
        logging.info("📊 Consultando resumo financeiro (contas a pagar e receber)...")

        rotas_pagar = [
            f"{BASE_URL}/accounts-payable/payable-bills",
            f"{BASE_URL}/accounts-payable/payable-titles",
            f"{BASE_URL}/accounts-payable/payables"
        ]
        rota_pagar_valida = None
        contas_pagar = []

        # Tenta rotas até encontrar uma que funcione
        for rota in rotas_pagar:
            r = requests.get(rota, headers=json_headers, timeout=40)
            logging.info(f"➡️ Testando rota a pagar: {rota} -> {r.status_code}")
            if r.status_code == 200:
                contas_pagar = r.json().get("results", [])
                rota_pagar_valida = rota
                logging.info(f"✅ Rota válida encontrada: {rota}")
                break

        if not rota_pagar_valida:
            logging.error("❌ Nenhuma rota válida para contas a pagar encontrada.")
            return {"erro": "Não foi possível acessar contas a pagar."}

        # Contas a receber
        rota_receber = f"{BASE_URL}/accounts-receivable/receivable-bills"
        r_receber = requests.get(rota_receber, headers=json_headers, timeout=40)
        logging.info(f"➡️ GET {rota_receber} -> {r_receber.status_code}")

        if r_receber.status_code != 200:
            logging.error("❌ Erro ao acessar contas a receber.")
            return {"erro": "Erro ao buscar contas a receber."}

        contas_receber = r_receber.json().get("results", [])

        logging.info(f"📦 {len(contas_pagar)} títulos a pagar | {len(contas_receber)} a receber")

        # Função auxiliar
        def extrair_valor(item):
            for campo in ["amount", "value", "billValue", "totalValue"]:
                if campo in item:
                    return float(item[campo] or 0)
            return 0.0

        total_pagar = sum(extrair_valor(i) for i in contas_pagar)
        total_receber = sum(extrair_valor(i) for i in contas_receber)
        lucro = total_receber - total_pagar

        logging.info(f"💸 Total a pagar: {total_pagar}")
        logging.info(f"💰 Total a receber: {total_receber}")
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
# 🏗️ GASTOS POR OBRA (usando rota válida detectada)
# ============================================================
def gastos_por_obra():
    try:
        rotas = [
            f"{BASE_URL}/accounts-payable/payable-bills",
            f"{BASE_URL}/accounts-payable/payable-titles",
            f"{BASE_URL}/accounts-payable/payables"
        ]
        dados = []
        rota_valida = None

        for rota in rotas:
            r = requests.get(rota, headers=json_headers, timeout=40)
            logging.info(f"➡️ Testando rota: {rota} -> {r.status_code}")
            if r.status_code == 200:
                dados = r.json().get("results", [])
                rota_valida = rota
                logging.info(f"✅ Usando rota {rota}")
                break

        if not rota_valida:
            return {"erro": "Nenhuma rota válida encontrada para contas a pagar."}

        obras = {}
        for item in dados:
            obra = item.get("unitName") or item.get("unitId") or "Sem obra"
            valor = float(item.get("amount") or item.get("value") or 0)
            obras[obra] = obras.get(obra, 0) + valor

        for nome, val in obras.items():
            logging.info(f"🏗️ {nome}: {val}")

        return [{"obra": k, "valor": v} for k, v in obras.items()]

    except Exception as e:
        logging.exception("Erro em gastos_por_obra:")
        return {"erro": str(e)}


# ============================================================
# 🧩 GASTOS POR CENTRO DE CUSTO (usando rota válida detectada)
# ============================================================
def gastos_por_centro_custo():
    try:
        rotas = [
            f"{BASE_URL}/accounts-payable/payable-bills",
            f"{BASE_URL}/accounts-payable/payable-titles",
            f"{BASE_URL}/accounts-payable/payables"
        ]
        dados = []
        rota_valida = None

        for rota in rotas:
            r = requests.get(rota, headers=json_headers, timeout=40)
            logging.info(f"➡️ Testando rota: {rota} -> {r.status_code}")
            if r.status_code == 200:
                dados = r.json().get("results", [])
                rota_valida = rota
                logging.info(f"✅ Usando rota {rota}")
                break

        if not rota_valida:
            return {"erro": "Nenhuma rota válida encontrada para contas a pagar."}

        centros = {}
        for item in dados:
            centro = item.get("costCenterName") or item.get("costCenterId") or "Sem centro de custo"
            valor = float(item.get("amount") or item.get("value") or 0)
            centros[centro] = centros.get(centro, 0) + valor

        for nome, val in centros.items():
            logging.info(f"🏢 {nome}: {val}")

        return [{"centro_custo": k, "valor": v} for k, v in centros.items()]

    except Exception as e:
        logging.exception("Erro em gastos_por_centro_custo:")
        return {"erro": str(e)}
