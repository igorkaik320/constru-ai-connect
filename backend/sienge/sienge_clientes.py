import requests
import logging
import json
from base64 import b64encode
from sienge.sienge_clientes import buscar_cliente_por_cpf

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Auth básico
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ==============================================================
# 🧾 FUNÇÕES DE INTEGRAÇÃO DE BOLETOS
# ==============================================================

def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    """Gera link de segunda via do boleto no Sienge"""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {
        "billReceivableId": titulo_id,
        "installmentId": parcela_id,
    }

    logging.info("GET %s -> params=%s", url, params)
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info("%s -> %s", url, r.status_code)

    if r.status_code == 200:
        try:
            data = r.json()
            results = data.get("results") or data.get("data") or []
            if results and isinstance(results, list):
                result = results[0]
                link = result.get("urlReport")
                linha_digitavel = result.get("digitableNumber")

                if link:
                    return (
                        f"📄 **Segunda via gerada com sucesso!**\n\n"
                        f"🔗 [Clique aqui para baixar o boleto]({link})\n"
                        f"💳 **Linha digitável:** `{linha_digitavel}`"
                    )
            return f"⚠️ Retorno inesperado da API:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        except Exception as e:
            logging.exception("Erro ao processar retorno JSON:")
            return f"❌ Erro ao processar retorno da API: {e}"

    logging.warning("Falha gerar link boleto (%s): %s", r.status_code, r.text)
    return f"❌ Erro ao gerar boleto ({r.status_code}). {r.text}"


def enviar_boleto_email(titulo_id: int, parcela_id: int) -> str:
    """Envia boleto de segunda via por e-mail ao cliente"""
    url = f"{BASE_URL}/payment-slip-notification"
    body = {
        "billReceivableId": titulo_id,
        "installmentId": parcela_id,
    }

    logging.info("POST %s -> data=%s", url, body)
    r = requests.post(url, headers=json_headers, json=body, timeout=30)
    logging.info("%s -> %s", url, r.status_code)

    if r.status_code == 200:
        return "📧 Boleto enviado por e-mail ao cliente com sucesso!"
    else:
        logging.warning("Falha ao enviar boleto (%s): %s", r.status_code, r.text)
        return f"❌ Erro ao enviar boleto ({r.status_code}). {r.text}"


# ==============================================================
# 🔍 FUNÇÕES DE BUSCA POR CPF
# ==============================================================

def buscar_boletos_por_cpf(cpf: str):
    """
    Busca boletos vinculados ao CPF do cliente (direto, por unidade ou por obra).
    """
    cliente = buscar_cliente_por_cpf(cpf)
    if not cliente:
        return "❌ Cliente não encontrado com esse CPF."

    cliente_id = cliente.get("id")
    nome = cliente.get("name")
    logging.info(f"✅ Cliente encontrado: {nome} (ID: {cliente_id})")

    # 1️⃣ Busca boletos diretos pelo cliente
    url_cliente = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url_cliente, headers=json_headers, timeout=30)
    logging.info(f"GET {url_cliente} -> {r.status_code}")

    boletos = []
    if r.status_code == 200:
        data = r.json()
        boletos = data.get("results") or []

    # 2️⃣ Se não tiver boletos, tenta buscar pelas unidades (unitId)
    if not boletos:
        unidades_url = f"{BASE_URL}/units?customerId={cliente_id}"
        r2 = requests.get(unidades_url, headers=json_headers, timeout=30)
        logging.info(f"GET {unidades_url} -> {r2.status_code}")
        if r2.status_code == 200:
            unidades = r2.json().get("results") or []
            for u in unidades:
                uid = u.get("id")
                url_unidade = f"{BASE_URL}/accounts-receivable/receivable-bills?unitId={uid}"
                r3 = requests.get(url_unidade, headers=json_headers, timeout=30)
                logging.info(f"GET {url_unidade} -> {r3.status_code}")
                if r3.status_code == 200:
                    boletos += r3.json().get("results") or []

    # 3️⃣ Se ainda não tiver, tenta pelas obras (buildingId)
    if not boletos:
        obras_url = f"{BASE_URL}/buildings?customerId={cliente_id}"
        r4 = requests.get(obras_url, headers=json_headers, timeout=30)
        logging.info(f"GET {obras_url} -> {r4.status_code}")
        if r4.status_code == 200:
            obras = r4.json().get("results") or []
            for o in obras:
                oid = o.get("id")
                url_obra = f"{BASE_URL}/accounts-receivable/receivable-bills?buildingId={oid}"
                r5 = requests.get(url_obra, headers=json_headers, timeout=30)
                logging.info(f"GET {url_obra} -> {r5.status_code}")
                if r5.status_code == 200:
                    boletos += r5.json().get("results") or []

    # 4️⃣ Formata o resultado
    if not boletos:
        return f"📭 Nenhum boleto encontrado para o cliente **{nome}**."

    texto = [f"📋 Boletos encontrados para **{nome}:**\n"]
    for b in boletos:
        texto.append(
            f"💳 Título {b.get('id')} — {b.get('description', '-')}\n"
            f"💰 Valor: R$ {b.get('amount', 0):,.2f}\n"
            f"📅 Vencimento: {b.get('dueDate', '-')}\n"
            f"🔢 Parcela(s): {b.get('installmentsCount', '-')}\n"
        )

    return "\n".join(texto)
