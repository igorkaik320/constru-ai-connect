# sienge/sienge_financeiro.py
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
from base64 import b64encode

logging.warning("🚀 Rodando versão 5.1 do sienge_financeiro.py (autenticação + extração completa de pagar/receber + rateios/obras/impostos)")

# ============================================================
# 🔐 AUTENTICAÇÃO (Basic) E CONFIGURAÇÃO BASE
# ============================================================
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ============================================================
# 🗓️ Datas padrão (últimos 12 meses)
# ============================================================
def periodo_padrao():
    fim = datetime.now().date()
    inicio = fim - timedelta(days=365)
    return inicio.isoformat(), fim.isoformat()

# ============================================================
# 🔄 Função GET segura
# ============================================================
def _safe_get(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("results") if isinstance(data, dict) else data
        logging.warning(f"⚠️ GET {url} -> {r.status_code}: {r.text[:200]}")
        return []
    except Exception as e:
        logging.exception(f"❌ Erro GET {url}: {e}")
        return []

# ============================================================
# 🔍 Listagem completa (pagar + receber) com detalhes
# ============================================================
def listar_titulos_completos(startDate=None, endDate=None, enterpriseId=None, incluir_receber=True):
    """Busca títulos a pagar e a receber + parcelas + rateios + obras + impostos."""
    if not startDate or not endDate:
        startDate, endDate = periodo_padrao()

    params = {"startDate": startDate, "endDate": endDate, "limit": 200}
    if enterpriseId:
        # No /bills, a empresa é o debtorId (empresa devida no Sienge)
        params["debtorId"] = enterpriseId

    linhas = []

    # --------------------------
    # 💸 Contas a Pagar (/bills)
    # --------------------------
    bills_url = f"{BASE_URL}/bills"
    pagar = _safe_get(bills_url, params=params)
    logging.info(f"📄 Títulos a pagar: {len(pagar)}")

    for b in pagar:
        try:
            bill_id = b.get("id")
            empresa = b.get("debtorId")
            fornecedor = b.get("creditorId")
            doc_num = b.get("documentNumber")
            doc_tipo = b.get("documentIdentificationId")
            emissao = b.get("issueDate")
            origem = b.get("originId")
            status = b.get("status")
            notas = b.get("notes", "")

            # Valor total do título (nota): totalInvoiceAmount
            valor_nota = float(b.get("totalInvoiceAmount") or 0.0)

            # Parcelas
            parcelas = _safe_get(f"{bills_url}/{bill_id}/installments")
            soma_parcelas = sum(float(p.get("amount", 0) or 0) for p in parcelas)
            vencs = ", ".join([p.get("dueDate") for p in parcelas if p.get("dueDate")]) or None
            sits = ", ".join([p.get("situation") for p in parcelas if p.get("situation")]) or None

            # Rateios Financeiros (centro de custo / plano)
            aprop = _safe_get(f"{bills_url}/{bill_id}/budget-categories")
            centros = [str(a.get("costCenterId")) for a in aprop if a.get("costCenterId") is not None]
            planos = [a.get("paymentCategoriesId") for a in aprop if a.get("paymentCategoriesId")]

            # Obras
            obras = _safe_get(f"{bills_url}/{bill_id}/buildings-cost")
            nomes_obras = [o.get("buildingName") for o in obras if o.get("buildingName")]

            # Departamentos
            deps = _safe_get(f"{bills_url}/{bill_id}/departments-cost")
            nomes_deps = [d.get("departmentName") for d in deps if d.get("departmentName")]

            # Impostos
            impostos = _safe_get(f"{bills_url}/{bill_id}/taxes")
            total_impostos = sum(float(t.get("amount", 0) or 0) for t in impostos)

            linhas.append({
                "tipo": "Pagar",
                "id": bill_id,
                "empresa": empresa,
                "fornecedor": fornecedor,
                "documento": doc_num,
                "tipo_doc": doc_tipo,
                "emissao": emissao,
                "vencimentos": vencs,
                "situacoes": sits,
                "valor_total": soma_parcelas if soma_parcelas > 0 else valor_nota,
                "impostos": total_impostos,
                "origem": origem,
                "status": status,
                "obra": ", ".join(nomes_obras) if nomes_obras else None,
                "centro_custo": ", ".join(centros) if centros else None,
                "plano_financeiro": ", ".join(planos) if planos else None,
                "departamento": ", ".join(nomes_deps) if nomes_deps else None,
                "notas": notas,
            })
        except Exception as e:
            logging.warning(f"⚠️ Falha ao processar título pagar {b.get('id')}: {e}")

    # --------------------------
    # 💰 Contas a Receber
    # --------------------------
    if incluir_receber:
        rec_url = f"{BASE_URL}/accounts-receivable/receivable-bills"
        rec = _safe_get(rec_url, params=params)
        logging.info(f"📄 Títulos a receber: {len(rec)}")

        for r in rec:
            try:
                # campos observados no seu ambiente: receivableBillValue, issueDate, documentNumber etc.
                valor = float(r.get("receivableBillValue") or r.get("totalInvoiceAmount") or 0.0)
                linhas.append({
                    "tipo": "Receber",
                    "id": r.get("receivableBillId") or r.get("id"),
                    "empresa": r.get("companyId") or r.get("debtorId"),
                    "fornecedor": r.get("customerId"),   # aqui é cliente (quem vai pagar)
                    "documento": r.get("documentNumber"),
                    "tipo_doc": r.get("documentId") or r.get("documentIdentificationId"),
                    "emissao": r.get("issueDate"),
                    "valor_total": valor,
                    "origem": r.get("originId"),
                    "status": r.get("status"),
                    "notas": r.get("note", ""),
                    "obra": None,
                    "centro_custo": None,
                    "plano_financeiro": None,
                    "departamento": None,
                    "impostos": None,
                    "vencimentos": None,
                    "situacoes": None,
                })
            except Exception as e:
                logging.warning(f"⚠️ Falha ao processar título receber {r.get('id')}: {e}")

    return pd.DataFrame(linhas)

# ============================================================
# 💰 Resumo Financeiro (string para chat)
# ============================================================
def resumo_financeiro(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    df = listar_titulos_completos(
        startDate=params.get("startDate"),
        endDate=params.get("endDate"),
        enterpriseId=params.get("enterpriseId"),
        incluir_receber=True,
    )
    if df.empty:
        inicio, fim = params.get("startDate"), params.get("endDate")
        return f"📊 **Resumo Financeiro (Período {inicio} a {fim})**\n\nNenhum dado encontrado."

    total_receitas = df.loc[df["tipo"] == "Receber", "valor_total"].sum()
    total_despesas = df.loc[df["tipo"] == "Pagar", "valor_total"].sum()
    lucro = total_receitas - total_despesas

    return (
        f"📊 **Resumo Financeiro (Período {params.get('startDate')} a {params.get('endDate')})**\n\n"
        f"💵 Receitas: R$ {total_receitas:,.2f}\n"
        f"💸 Despesas: R$ {total_despesas:,.2f}\n"
        f"📈 Resultado: R$ {lucro:,.2f}"
    )

# ============================================================
# 🏗️ Gastos por Obra (string para chat)
# ============================================================
def gastos_por_obra(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    df = listar_titulos_completos(
        startDate=params.get("startDate"),
        endDate=params.get("endDate"),
        enterpriseId=params.get("enterpriseId"),
        incluir_receber=False,
    )
    df = df[df["tipo"] == "Pagar"]
    if df.empty:
        return "📭 Nenhum gasto encontrado."

    # Normaliza None
    df["obra"] = df["obra"].fillna("N/A")
    agrupado = df.groupby("obra")["valor_total"].sum().sort_values(ascending=False)
    total = float(agrupado.sum()) or 1.0

    linhas = [f"📊 **Top Obras por Gastos ({params.get('startDate')} a {params.get('endDate')})**\n"]
    for i, (obra, valor) in enumerate(agrupado.items()):
        if i >= 10:
            linhas.append(f"...(+{len(agrupado) - 10} outras obras)")
            break
        perc = (valor / total) * 100
        nome = (obra or "N/A")
        linhas.append(f"🏗️ **{nome[:60]}** — R$ {valor:,.2f} ({perc:.1f}%)")

    return "\n".join(linhas)

# ============================================================
# 📂 Gastos por Centro de Custo (string para chat)
# ============================================================
def gastos_por_centro_custo(params=None, **kwargs):
    if not params:
        params = kwargs or {}
    df = listar_titulos_completos(
        startDate=params.get("startDate"),
        endDate=params.get("endDate"),
        enterpriseId=params.get("enterpriseId"),
        incluir_receber=False,
    )
    df = df[df["tipo"] == "Pagar"]
    if df.empty:
        return "📭 Nenhum dado encontrado."

    df["centro_custo"] = df["centro_custo"].fillna("N/A")
    agrupado = df.groupby("centro_custo")["valor_total"].sum().sort_values(ascending=False)

    linhas = ["📂 **Top Centros de Custo**\n"]
    for i, (cc, valor) in enumerate(agrupado.items()):
        if i >= 10:
            linhas.append(f"...(+{len(agrupado) - 10} outros)")
            break
        linhas.append(f"🏢 {cc} — R$ {valor:,.2f}")
    return "\n".join(linhas)

# ============================================================
# 🧮 Relatório JSON (para dashboard/IA)
# ============================================================
def gerar_relatorio_json(params=None, **kwargs):
    if not params:
        params = kwargs or {}

    df = listar_titulos_completos(
        startDate=params.get("startDate"),
        endDate=params.get("endDate"),
        enterpriseId=params.get("enterpriseId"),
        incluir_receber=True,
    )

    if df.empty:
        return {"todas_despesas": [], "dre": {"formatado": {"receitas": "R$ 0,00", "despesas": "R$ 0,00", "lucro": "R$ 0,00"}}}

    total_receitas = df.loc[df["tipo"] == "Receber", "valor_total"].sum()
    total_despesas = df.loc[df["tipo"] == "Pagar", "valor_total"].sum()
    lucro = total_receitas - total_despesas

    dre_formatado = {
        "receitas": f"R$ {total_receitas:,.2f}",
        "despesas": f"R$ {total_despesas:,.2f}",
        "lucro": f"R$ {lucro:,.2f}",
    }

    # Para o dashboard antigo, mantemos nomes esperados nas colunas principais:
    df_export = df.rename(columns={
        "obra": "obra",
        "centro_custo": "centro_custo",
        "fornecedor": "fornecedor",
        "empresa": "empresa",
        "status": "status",
        "valor_total": "valor_total",
    })

    return {
        "todas_despesas": df_export.to_dict(orient="records"),
        "dre": {"formatado": dre_formatado},
    }
