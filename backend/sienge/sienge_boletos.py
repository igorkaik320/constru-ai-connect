import requests
import logging
from base64 import b64encode

# 🚀 Identificação da versão atual
logging.warning("🚀 Rodando versão 1.7 do sienge_boletos.py (correção installmentId e log detalhado)")

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
# 👤 CLIENTE
# ============================================================
def buscar_cliente_por_cpf(cpf: str):
    """Busca cliente no Sienge pelo CPF."""
    url = f"{BASE_URL}/customers?cpf={cpf}"
    logging.info(f"GET {url}")
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"{url} -> {r.status_code}")

    if r.status_code != 200:
        logging.warning("Erro ao buscar cliente: %s", r.text)
        return None

    data = r.json()
    results = data.get("results") or data
    if isinstance(results, list) and len(results) > 0:
        return results[0]
    return None


# ============================================================
# 🧾 BOLETOS / TÍTULOS
# ============================================================
def listar_boletos_por_cliente(cliente_id: int):
    """Lista boletos/títulos vinculados a um cliente."""
    url = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return []
    return r.json().get("results") or []


def listar_parcelas(titulo_id: int):
    """Lista parcelas de um título."""
    if not titulo_id:
        return []
    url = f"{BASE_URL}/accounts-receivable/receivable-bills/{titulo_id}/installments"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return []
    return r.json().get("results") or []


# ============================================================
# 🧠 VERIFICAÇÃO DE SEGUNDA VIA (LOG DETALHADO)
# ============================================================
def boleto_existe(titulo_id: int, parcela_id: int) -> bool:
    """Verifica se existe segunda via real para essa parcela."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    try:
        r = requests.get(url, headers=json_headers, params=params, timeout=20)
        logging.info(f"🔎 Verificando boleto: {params} -> {r.status_code}")
        logging.info(f"Resposta: {r.text[:400]}")

        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or []
            if results and results[0].get("urlReport"):
                logging.info(f"🟢 Segunda via encontrada -> {results[0].get('urlReport')}")
                return True

        logging.info("🔴 Segunda via não encontrada.")
    except Exception as e:
        logging.error(f"Erro ao verificar boleto ({titulo_id}/{parcela_id}): {e}")
    return False


# ============================================================
# 🔍 BUSCAR BOLETOS POR CPF (CORRIGIDO COM installmentId)
# ============================================================
def buscar_boletos_por_cpf(cpf: str):
    """Busca apenas boletos realmente disponíveis para 2ª via (com logs detalhados)."""
    cliente = buscar_cliente_por_cpf(cpf)
    if not cliente:
        return {"erro": "❌ Nenhum cliente encontrado com esse CPF."}

    nome = cliente.get("name")
    cid = cliente.get("id")
    logging.info(f"✅ Cliente encontrado: {nome} (ID {cid})")

    boletos = listar_boletos_por_cliente(cid)
    logging.info(f"📊 Total de títulos retornados: {len(boletos)}")

    if not boletos:
        return {"erro": f"📭 Nenhum boleto encontrado para {nome}."}

    lista = []
    for b in boletos:
        titulo_id = b.get("id") or b.get("receivableBillId")
        valor = b.get("amount") or b.get("receivableBillValue") or 0.0
        desc = b.get("description") or b.get("documentNumber") or b.get("note") or "-"
        emissao = b.get("issueDate")
        quitado = b.get("payOffDate")

        logging.info(f"🧾 Título {titulo_id} | Valor {valor} | Descrição: {desc}")

        if quitado:
            logging.info(f"⏭️ Ignorando título {titulo_id} (já quitado)")
            continue

        parcelas = listar_parcelas(titulo_id)
        logging.info(f"📦 Parcelas do título {titulo_id}: {len(parcelas)}")

        if not parcelas:
            continue

        for p in parcelas:
            logging.info(f"🧩 Parcela -> {p}")

            # ✅ Correção: usa installmentId se o campo id não existir
            parcela_id = p.get("id") or p.get("installmentId")
            if not parcela_id:
                logging.info("⚠️ Parcela sem ID, ignorada")
                continue

            logging.info(f"🔍 Testando boleto título={titulo_id}, parcela={parcela_id}, valor={p.get('balanceDue')}")

            existe = boleto_existe(titulo_id, parcela_id)
            logging.info(f"Resultado da verificação -> {'🟢 Existe' if existe else '🔴 Não existe'}")

            if not existe:
                continue

            lista.append({
                "titulo_id": titulo_id,
                "parcela_id": parcela_id,
                "descricao": desc,
                "valor": p.get("balanceDue") or valor,
                "vencimento": p.get("dueDate") or emissao,
            })

    if not lista:
        return {"erro": f"📭 Nenhum boleto disponível para segunda via de {nome}."}

    return {
        "nome": nome,
        "boletos": lista
    }


# ============================================================
# 🔗 GERAR LINK DO BOLETO (2ª VIA)
# ============================================================
def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    """Gera link da segunda via do boleto."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    logging.info(f"GET {url} -> params={params}")
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info(f"{url} -> {r.status_code}")
    logging.info(f"Resposta: {r.text[:400]}")

    if r.status_code == 200:
        try:
            data = r.json()
            results = data.get("results") or []
            if results and isinstance(results, list):
                result = results[0]
                link = result.get("urlReport")
                linha_digitavel = result.get("digitableNumber")

                if link:
                    logging.info(f"🟢 Link do boleto gerado: {link}")
                    return (
                        f"📄 **Segunda via gerada com sucesso!**\n"
                        f"🔗 [Clique aqui para abrir o boleto]({link})\n"
                        f"💳 **Linha digitável:** `{linha_digitavel}`"
                    )
        except Exception as e:
            logging.exception("Erro ao processar resposta do boleto:")
            return f"❌ Erro ao processar boleto: {e}"

    return f"❌ Erro ao gerar boleto ({r.status_code})."
