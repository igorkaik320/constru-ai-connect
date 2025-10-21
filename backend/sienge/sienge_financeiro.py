import requests
import logging
import datetime
import pandas as pd
from base64 import b64encode

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 3.1 do sienge_financeiro.py (DRE + Fluxo + Obras + Fornecedores)")

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
# 🧮 FUNÇÕES AUXILIARES
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def get_date(days_ago=30):
    hoje = datetime.date.today()
    return (hoje - datetime.timedelta(days=days_ago)).isoformat(), hoje.isoformat()


def get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    logging.info(f"➡️ GET {url}")
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info(f"📦 Status: {r.status_code}")
    if r.status_code == 200:
        return r.json()
    logging.error(f"❌ Erro na requisição: {r.status_code} -> {r.text[:200]}")
    return {}

# ============================================================
# 💰 1️⃣ RESUMO FINANCEIRO / DRE
# ============================================================
def resumo_financeiro_dre():
    logging.info("📊 Consultando DRE resumido...")

    inicio, fim = get_date(30)
    logging.info(f"📅 Período: {inicio} até {fim}")

    # --- Contas a pagar ---
    pagar = get("bills", {"startDate": inicio, "endDate": fim})
    total_pagar = sum(i.get("totalInvoiceAmount", 0) for i in pagar.get("results", []))

    # --- Contas a receber ---
    receber = get("accounts-receivable/receivable-bills", {"startDate": inicio, "endDate": fim})
    total_receber = sum(i.get("amount", 0) for i in receber.get("results", []))

    lucro = total_receber - total_pagar

    dre = {
        "periodo": {"inicio": inicio, "fim": fim},
        "receitas": total_receber,
        "despesas": total_pagar,
        "lucro": lucro,
        "formatado": {
            "receitas": money(total_receber),
            "despesas": money(total_pagar),
            "lucro": money(lucro),
        },
    }

    logging.info(f"💰 Receita: {money(total_receber)} | Despesa: {money(total_pagar)} | Lucro: {money(lucro)}")
    return dre

# ============================================================
# 📈 2️⃣ FLUXO DE CAIXA (Entradas e Saídas por dia)
# ============================================================
def fluxo_caixa(dias=30):
    logging.info("📊 Gerando fluxo de caixa diário...")

    inicio, fim = get_date(dias)
    bills = get("bills", {"startDate": inicio, "endDate": fim}).get("results", [])
    df = pd.DataFrame(bills)

    if df.empty:
        logging.warning("⚠️ Nenhum dado financeiro encontrado.")
        return []

    df["issueDate"] = pd.to_datetime(df["issueDate"], errors="coerce")
    df["totalInvoiceAmount"] = pd.to_numeric(df["totalInvoiceAmount"], errors="coerce").fillna(0)

    fluxo = (
        df.groupby(df["issueDate"].dt.date)["totalInvoiceAmount"]
        .sum()
        .reset_index()
        .rename(columns={"issueDate": "data", "totalInvoiceAmount": "valor"})
    )

    fluxo["tipo"] = "Saída"
    fluxo = fluxo.to_dict(orient="records")
    logging.info(f"📅 {len(fluxo)} dias processados no fluxo de caixa")
    return fluxo

# ============================================================
# 🏗️ 3️⃣ GASTOS POR OBRA
# ============================================================
def gastos_por_obra():
    logging.info("🏗️ Consultando gastos por obra...")
    inicio, fim = get_date(60)
    bills = get("bills", {"startDate": inicio, "endDate": fim}).get("results", [])
    dados = []

    for b in bills:
        bill_id = b.get("id")
        total = b.get("totalInvoiceAmount", 0)
        obras = get(f"bills/{bill_id}/buildings-cost").get("results", [])
        for o in obras:
            dados.append({
                "obra": o.get("buildingName", "Sem nome"),
                "empresa": o.get("costEstimationSheetName", "Não informado"),
                "valor": total * (o.get("percentage", 0) / 100),
            })

    df = pd.DataFrame(dados)
    if df.empty:
        return []

    df = df.groupby(["empresa", "obra"])["valor"].sum().reset_index()
    logging.info(f"🏗️ {len(df)} obras encontradas.")
    return df.to_dict(orient="records")

# ============================================================
# 🧾 4️⃣ GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    logging.info("🏢 Consultando gastos por centro de custo...")
    inicio, fim = get_date(60)
    bills = get("bills", {"startDate": inicio, "endDate": fim}).get("results", [])
    dados = []

    for b in bills:
        bill_id = b.get("id")
        total = b.get("totalInvoiceAmount", 0)
        centros = get(f"bills/{bill_id}/budget-categories").get("results", [])
        for c in centros:
            dados.append({
                "centro_custo": c.get("paymentCategoriesId", "Não informado"),
                "valor": total * (c.get("percentage", 0) / 100),
            })

    df = pd.DataFrame(dados)
    if df.empty:
        return []

    df = df.groupby("centro_custo")["valor"].sum().reset_index()
    logging.info(f"🏢 {len(df)} centros de custo processados.")
    return df.to_dict(orient="records")

# ============================================================
# 👥 5️⃣ GASTOS POR FORNECEDOR
# ============================================================
def gastos_por_fornecedor():
    logging.info("👥 Consultando gastos por fornecedor...")
    inicio, fim = get_date(60)
    bills = get("bills", {"startDate": inicio, "endDate": fim}).get("results", [])

    df = pd.DataFrame(bills)
    if df.empty:
        return []

    df = df.groupby("creditorId")["totalInvoiceAmount"].sum().reset_index()
    df = df.sort_values(by="totalInvoiceAmount", ascending=False)
    df.rename(columns={"creditorId": "fornecedor", "totalInvoiceAmount": "valor"}, inplace=True)

    logging.info(f"👥 {len(df)} fornecedores processados.")
    return df.to_dict(orient="records")

# ============================================================
# 📊 6️⃣ RELATÓRIO UNIFICADO
# ============================================================
def gerar_relatorio_json():
    return {
        "dre": resumo_financeiro_dre(),
        "fluxo_caixa": fluxo_caixa(),
        "gastos_por_obra": gastos_por_obra(),
        "gastos_por_centro_custo": gastos_por_centro_custo(),
        "gastos_por_fornecedor": gastos_por_fornecedor(),
    }
