from typing import Dict, List, Any
import logging
import requests

# Imports das demais camadas do seu projeto
from sienge.sienge_clientes import buscar_cliente_por_cpf
from sienge.sienge_parcelas import listar_parcelas
from sienge.sienge_titulos import listar_boletos_por_cliente, boleto_existe

__all__ = ["buscar_boletos_por_cpf", "gerar_link_boleto"]

# ---------------------------------------------------------------------------
# Busca boletos disponíveis por CPF (mantida exatamente como você enviou)
# ---------------------------------------------------------------------------

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

            # 🔍 Log detalhado da verificação
            logging.info(f"🔎 Testando boleto título={titulo_id} parcela={parcela_id}")

            # ✅ Verifica se o boleto realmente existe
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

    return {
        "nome": nome,
        "boletos": lista
    }

# ---------------------------------------------------------------------------
# Geração do link de segunda via do boleto
# ---------------------------------------------------------------------------

def gerar_link_boleto(titulo_id: int | str, parcela_id: int | str) -> str:
    """
    Gera o link de 2ª via para um título/parcela no endpoint público do Sienge CCT Control.

    Retorna uma string pronta para exibir no chat:
      - "🔗 Segunda via disponível: <URL>"
      - ou uma mensagem de erro amigável.
    """
    try:
        # Garante que conseguimos logar corretamente os IDs
        try:
            t_id = int(titulo_id)
            p_id = int(parcela_id)
        except Exception:
            # Se não der para converter, segue com o valor original,
            # mas registra o alerta.
            logging.warning(f"IDs não numéricos recebidos: titulo_id={titulo_id}, parcela_id={parcela_id}")
            t_id = titulo_id
            p_id = parcela_id

        url = (
            "https://api.sienge.com.br/cctcontrol/public/api/v1/"
            f"accounts-receivable/receivable-bills/{t_id}/installments/{p_id}/link"
        )
        logging.info(f"🔗 Gerando link do boleto: {url}")

        # Timeout curto para evitar travar no Render se a API não responder
        resp = requests.get(url, timeout=15)

        if resp.status_code != 200:
            logging.error(f"❌ Erro ao gerar link ({resp.status_code}): {resp.text}")
            return f"❌ Erro ao gerar link do boleto (status {resp.status_code})."

        # Tenta extrair o link de diversos formatos possíveis
        link = None
        data: Any
        try:
            data = resp.json()
            link = data.get("url") or data.get("link") or data.get("href")
        except Exception:
            # Caso venha texto puro
            data = resp.text

        if not link:
            # Tenta heurística: procurar um http(s) na string de resposta
            if isinstance(data, str):
                import re as _re
                m = _re.search(r"https?://\S+", data)
                if m:
                    link = m.group(0)

        if link:
            logging.info(f"🟢 Link do boleto gerado com sucesso: {link}")
            return f"🔗 Segunda via disponível: {link}"

        logging.warning(f"⚠️ Resposta sem link. Payload: {data}")
        return "⚠️ Não foi possível obter o link do boleto."

    except requests.Timeout:
        logging.exception("Tempo esgotado ao chamar o endpoint de link do boleto.")
        return "⏱️ Tempo esgotado ao gerar o link do boleto. Tente novamente."

    except Exception as e:
        logging.exception("Erro ao gerar link do boleto:")
        return f"❌ Falha ao gerar link do boleto: {e}"
