import requests
import logging
import json
from base64 import b64encode

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# === Auth básico ===
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# ==============================================================
# 🧾 Funções de integração de boletos
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

            # O retorno esperado é algo como:
            # {"results":[{"urlReport":"https://...","digitableNumber":"1049..."}]}
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

            # fallback se o formato não for o esperado
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
# 👥 Buscar boletos em aberto por cliente (CPF ou ID)
# ==============================================================

def listar_boletos_por_cliente(cliente_id: int):
    """
    Lista boletos (contas a receber) de um cliente no Sienge.
    Apenas boletos EM ABERTO.
    """
    url = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    logging.info(f"GET {url}")

    r = requests.get(url, headers=json_headers, timeout=30)
    if r.status_code != 200:
        logging.warning(f"Erro ao listar boletos: {r.text}")
        return []

    data = r.json()
    results = data.get("results") or data or []

    boletos_abertos = []
    for b in results:
        status = (b.get("status") or "").lower()
        # status possíveis: OPEN, PAID, CANCELLED, OVERDUE, etc.
        if status in ["open", "overdue", "em aberto", "pendente"]:
            boletos_abertos.append({
                "id": b.get("id"),
                "amount": b.get("amount"),
                "dueDate": b.get("dueDate"),
                "status": b.get("status"),
                "titleNumber": b.get("titleNumber"),
            })

    logging.info(f"🔎 {len(boletos_abertos)} boletos em aberto encontrados.")
    return boletos_abertos
