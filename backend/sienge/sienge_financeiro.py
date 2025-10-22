import requests
import logging
from base64 import b64encode
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 4.2 do sienge_financeiro.py (datas/empresa, relatorio_json e IA)")

# ============================================================
# 🔐 AUTENTICAÇÃO (igual aos boletos)
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
# 📅 Período padrão (últimos 12 meses)
# ============================================================
def periodo_padrao() -> Tuple[str, str]:
    fim = datetime.now().date()
    inicio = fim - timedelta(days=365)
    return inicio.isoformat(), fim.isoformat()

# ============================================================
# ⚙️ GET helper
# ============================================================
def sienge_get(endpoint: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}/{endpoint}"
    params = dict(params or {})

    if "startDate" not in params or "endDate" not in params:
        i, f = periodo_padrao()
        params.setdefault("startDate", i)
        params.setdefault("endDate", f)

    try:
        logging.info(f"➡️ GET {url} -> params={params}")
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        logging.info(f"📦 Status: {r.status_code}")

        if r.status_code != 200:
            logging.warning(f"⚠️ Erro {r.status_code}: {r.text[:400]}")
            return []

        data = r.json()
        return data.get("results") or (data if isinstance(data, list) else [])
    except Exception as e:
        logging.exception(f"❌ Erro em {endpoint}:")
        return []

# ============================================================
# 🔢 Dinheiro bonitinho
# ============================================================
def money(v: float) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

# ============================================================
# 💰 Resumo Financeiro
# params opcionais: startDate, endDate, enterpriseId
# ============================================================
def resumo_financeiro(**params) -> str:
    logging.info("📊 DRE Resumido (com período/empresa opcionais)")
    pagar = sienge_get("bills", params)
    receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(x.get("amountValue") or x.get("amount") or 0) for x in receber)
    total_despesas = sum(float(x.get("amountValue") or x.get("amount") or 0) for x in pagar)
    lucro = total_receitas - total_despesas

    i = params.get("startDate") or periodo_padrao()[0]
    f = params.get("endDate") or periodo_padrao()[1]
    emp = params.get("enterpriseId")

    subtitulo = f"Período {i} → {f}" + (f" • Empresa {emp}" if emp else "")
    return (
        f"📊 **Resumo Financeiro**\n"
        f"🗓️ {subtitulo}\n\n"
        f"💵 Receitas: {money(total_receitas)}\n"
        f"💸 Despesas: {money(total_despesas)}\n"
        f"📈 Resultado: {money(lucro)}"
    )

# ============================================================
# 🏗️ Gastos por obra
# ============================================================
def gastos_por_obra(**params) -> str:
    dados = sienge_get("bills", params)
    obras: Dict[str, float] = {}
    for x in dados:
        obra = (
            (x.get("constructionSite") or {}).get("name")
            or x.get("constructionSiteName")
            or "Obra não informada"
        )
        valor = float(x.get("amountValue") or x.get("amount") or 0)
        obras[obra] = obras.get(obra, 0) + valor

    if not obras:
        return "📭 Nenhum gasto encontrado nesse período/empresa."

    i = params.get("startDate") or periodo_padrao()[0]
    f = params.get("endDate") or periodo_padrao()[1]
    emp = params.get("enterpriseId")
    header = f"🗓️ {i} → {f}" + (f" • Empresa {emp}" if emp else "")

    linhas = [f"🏗️ {obra}: {money(v)}" for obra, v in sorted(obras.items(), key=lambda kv: kv[1], reverse=True)]
    return "📊 **Gastos por Obra**\n" + header + "\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 Gastos por centro de custo
# ============================================================
def gastos_por_centro_custo(**params) -> str:
    dados = sienge_get("bills", params)
    centros: Dict[str, float] = {}
    for x in dados:
        cc = (x.get("costCenter") or {}).get("name") or x.get("costCenterName") or "Centro não informado"
        valor = float(x.get("amountValue") or x.get("amount") or 0)
        centros[cc] = centros.get(cc, 0) + valor

    if not centros:
        return "📭 Nenhum dado de centros de custo nesse período/empresa."

    i = params.get("startDate") or periodo_padrao()[0]
    f = params.get("endDate") or periodo_padrao()[1]
    emp = params.get("enterpriseId")
    header = f"🗓️ {i} → {f}" + (f" • Empresa {emp}" if emp else "")

    linhas = [f"📂 {cc}: {money(v)}" for cc, v in sorted(centros.items(), key=lambda kv: kv[1], reverse=True)]
    return "📊 **Gastos por Centro de Custo**\n" + header + "\n\n" + "\n".join(linhas)

# ============================================================
# 🧱 Relatório consolidado p/ Dashboard/IA
# ============================================================
def gerar_relatorio_json(**params) -> Dict[str, Any]:
    pagar = sienge_get("bills", params)
    receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(x.get("amountValue") or x.get("amount") or 0) for x in receber)
    total_despesas = sum(float(x.get("amountValue") or x.get("amount") or 0) for x in pagar)
    lucro = total_receitas - total_despesas

    despesas_normalizadas = []
    for x in pagar:
        despesas_normalizadas.append({
            "data": x.get("issueDate") or x.get("dueDate"),
            "empresa": (x.get("enterprise") or {}).get("name") or x.get("enterpriseName"),
            "fornecedor": (x.get("supplier") or {}).get("name") or x.get("supplierName"),
            "obra": (x.get("constructionSite") or {}).get("name") or x.get("constructionSiteName"),
            "centro_custo": (x.get("costCenter") or {}).get("name") or x.get("costCenterName"),
            "conta_financeira": (x.get("financialAccount") or {}).get("name") or x.get("financialAccountName"),
            "status": x.get("status") or x.get("situation") or "-",
            "descricao": x.get("description") or x.get("history") or "-",
            "valor_total": float(x.get("amountValue") or x.get("amount") or 0),
        })

    return {
        "periodo": {
            "inicio": params.get("startDate") or periodo_padrao()[0],
            "fim": params.get("endDate") or periodo_padrao()[1],
            "enterpriseId": params.get("enterpriseId"),
        },
        "dre": {
            "receitas": total_receitas,
            "despesas": total_despesas,
            "lucro": lucro,
            "formatado": {
                "receitas": money(total_receitas),
                "despesas": money(total_despesas),
                "lucro": money(lucro),
            },
        },
        "todas_despesas": despesas_normalizadas,
    }
