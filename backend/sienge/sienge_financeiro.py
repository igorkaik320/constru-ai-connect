import requests
import logging
import datetime
import pandas as pd
from base64 import b64encode

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 4.0 do sienge_financeiro.py (dados completos + integração IA)")

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
    pagar = get("bills", {"startDate": inicio, "endDate": fim})
    total_pagar = sum(i.get("totalInvoiceAmount", 0) for i in pagar.get("results", []))
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
# 🧾 2️⃣ TODAS AS DESPESAS DETALHADAS
# ============================================================
def todas_despesas_detalhadas(dias=90):
    logging.info("📚 Buscando todas as despesas detalhadas...")
    inicio, fim = get_date(dias)
    bills = get("bills", {"startDate": inicio, "endDate": fim}).get("results", [])
    dados = []

    for b in bills:
        dados.append({
            "empresa": b.get("companyName", "Não informada"),
            "fornecedor": b.get("creditorName", "Não informado"),
            "conta_financeira": b.get("paymentCategoryName", "Não informada"),
            "obra": b.get("buildingName", "Sem obra"),
            "status": b.get("billStatus", "Sem status"),
            "data_emissao": b.get("issueDate"),
            "data_pagamento": b.get("payOffDate"),
            "valor_total": b.get("totalInvoiceAmount", 0),
        })

    df = pd.DataFrame(dados)
    logging.info(f"📦 {len(df)} registros financeiros detalhados coletados.")
    return df

# ============================================================
# 📈 3️⃣ FUNÇÕES DE AGRUPAMENTO
# ============================================================
def gastos_por_obra(dias=60):
    df = todas_despesas_detalhadas(dias)
    if df.empty:
        return []
    df = df.groupby(["empresa", "obra"])["valor_total"].sum().reset_index()
    df.rename(columns={"valor_total": "valor"}, inplace=True)
    return df.to_dict(orient="records")


def gastos_por_centro_custo(dias=60):
    df = todas_despesas_detalhadas(dias)
    if df.empty:
        return []
    df = df.groupby("conta_financeira")["valor_total"].sum().reset_index()
    df.rename(columns={"conta_financeira": "centro_custo", "valor_total": "valor"}, inplace=True)
    return df.to_dict(orient="records")


def gastos_por_fornecedor(dias=60):
    df = todas_despesas_detalhadas(dias)
    if df.empty:
        return []
    df = df.groupby("fornecedor")["valor_total"].sum().reset_index()
    df = df.sort_values(by="valor_total", ascending=False)
    df.rename(columns={"valor_total": "valor"}, inplace=True)
    return df.to_dict(orient="records")

# ============================================================
# 📊 4️⃣ RELATÓRIO UNIFICADO
# ============================================================
def gerar_relatorio_json():
    df = todas_despesas_detalhadas()
    return {
        "dre": resumo_financeiro_dre(),
        "obras": gastos_por_obra(),
        "centros_custo": gastos_por_centro_custo(),
        "fornecedores": gastos_por_fornecedor(),
        "todas_despesas": df.to_dict(orient="records"),
    }
