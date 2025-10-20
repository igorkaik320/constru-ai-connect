import requests
import logging
import json
from base64 import b64encode

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
# 🧾 FUNÇÕES DE BOLETO
# ==============================================================

def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

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
                        f"🔗 [Clique aqui para abrir o boleto]({link})\n"
                        f"💳 **Linha digitável:** `{linha_digitavel}`"
                    )
            return f"⚠️ Retorno inesperado da API:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        except Exception as e:
            logging.exception("Erro ao processar retorno JSON:")
            return f"❌ Erro ao processar retorno da API: {e}"

    logging.warning("Falha gerar link boleto (%s): %s", r.status_code, r.text)
    return f"❌ Erro ao gerar boleto ({r.status_code}). {r.text}"


def enviar_boleto_email(titulo_id: int, parcela_id: int) -> str:
    url = f"{BASE_URL}/payment-slip-notification"
    body = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    logging.info("POST %s -> data=%s", url, body)
    r = requests.post(url, headers=json_headers, json=body, timeout=30)
    logging.info("%s -> %s", url, r.status_code)

    if r.status_code == 200:
        return "📧 Boleto enviado por e-mail ao cliente com sucesso!"
    else:
        logging.warning("Falha ao enviar boleto (%s): %s", r.status_code, r.text)
        return f"❌ Erro ao enviar boleto ({r.status_code}). {r.text}"


# ==============================================================
# 🔍 FUNÇÃO PRINCIPAL — Buscar boletos por CPF
# ==============================================================

def buscar_boletos_por_cpf(cpf: str):
    """Busca boletos de um cliente pelo CPF, verificando cliente, unidade e obra."""
    from sienge.sienge_clientes import buscar_cliente_por_cpf  # ✅ import local

    cliente = buscar_cliente_por_cpf(cpf)
    if not cliente:
        return "❌ Cliente não encontrado com esse CPF."

    cliente_id = cliente.get("id")
    nome = cliente.get("name") or cliente.get("fullName", "Cliente")
    logging.info(f"✅ Cliente encontrado: {nome} (ID {cliente_id})")

    boletos = []

    # 1️⃣ — Boletos diretos
    url_cliente = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url_cliente, headers=json_headers, timeout=30)
    logging.info(f"GET {url_cliente} -> {r.status_code}")
    if r.status_code == 200:
        boletos += r.json().get("results") or []

    # 2️⃣ — Boletos por unidade (unitId)
    if not boletos:
        url_units = f"{BASE_URL}/units?customerId={cliente_id}"
        r2 = requests.get(url_units, headers=json_headers, timeout=30)
        logging.info(f"GET {url_units} -> {r2.status_code}")
        if r2.status_code == 200:
            unidades = r2.json().get("results") or []
            for u in unidades:
                uid = u.get("id")
                r3 = requests.get(
                    f"{BASE_URL}/accounts-receivable/receivable-bills?unitId={uid}",
                    headers=json_headers,
                    timeout=30,
                )
                if r3.status_code == 200:
                    boletos += r3.json().get("results") or []

    # 3️⃣ — Boletos por obra (buildingId)
    if not boletos:
        url_buildings = f"{BASE_URL}/buildings?customerId={cliente_id}"
        r4 = requests.get(url_buildings, headers=json_headers, timeout=30)
        if r4.status_code == 200:
            obras = r4.json().get("results") or []
            for o in obras:
                oid = o.get("id")
                r5 = requests.get(
                    f"{BASE_URL}/accounts-receivable/receivable-bills?buildingId={oid}",
                    headers=json_headers,
                    timeout=30,
                )
                if r5.status_code == 200:
                    boletos += r5.json().get("results") or []

    # 4️⃣ — Monta o texto de resposta
    if not boletos:
        return f"📭 Nenhum boleto encontrado para o cliente **{nome}**."

    texto = [f"📋 Boletos encontrados para **{nome}:**\n"]

    for b in boletos:
        # Extrai campos de forma segura
        titulo_id = b.get("id") or b.get("billReceivableId") or "-"
        desc = (
            b.get("description")
            or (b.get("billReceivable") or {}).get("description")
            or "Sem descrição"
        )
        amount = (
            b.get("amount")
            or (b.get("billReceivable") or {}).get("amount")
            or (b.get("installment") or {}).get("amount")
            or 0.0
        )
        due_date = (
            b.get("dueDate")
            or (b.get("installment") or {}).get("dueDate")
            or "-"
        )

        texto.append(
            f"💳 **Título {titulo_id}** — {desc}\n"
            f"💰 Valor: R$ {float(amount):,.2f}\n"
            f"📅 Vencimento: {due_date}\n"
        )

    return "\n".join(texto)
