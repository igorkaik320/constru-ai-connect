import requests
import logging
import os

# ============================================================
# ⚙️ CONFIGURAÇÕES
# ============================================================
BASE_URL = "https://api.sienge.com.br/cctcontrol/public/api/v1"
SIENGE_USER = os.getenv("SIENGE_USER", "seu_usuario_api")
SIENGE_PASS = os.getenv("SIENGE_PASS", "sua_senha_api")

# ============================================================
# 🧾 FUNÇÃO BASE DE REQUISIÇÃO
# ============================================================
def sienge_get(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    logging.info(f"➡️ GET {url}")
    r = requests.get(url, auth=(SIENGE_USER, SIENGE_PASS))
    logging.info(f"📦 Status: {r.status_code}")
    if r.status_code != 200:
        logging.warning(f"Erro: {r.text}")
        return []
    return r.json().get("results", [])

# ============================================================
# 💰 RESUMO FINANCEIRO
# ============================================================
def resumo_financeiro():
    logging.info("📊 Consultando DRE resumido...")

    contas_pagar = sienge_get("bills")
    contas_receber = sienge_get("accounts-receivable/receivable-bills")

    total_receitas = sum(
        float(c.get("amountValue", 0) or 0) for c in contas_receber if not c.get("cancelled")
    )
    total_despesas = sum(
        float(c.get("amountValue", 0) or 0) for c in contas_pagar if not c.get("cancelled")
    )
    lucro = total_receitas - total_despesas

    logging.info(f"💰 Receita: {total_receitas} | Despesa: {total_despesas} | Lucro: {lucro}")

    return (
        f"📊 **Resumo Financeiro:**\n\n"
        f"💵 Receitas: R$ {total_receitas:,.2f}\n"
        f"💸 Despesas: R$ {total_despesas:,.2f}\n"
        f"📈 Resultado: R$ {lucro:,.2f}"
    )

# ============================================================
# 🏗️ GASTOS POR OBRA
# ============================================================
def gastos_por_obra():
    logging.info("📚 Buscando todas as despesas detalhadas...")

    dados = sienge_get("bills")
    obras = {}

    for item in dados:
        obra = item.get("constructionSite", {}).get("name") or "Obra não informada"
        valor = float(item.get("amountValue", 0) or 0)
        obras[obra] = obras.get(obra, 0) + valor

    if not obras:
        return "📭 Nenhum gasto encontrado."

    linhas = [f"🏗️ {obra}: R$ {valor:,.2f}" for obra, valor in obras.items()]
    return "📊 **Gastos por Obra:**\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 GASTOS POR CENTRO DE CUSTO
# ============================================================
def gastos_por_centro_custo():
    logging.info("📊 Calculando gastos por centro de custo...")

    dados = sienge_get("bills")
    centros = {}

    for item in dados:
        cc = item.get("costCenter", {}).get("name") or "Centro não informado"
        valor = float(item.get("amountValue", 0) or 0)
        centros[cc] = centros.get(cc, 0) + valor

    if not centros:
        return "📭 Nenhum dado encontrado."

    linhas = [f"📂 {cc}: R$ {valor:,.2f}" for cc, valor in centros.items()]
    return "📊 **Gastos por Centro de Custo:**\n\n" + "\n".join(linhas)
