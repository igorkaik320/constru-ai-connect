import requests
import logging
from base64 import b64encode
from datetime import datetime, timedelta

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 4.4 do sienge_financeiro.py (compatibilidade kwargs + debug ativo)")

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
# 📅 FUNÇÃO PADRÃO DE DATAS (últimos 12 meses)
# ============================================================
def periodo_padrao():
    fim = datetime.now().date()
    inicio = fim - timedelta(days=365)
    return inicio.isoformat(), fim.isoformat()

# ============================================================
# ⚙️ FUNÇÃO BASE DE REQUISIÇÃO
# ============================================================
def sienge_get(endpoint, params=None):
    """Faz requisições GET autenticadas na API Sienge."""
    url = f"{BASE_URL}/{endpoint}"

    if params is None:
        params = {}

    if "startDate" not in params:
        inicio, fim = periodo_padrao()
        params["startDate"] = inicio
        params["endDate"] = fim

    try:
        logging.info(f"➡️ GET {url} -> params={params}")
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        logging.info(f"📦 Status: {r.status_code}")

        if r.status_code != 200:
            logging.warning(f"⚠️ Erro {r.status_code}: {r.text[:300]}")
            return []

        data = r.json()
        resultados = data.get("results") or data

        # 🧩 Log de amostra
        if isinstance(resultados, list) and resultados:
            logging.info(f"📄 Exemplo de retorno: {resultados[0]}")
        else:
            logging.warning("⚠️ Nenhum dado encontrado neste endpoint.")

        return resultados

    except Exception as e:
        logging.exception(f"❌ Erro de requisição no endpoint {endpoint}: {e}")
        return []

# ============================================================
# 💰 RESUMO FINANCEIRO (DRE SIMPLIFICADO)
# ============================================================
def resumo_financeiro(params=None, **kwargs):
    """Resumo geral de receitas, despesas e lucro."""
    if not params:
        params = kwargs or {}

    logging.info("📊 DRE Resumido (com período/empresa opcionais)")

    contas_pagar = sienge_get("bills", params)
    contas_receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(c.get("receivableBillValue", 0) or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("totalValueAmount", 0) or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    return (
        f"📊 **Resumo Financeiro**\n\n"
        f"💵 Receitas: R$ {total_receitas:,.2f}\n"
        f"💸 Despesas: R$ {total_despesas:,.2f}\n"
        f"📈 Resultado: R$ {lucro:,.2f}"
    )

# ============================================================
# 🏗️ GASTOS POR OBRA
# ============================================================
def gastos_por_obra(params=None, **kwargs):
    if not params:
        params = kwargs or {}

    logging.info("📚 Coletando despesas agrupadas por obra...")
    dados = sienge_get("bills", params)
    obras = {}

    for item in dados:
        obra = (
            item.get("buildingCost", {}).get("name")
            or item.get("notes", "")
            or "Obra não informada"
        )
        valor = float(item.get("totalValueAmount", 0) or 0)
        obras[obra] = obras.get(obra, 0) + valor

    if not obras:
        return "📭 Nenhum gasto encontrado nas contas a pagar."

    linhas = [f"🏗️ {obra[:50]}...: R$ {valor:,.2f}" for obra, valor in obras.items()]
    return "📊 **Gastos por Obra**\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo(params=None, **kwargs):
    if not params:
        params = kwargs or {}

    logging.info("📊 Calculando gastos por centro de custo...")
    dados = sienge_get("bills", params)
    centros = {}

    for item in dados:
        cc = item.get("departmentCost", {}).get("name") or "Centro de custo não informado"
        valor = float(item.get("totalValueAmount", 0) or 0)
        centros[cc] = centros.get(cc, 0) + valor

    if not centros:
        return "📭 Nenhum dado encontrado para centros de custo."

    linhas = [f"📂 {cc}: R$ {valor:,.2f}" for cc, valor in centros.items()]
    return "📊 **Gastos por Centro de Custo**\n\n" + "\n".join(linhas)

# ============================================================
# 🧩 RELATÓRIO JSON (para dashboard e IA)
# ============================================================
def gerar_relatorio_json(params=None, **kwargs):
    """Gera um dicionário completo para o dashboard."""
    if not params:
        params = kwargs or {}

    contas_pagar = sienge_get("bills", params)
    contas_receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(c.get("receivableBillValue", 0) or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("totalValueAmount", 0) or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    dre_formatado = {
        "receitas": f"R$ {total_receitas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "despesas": f"R$ {total_despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "lucro": f"R$ {lucro:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
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
            "valor_total": float(item.get("totalValueAmount", 0) or 0),
            "data_vencimento": item.get("dueDate", "N/A"),
        })

    return {
        "todas_despesas": todas_despesas,
        "dre": {"formatado": dre_formatado},
    }
