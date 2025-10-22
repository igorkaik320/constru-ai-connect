import requests
import logging
from base64 import b64encode
from datetime import datetime, timedelta

logging.warning("🚀 Rodando versão 4.5 do sienge_financeiro.py (valores corrigidos + layout formatado)")

# 🔐 Configurações de autenticação
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
# Datas padrão
# ============================================================
def periodo_padrao():
    fim = datetime.now().date()
    inicio = fim - timedelta(days=365)
    return inicio.isoformat(), fim.isoformat()

# ============================================================
# Requisição base
# ============================================================
def sienge_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    if params is None:
        params = {}

    if "startDate" not in params:
        inicio, fim = periodo_padrao()
        params["startDate"], params["endDate"] = inicio, fim

    try:
        logging.info(f"➡️ GET {url} -> params={params}")
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        logging.info(f"📦 Status: {r.status_code}")
        if r.status_code != 200:
            logging.warning(f"⚠️ Erro {r.status_code}: {r.text[:300]}")
            return []
        data = r.json()
        return data.get("results") or data
    except Exception as e:
        logging.exception(f"❌ Erro em {endpoint}: {e}")
        return []

# ============================================================
# 💰 Resumo Financeiro
# ============================================================
def resumo_financeiro(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    contas_pagar = sienge_get("bills", params)
    contas_receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(c.get("receivableBillValue") or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("totalInvoiceAmount") or c.get("totalValueAmount") or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    return (
        f"📊 **Resumo Financeiro (Período {params.get('startDate')} a {params.get('endDate')})**\n\n"
        f"💵 Receitas: R$ {total_receitas:,.2f}\n"
        f"💸 Despesas: R$ {total_despesas:,.2f}\n"
        f"📈 Resultado: R$ {lucro:,.2f}"
    )

# ============================================================
# 🏗️ Gastos por Obra
# ============================================================
def gastos_por_obra(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    dados = sienge_get("bills", params)
    obras = {}

    for item in dados:
        obra = item.get("buildingCost", {}).get("name") or item.get("notes", "Obra não informada")
        valor = float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0)
        obras[obra] = obras.get(obra, 0) + valor

    if not obras:
        return "📭 Nenhum gasto encontrado."

    # Ordenar do maior para o menor
    obras = dict(sorted(obras.items(), key=lambda x: x[1], reverse=True))
    total = sum(obras.values())
    linhas = []
    for i, (obra, valor) in enumerate(obras.items()):
        if i >= 10:
            linhas.append(f"...(+{len(obras)-10} outras obras)")
            break
        percentual = (valor / total * 100) if total else 0
        linhas.append(f"🏗️ **{obra[:50]}** — R$ {valor:,.2f} ({percentual:.1f}%)")

    return f"📊 **Top Obras por Gastos ({params.get('startDate')} a {params.get('endDate')})**\n\n" + "\n".join(linhas)

# ============================================================
# 📂 Gastos por Centro de Custo
# ============================================================
def gastos_por_centro_custo(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    dados = sienge_get("bills", params)
    centros = {}
    for item in dados:
        cc = item.get("departmentCost", {}).get("name") or "Centro não informado"
        valor = float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0)
        centros[cc] = centros.get(cc, 0) + valor

    if not centros:
        return "📭 Nenhum dado encontrado."

    centros = dict(sorted(centros.items(), key=lambda x: x[1], reverse=True))
    linhas = [f"📂 {cc}: R$ {valor:,.2f}" for cc, valor in list(centros.items())[:10]]
    return "📊 **Top Centros de Custo**\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 Relatório JSON (para dashboard/IA)
# ============================================================
def gerar_relatorio_json(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    contas_pagar = sienge_get("bills", params)
    contas_receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(c.get("receivableBillValue") or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("totalInvoiceAmount") or c.get("totalValueAmount") or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    dre_formatado = {
        "receitas": f"R$ {total_receitas:,.2f}",
        "despesas": f"R$ {total_despesas:,.2f}",
        "lucro": f"R$ {lucro:,.2f}",
    }

    todas_despesas = []
    for item in contas_pagar:
        todas_despesas.append({
            "empresa": item.get("enterprise", {}).get("name") or "N/A",
            "fornecedor": item.get("provider", {}).get("name") or "N/A",
            "centro_custo": item.get("departmentCost", {}).get("name") or "N/A",
            "conta_financeira": item.get("financialAccount", {}).get("name") or "N/A",
            "obra": item.get("buildingCost", {}).get("name") or "N/A",
            "status": item.get("status", "N/A"),
            "valor_total": float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0),
            "data_vencimento": item.get("dueDate", "N/A"),
        })

    return {"todas_despesas": todas_despesas, "dre": {"formatado": dre_formatado}}
