# sienge/sienge_boletos.py
import os
import requests
import logging

# 🔹 Carrega as variáveis do ambiente (Render ou .env local)
SIENGE_URL = os.getenv("SIENGE_URL")
SIENGE_USER = os.getenv("SIENGE_USER")
SIENGE_PASSWORD = os.getenv("SIENGE_PASSWORD")

# ===== Função para gerar link do boleto =====
def gerar_link_boleto(titulo_id: int, parcela_id: int):
    """
    Gera o link de boleto de segunda via (GET /payment-slip-notification)
    Retorna link e linha digitável do boleto.
    """
    if not SIENGE_URL:
        logging.error("❌ Variável SIENGE_URL não configurada.")
        return "❌ Erro interno: URL base do Sienge não configurada."

    url = f"{SIENGE_URL}/payment-slip-notification"
    params = {
        "titleId": titulo_id,
        "installmentNumber": parcela_id
    }

    try:
        resp = requests.get(url, params=params, auth=(SIENGE_USER, SIENGE_PASSWORD))
        logging.info(f"gerar_link_boleto: {url} -> {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            link = data.get("link")
            barcode = data.get("barCode")

            if link:
                return (
                    f"💳 Link do boleto (válido por 5 min): {link}\n"
                    f"🏦 Linha Digitável: {barcode or '-'}"
                )
            return "❌ Nenhum link retornado pela API do Sienge."

        logging.warning(f"Falha gerar link boleto ({resp.status_code}): {resp.text}")
        return f"❌ Falha ao gerar link do boleto ({resp.status_code})."

    except Exception as e:
        logging.exception("Erro ao gerar link do boleto:")
        return f"❌ Erro ao gerar link do boleto: {e}"


# ===== Função para enviar boleto por e-mail =====
def enviar_boleto_email(titulo_id: int, parcela_id: int):
    """
    Envia o boleto de segunda via por e-mail (POST /payment-slip-notification)
    O e-mail é enviado ao cliente vinculado ao título.
    """
    if not SIENGE_URL:
        logging.error("❌ Variável SIENGE_URL não configurada.")
        return "❌ Erro interno: URL base do Sienge não configurada."

    url = f"{SIENGE_URL}/payment-slip-notification"
    body = {
        "titleId": titulo_id,
        "installmentNumber": parcela_id
    }

    try:
        resp = requests.post(url, json=body, auth=(SIENGE_USER, SIENGE_PASSWORD))
        logging.info(f"enviar_boleto_email: {url} -> {resp.status_code}")

        if resp.status_code == 200:
            return "📧 Boleto de segunda via enviado com sucesso por e-mail!"
        elif resp.status_code == 404:
            return "❌ Título ou parcela não encontrados no Sienge."
        elif resp.status_code == 400:
            return "⚠️ Requisição inválida. Verifique os parâmetros enviados."

        logging.warning(f"Falha enviar boleto ({resp.status_code}): {resp.text}")
        return f"❌ Falha ao enviar boleto ({resp.status_code})."

    except Exception as e:
        logging.exception("Erro ao enviar boleto:")
        return f"❌ Erro ao enviar boleto: {e}"
