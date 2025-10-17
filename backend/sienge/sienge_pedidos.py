# sienge_pedidos.py
import httpx
import logging
from typing import List, Dict

# Substitua pela sua chave de API do Sienge
SIENGE_API_KEY = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"  
BASE_URL = "https://api.sienge.com.br/cctcontrol/public/api/v1/purchase-orders"

logging.basicConfig(level=logging.INFO)

# ==========================
# Listar pedidos pendentes
# ==========================
def listar_pedidos_pendentes(data_inicio=None, data_fim=None) -> List[Dict]:
    params = {}
    if data_inicio:
        params["dateStart"] = data_inicio
    if data_fim:
        params["dateEnd"] = data_fim

    headers = {"Authorization": f"Bearer {SIENGE_API_KEY}"}

    resp = httpx.get(BASE_URL, headers=headers, params=params)
    if resp.status_code == 200:
        return resp.json()
    else:
        logging.warning(f"Falha ao listar pedidos: {resp.status_code}, {resp.text}")
        return []

# ==========================
# Buscar pedido por ID
# ==========================
def buscar_pedido_por_id(pedido_id: int) -> Dict | None:
    url = f"{BASE_URL}/{pedido_id}"
    headers = {"Authorization": f"Bearer {SIENGE_API_KEY}"}
    resp = httpx.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    logging.warning(f"Pedido {pedido_id} não encontrado: {resp.status_code}")
    return None

# ==========================
# Itens do pedido
# ==========================
def itens_pedido(pedido_id: int) -> List[Dict]:
    url = f"{BASE_URL}/{pedido_id}/items"
    headers = {"Authorization": f"Bearer {SIENGE_API_KEY}"}
    resp = httpx.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    logging.warning(f"Falha ao obter itens do pedido {pedido_id}: {resp.status_code}")
    return []

# ==========================
# Autorizar pedido
# ==========================
def autorizar_pedido(pedido_id: int, observacao: str = None) -> bool:
    url = f"{BASE_URL}/{pedido_id}/authorize"
    headers = {"Authorization": f"Bearer {SIENGE_API_KEY}"}
    payload = {"observation": observacao}
    resp = httpx.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 204):
        return True
    logging.warning(f"Falha ao autorizar pedido {pedido_id}: {resp.status_code}, {resp.text}")
    return False

# ==========================
# Reprovar pedido
# ==========================
def reprovar_pedido(pedido_id: int, observacao: str = None) -> bool:
    url = f"{BASE_URL}/{pedido_id}/reject"
    headers = {"Authorization": f"Bearer {SIENGE_API_KEY}"}
    payload = {"observation": observacao}
    resp = httpx.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 204):
        return True
    logging.warning(f"Falha ao reprovar pedido {pedido_id}: {resp.status_code}, {resp.text}")
    return False

# ==========================
# Gerar PDF do pedido
# ==========================
def gerar_relatorio_pdf_bytes(pedido_id: int) -> bytes | None:
    """
    Gera o PDF do pedido retornando bytes.
    Para evitar erro 406, envia 'Accept: application/pdf'.
    """
    url = f"{BASE_URL}/{pedido_id}/analysis/pdf"
    headers = {
        "Authorization": f"Bearer {SIENGE_API_KEY}",
        "Accept": "application/pdf"
    }
    resp = httpx.get(url, headers=headers)
    if resp.status_code == 200:
        logging.info(f"PDF do pedido {pedido_id} gerado com sucesso.")
        return resp.content
    else:
        logging.warning(f"Falha ao gerar PDF: status={resp.status_code}, response={resp.text}")
        return None
