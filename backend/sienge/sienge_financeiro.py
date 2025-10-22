import requests
import logging
from base64 import b64encode
from datetime import datetime, timedelta

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 4.1 do sienge_financeiro.py (datas automáticas + integração IA)")

# ============================================================
# 🔐 CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE (IGUAL AO BOLETOS)
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

    # ✅ adiciona período padrão se não informado
    if "startDate" not in params:
        inicio, fim = periodo_padrao()
        params["startDate"] = inicio
        params["endDate"] = fim

    try:
        logging.info(f"➡️ GET {url} -> params={params}")
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        logging.info(f"📦 Status: {r.status_code}")

        if r.status_code == 401:
            logging.warning(f"🚫 Falha de autenticação! ({r.text})")
            return []

        if r.status_code != 200:
            logging.warning(f"⚠️ Erro {r.status_code}: {r.text[:300]}")
            return []

        data = r.json()
        return data.get("results") or data

    except Exception as e:
        logging.exception(f"❌ Erro de requisição no endpoint {endpoint}: {e}")
        return []

# ============================================================
# 💰 RESUMO FINANCEIRO (DRE SIMPLIFICADO)
# ============================================================
def resumo_financeiro():
    """Resumo geral de receitas, despesas e lucro."""
    logging.info("📊 Consultando DRE resumido...")

    contas_pagar = sienge_get("bills")
    contas_receber = sienge_get("accounts-receivable/receivable-bills")

    if not contas_pagar and not contas_receber:
        return "⚠️ Nenhum dado retornado da API Sienge. Verifique o período ou as credenciais."

    total_receitas = sum(float(c.get("amountValue", 0) or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("amountValue", 0) or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    return (
        f"📊 **Resumo Financeiro (últimos 12 meses)**\n\n"
        f"💵 Receitas: R$ {total_receitas:,.2f}\n"
        f"💸 Despesas: R$ {total_despesas:,.2f}\n"
        f"📈 Resultado: R$ {lucro:,.2f}"
    )

# ============================================================
# 🏗️ GASTOS POR OBRA
# ============================================================
def gastos_por_obra():
    """Total de gastos agrupados por obra."""
    logging.info("📚 Coletando despesas agrupadas por obra...")
    dados = sienge_get("bills")
    obras = {}

    for item in dados:
        obra = item.get("constructionSite", {}).get("name") or "Obra não informada"
        valor = float(item.get("amountValue", 0) or 0)
        obras[obra] = obras.get(obra, 0) + valor

    if not obras:
        return "📭 Nenhum gasto encontrado nas contas a pagar."

    linhas = [f"🏗️ {obra}: R$ {valor:,.2f}" for obra, valor in obras.items()]
    return "📊 **Gastos por Obra (últimos 12 meses)**\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    """Total de gastos agrupados por centro de custo."""
    logging.info("📊 Calculando gastos por centro de custo...")
    dados = sienge_get("bills")
    centros = {}

    for item in dados:
        cc = item.get("costCenter", {}).get("name") or "Centro de custo não informado"
        valor = float(item.get("amountValue", 0) or 0)
        centros[cc] = centros.get(cc, 0) + valor

    if not centros:
        return "📭 Nenhum dado encontrado para centros de custo."

    linhas = [f"📂 {cc}: R$ {valor:,.2f}" for cc, valor in centros.items()]
    return "📊 **Gastos por Centro de Custo (últimos 12 meses)**\n\n" + "\n".join(linhas)

# ============================================================
# 🧠 PLACEHOLDER DE ANÁLISE COM IA
# ============================================================
def analise_financeira_resumida():
    """Mensagem genérica até integrar o módulo de IA."""
    return "🤖 A análise financeira detalhada será feita com IA (sienge_ia.py)."
