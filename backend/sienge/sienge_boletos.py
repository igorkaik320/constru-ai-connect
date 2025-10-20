import requests
import logging
import os
import json

# 🔐 Variáveis de ambiente (substitua pelas suas se preferir fixas)
BASE_URL = "https://api.sienge.com.br/cctcontrol/public/api/v1"
SIENGE_USER = os.getenv("SIENGE_USER")
SIENGE_PASSWORD = os.getenv("SIENGE_PASSWORD")

json_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
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

            # O retorno vem em formato { "results": [ { "urlReport": "...", "digitableNumber": "..." } ] }
            results = data.get("results") or data.get("data") or []
            if results and isinstance(results, list):
                result = results[0]
                link = result.get("urlReport")
                linha_digitavel = result.get("digitableNumber")

                if link:
                    return f"{link} (Linha digitável: {linha_digitavel})"

            # fallback
            return json.dumps(data, ensure_ascii=False)

        except Exception as e:
            logging.exception("Erro ao processar retorno JSON:")
            return f"Erro ao processar retorno da API: {e}"

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
