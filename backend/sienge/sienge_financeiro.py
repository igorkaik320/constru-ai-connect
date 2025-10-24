import requests
import logging
import time
import json
from base64 import b64encode
from datetime import datetime, timedelta

logging.warning("🚀 Rodando versão 5.3.1 do sienge_financeiro.py (com filtro de empresa e apropriação financeira)")

# ============================================================
# 🔐 Configurações de autenticação
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
# Cache simples
# ============================================================
_cache = {}

def get_cached(url):
    if not url:
        return "N/A"
    if url in _cache:
        return _cache[url]
    try:
        r = requests.get(url, headers=json_headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            name = data.get("name") or data.get("description") or data.get("fantasyName") or "N/A"
            _cache[url] = name
            return name
    except Exception as e:
        logging.error(f"⚠️ Erro ao buscar {url}: {e}")
    _cache[url] = "N/A"
    return "N/A"

# ============================================================
# 🧾 Apropriação Financeira (Plano de Contas)
# ============================================================
def get_apropriacoes_financeiras(bill_id: int):
    try:
        url = f"{BASE_URL}/bills/{bill_id}/budget-categories"
        logging.info(f"➡️ GET {url} (apropriações financeiras)")
        r = requests.get(url, headers=json_headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            aprop_detalhes = []
            for item in results:
                categoria = item.get("paymentCategoriesId", "N/A")
                percentual = item.get("percentage", 0)
                centro = "N/A"
                for link in item.get("links", []):
                    if link.get("rel") == "debtor":
                        centro = get_cached(link.get("href"))
                        break
                aprop_detalhes.append({
                    "categoria": categoria,
                    "percentual": percentual,
                    "debtor": centro,
                })
            return aprop_detalhes
        elif r.status_code == 404:
            return []
        else:
            logging.error(f"❌ Erro {r.status_code} ao buscar apropriações: {r.text[:200]}")
            return []
    except Exception as e:
        logging.exception(f"⚠️ Erro ao buscar apropriações financeiras do bill {bill_id}: {e}")
        return []

# ============================================================
# Datas padrão
# ============================================================
def periodo_padrao():
    fim = datetime.now().date()
    inicio = fim - timedelta(days=365)
    return inicio.isoformat(), fim.isoformat()

# ============================================================
# Função base de requisição (com retry e filtro empresa)
# ============================================================
def sienge_get(endpoint, params=None, max_retries=3):
    url = f"{BASE_URL}/{endpoint}"
    if params is None:
        params = {}

    # 🧭 Ajusta filtros padrão
    if "startDate" not in params:
        inicio, fim = periodo_padrao()
        params["startDate"], params["endDate"] = inicio, fim

    # ✅ Novo: adiciona filtro de empresa se existir
    if "enterpriseId" not in params:
        if "empresa" in params:
            params["enterpriseId"] = params["empresa"]
        elif "empresa_id" in params:
            params["enterpriseId"] = params["empresa_id"]
        elif "companyId" in params:
            params["enterpriseId"] = params["companyId"]

    for tentativa in range(1, max_retries + 1):
        try:
            logging.info(f"➡️ GET {url} -> {params}")
            r = requests.get(url, headers=json_headers, params=params, timeout=40)
            logging.info(f"📦 Status: {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                results = data.get("results") or data
                return results

            elif r.status_code == 429:
                espera = 3 * tentativa
                logging.warning(f"⏳ 429 Too Many Requests – aguardando {espera}s...")
                time.sleep(espera)

            elif r.status_code >= 500:
                logging.warning(f"⚠️ Erro {r.status_code} no servidor Sienge. Retentando...")
                time.sleep(2 * tentativa)

            else:
                logging.error(f"❌ Erro {r.status_code}: {r.text[:400]}")
                break

        except Exception as e:
            logging.exception(f"❌ Erro em {endpoint}: {e}")
            time.sleep(2)
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

    empresa = params.get("enterpriseId", "Todas")
    return (
        f"📊 **Resumo Financeiro — Empresa {empresa} ({params.get('startDate')} → {params.get('endDate')})**\n\n"
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
        obra = "N/A"
        for link in item.get("links", []):
            if link["rel"] == "buildingsCost":
                obra = get_cached(link["href"])
                break
        valor = float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0)
        obras[obra] = obras.get(obra, 0) + valor

    obras = dict(sorted(obras.items(), key=lambda x: x[1], reverse=True))
    total = sum(obras.values())
    linhas = []
    for i, (obra, valor) in enumerate(obras.items()):
        if i >= 10:
            linhas.append(f"...(+{len(obras)-10} outras obras)")
            break
        percentual = (valor / total * 100) if total else 0
        linhas.append(f"🏗️ **{obra[:60]}** — R$ {valor:,.2f} ({percentual:.1f}%)")

    return f"📊 **Top Obras ({params.get('startDate')} → {params.get('endDate')})**\n\n" + "\n".join(linhas)

# ============================================================
# 📂 Gastos por Centro de Custo
# ============================================================
def gastos_por_centro_custo(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    dados = sienge_get("bills", params)
    centros = {}

    for item in dados:
        centro = "N/A"
        for link in item.get("links", []):
            if link["rel"] == "departmentsCost":
                centro = get_cached(link["href"])
                break
        valor = float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0)
        centros[centro] = centros.get(centro, 0) + valor

    centros = dict(sorted(centros.items(), key=lambda x: x[1], reverse=True))
    linhas = [f"📂 {cc}: R$ {valor:,.2f}" for cc, valor in list(centros.items())[:10]]
    return "📊 **Top Centros de Custo**\n\n" + "\n".join(linhas)

# ============================================================
# 🧮 Relatório JSON (para IA e dashboards)
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
        links = {l["rel"]: l["href"] for l in item.get("links", [])}
        empresa = get_cached(links.get("company", "")) if "company" in links else "N/A"
        fornecedor = get_cached(links.get("creditor", "")) if "creditor" in links else "N/A"
        centro = get_cached(links.get("departmentsCost", "")) if "departmentsCost" in links else "N/A"
        obra = get_cached(links.get("buildingsCost", "")) if "buildingsCost" in links else "N/A"

        descricao = item.get("notes") or item.get("description") or ""
        if not isinstance(descricao, str):
            descricao = str(descricao)
        descricao = descricao[:200]

        bill_id = item.get("id")
        aprop_fin = get_apropriacoes_financeiras(bill_id) if bill_id else []

        todas_despesas.append({
            "empresa": empresa,
            "fornecedor": fornecedor,
            "centro_custo": centro,
            "obra": obra,
            "status": item.get("status", "N/A"),
            "valor_total": float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0),
            "data_vencimento": item.get("dueDate", "N/A"),
            "descricao": descricao,
            "documento": item.get("documentNumber", ""),
            "tipo_lancamento": item.get("originId", ""),
            "apropriacoes_financeiras": aprop_fin,
        })

    return {
        "todas_despesas": todas_despesas,
        "dre": {"formatado": dre_formatado},
        "total_registros": len(todas_despesas)
    }
