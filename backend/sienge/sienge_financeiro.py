import requests
import logging
from base64 import b64encode
from datetime import datetime, timedelta

# ============================================================
# 🚀 IDENTIFICAÇÃO
# ============================================================
logging.warning("🚀 Rodando versão 2.0 do sienge_financeiro.py (endpoint oficial /bills do Sienge)")

# ============================================================
# 🔐 AUTENTICAÇÃO
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
# 🧠 FUNÇÃO AUXILIAR
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def periodo_padrao(dias=30):
    """Retorna período padrão (últimos N dias) no formato yyyy-MM-dd"""
    fim = datetime.now().date()
    ini = fim - timedelta(days=dias)
    return ini.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d")


# ============================================================
# 💰 RESUMO FINANCEIRO GERAL
# ============================================================
def resumo_financeiro():
    """Busca títulos a pagar e a receber no período atual."""
    try:
        logging.info("📊 Consultando resumo financeiro...")

        start, end = periodo_padrao(30)
        logging.info(f"📅 Período: {start} até {end}")

        # ===== CONTAS A PAGAR =====
        url_pagar = f"{BASE_URL}/bills?startDate={start}&endDate={end}"
        logging.info(f"➡️ GET {url_pagar}")
        r_pagar = requests.get(url_pagar, headers=json_headers, timeout=40)

        if r_pagar.status_code != 200:
            logging.error(f"❌ Erro contas a pagar -> {r_pagar.status_code}")
            contas_pagar = []
        else:
            contas_pagar = r_pagar.json().get("results", [])
            logging.info(f"📦 {len(contas_pagar)} títulos a pagar retornados")

        # ===== CONTAS A RECEBER =====
        url_receber = f"{BASE_URL}/accounts-receivable/receivable-bills"
        logging.info(f"➡️ GET {url_receber}")
        r_receber = requests.get(url_receber, headers=json_headers, timeout=40)

        if r_receber.status_code != 200:
            logging.error(f"❌ Erro contas a receber -> {r_receber.status_code}")
            contas_receber = []
        else:
            contas_receber = r_receber.json().get("results", [])
            logging.info(f"📦 {len(contas_receber)} títulos a receber retornados")

        # ===== SOMATÓRIOS =====
        total_pagar = sum(float(i.get("totalInvoiceAmount") or 0) for i in contas_pagar)
        total_receber = sum(float(i.get("amount") or i.get("value") or 0) for i in contas_receber)
        lucro = total_receber - total_pagar

        logging.info(f"💸 A pagar: {total_pagar}")
        logging.info(f"💰 A receber: {total_receber}")
        logging.info(f"📈 Lucro: {lucro}")

        return {
            "periodo": f"{start} até {end}",
            "a_pagar": total_pagar,
            "a_receber": total_receber,
            "lucro": lucro,
        }

    except Exception as e:
        logging.exception("Erro no resumo financeiro:")
        return {"erro": str(e)}


# ============================================================
# 🏗️ GASTOS POR OBRA
# ============================================================
def gastos_por_obra():
    """Agrupa títulos por obra (building)."""
    try:
        start, end = periodo_padrao(30)
        url = f"{BASE_URL}/bills?startDate={start}&endDate={end}"
        logging.info(f"🏗️ Consultando gastos por obra: {url}")

        r = requests.get(url, headers=json_headers, timeout=40)
        if r.status_code != 200:
            return {"erro": f"Erro ({r.status_code}) ao buscar obras"}

        dados = r.json().get("results", [])
        logging.info(f"📦 {len(dados)} títulos retornados.")

        obras = {}
        for item in dados:
            obra = item.get("originId") or "Sem origem"
            valor = float(item.get("totalInvoiceAmount") or 0)
            obras[obra] = obras.get(obra, 0) + valor

        for nome, val in obras.items():
            logging.info(f"🏗️ {nome}: {money(val)}")

        return [{"obra": k, "valor": v} for k, v in obras.items()]

    except Exception as e:
        logging.exception("Erro em gastos_por_obra:")
        return {"erro": str(e)}


# ============================================================
# 🧩 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    """Agrupa títulos por centro de custo, via apropriação financeira."""
    try:
        start, end = periodo_padrao(30)
        url = f"{BASE_URL}/bills?startDate={start}&endDate={end}"
        logging.info(f"🏢 Consultando gastos por centro de custo: {url}")

        r = requests.get(url, headers=json_headers, timeout=40)
        if r.status_code != 200:
            return {"erro": f"Erro ({r.status_code}) ao buscar títulos"}

        dados = r.json().get("results", [])
        centros = {}

        for item in dados:
            bill_id = item.get("id")
            if not bill_id:
                continue

            # Busca apropriações financeiras do título
            url_cc = f"{BASE_URL}/bills/{bill_id}/budget-categories"
            r_cc = requests.get(url_cc, headers=json_headers, timeout=20)

            if r_cc.status_code != 200:
                continue

            categorias = r_cc.json().get("results", [])
            for cat in categorias:
                cc = str(cat.get("costCenterId") or "Sem CC")
                perc = float(cat.get("percentage") or 0)
                valor_total = float(item.get("totalInvoiceAmount") or 0)
                valor_parcial = valor_total * (perc / 100)
                centros[cc] = centros.get(cc, 0) + valor_parcial

        for nome, val in centros.items():
            logging.info(f"🏢 {nome}: {money(val)}")

        return [{"centro_custo": k, "valor": v} for k, v in centros.items()]

    except Exception as e:
        logging.exception("Erro em gastos_por_centro_custo:")
        return {"erro": str(e)}
