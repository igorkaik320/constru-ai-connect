import requests
import logging
from base64 import b64encode
from functools import lru_cache

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
# 🧠 VERIFICAÇÃO DE SEGUNDA VIA
# ============================================================
@lru_cache(maxsize=200)
def boleto_existe(titulo_id: int, parcela_id: int) -> bool:
    """Verifica se existe segunda via real para essa parcela."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    try:
        r = requests.get(url, headers=json_headers, params=params, timeout=20)
        logging.info(f"🔎 Verificando boleto: {params} -> {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or []
            if results and results[0].get("urlReport"):
                return True
    except Exception as e:
        logging.error(f"Erro ao verificar boleto ({titulo_id}/{parcela_id}): {e}")
    return False

# ============================================================
# 🔍 BUSCAR BOLETOS POR CPF
# ============================================================
def buscar_boletos_por_cpf(cpf: str):
    """Busca apenas boletos realmente disponíveis para 2ª via."""
    cliente = buscar_cliente_por_cpf(cpf)
    if not cliente:
        return {"erro": "❌ Nenhum cliente encontrado com esse CPF."}

    nome = cliente.get("name")
    cid = cliente.get("id")
    logging.info(f"✅ Cliente encontrado: {nome} (ID {cid})")

    boletos = listar_boletos_por_cliente(cid)
    if not boletos:
        return {"erro": f"📭 Nenhum boleto encontrado para {nome}."}

    lista = []
    for b in boletos:
        titulo_id = b.get("id") or b.get("receivableBillId")
        valor = b.get("amount") or b.get("receivableBillValue") or 0.0
        desc = b.get("description") or b.get("documentNumber") or b.get("note") or "-"
        emissao = b.get("issueDate")
        quitado = b.get("payOffDate")

        if quitado:
            continue

        parcelas = listar_parcelas(titulo_id)
        if not parcelas:
            continue

        for p in parcelas:
            parcela_id = p.get("id")
            if not parcela_id:
                continue

            logging.info(f"🔎 Testando boleto título={titulo_id} parcela={parcela_id}")

            if not boleto_existe(titulo_id, parcela_id):
                logging.info(f"🔴 Boleto NÃO disponível -> Título {titulo_id}, Parcela {parcela_id}")
                continue

            logging.info(f"🟢 Boleto DISPONÍVEL -> Título {titulo_id}, Parcela {parcela_id}")

            lista.append({
                "titulo_id": titulo_id,
                "parcela_id": parcela_id,
                "descricao": desc,
                "valor": p.get("amount") or valor,
                "vencimento": p.get("dueDate") or emissao,
            })

    if not lista:
        return {"erro": f"📭 Nenhum boleto disponível para segunda via de {nome}."}

    return {"nome": nome, "boletos": lista}

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
