import requests
import logging
from base64 import b64encode

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 4.0 do sienge_financeiro.py (dados completos + integração IA)")

# ============================================================
# 🔐 CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE (MESMO PADRÃO DO BOLETOS)
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
# ⚙️ FUNÇÃO BASE DE REQUISIÇÃO
# ============================================================
def sienge_get(endpoint, params=None):
    """Faz requisições GET autenticadas na API Sienge."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        logging.info(f"➡️ GET {url}")
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        logging.info(f"📦 Status: {r.status_code}")

        if r.status_code == 401:
            logging.warning(f"🚫 Falha de autenticação! ({r.text})")
            return []

        if r.status_code != 200:
            logging.warning(f"⚠️ Erro {r.status_code}: {r.text[:200]}")
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
    """Gera um resumo simples com total de receitas, despesas e lucro."""
    logging.info("📊 Consultando DRE resumido...")

    contas_pagar = sienge_get("bills")
    contas_receber = sienge_get("accounts-receivable/receivable-bills")

    if not contas_pagar and not contas_receber:
        return "⚠️ Não foi possível obter os dados financeiros (401 - credenciais inválidas ou API bloqueada)."

    total_receitas = sum(float(c.get("amountValue", 0) or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("amountValue", 0) or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    logging.info(f"💰 Receita: R$ {total_receitas:,.2f} | Despesa: R$ {total_despesas:,.2f} | Lucro: R$ {lucro:,.2f}")

    return (
        f"📊 **Resumo Financeiro (Sienge)**\n\n"
        f"💵 Receitas: R$ {total_receitas:,.2f}\n"
        f"💸 Despesas: R$ {total_despesas:,.2f}\n"
        f"📈 Resultado: R$ {lucro:,.2f}"
    )

# ============================================================
# 🏗️ GASTOS POR OBRA
# ============================================================
def gastos_por_obra():
    """Lista o total de gastos agrupados por obra."""
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
    return "📊 **Gastos por Obra (Sienge)**\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    """Lista os gastos agrupados por centro de custo."""
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
    return "📊 **Gastos por Centro de Custo (Sienge)**\n\n" + "\n".join(linhas)

# ============================================================
# 🧠 ANÁLISE FINANCEIRA (IA FUTURA)
# ============================================================
def analise_financeira_resumida():
    """Retorna mensagem genérica de placeholder para integração IA."""
    return "🤖 A análise financeira detalhada será gerada pela IA (sienge_ia.py)."
