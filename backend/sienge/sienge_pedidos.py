import requests
from base64 import b64encode
import logging
from typing import List, Dict, Any, Optional

# === CONFIGURAÇÕES ===
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"  # sua senha atual

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"

# Auth básico
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

# Cabeçalhos padrão JSON
json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# Cabeçalho para PDF (IMPORTANTE p/ evitar 406)
pdf_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/pdf",   # <- isso corrige o 406
    # NADA de Content-Type aqui
}

logging.basicConfig(level=logging.INFO)


def _get(url: str, headers: Dict[str, str]) -> requests.Response:
    r = requests.get(url, headers=headers, timeout=30)
    logging.info("%s -> %s", url, r.status_code)
    return r


def _put(url: str, headers: Dict[str, str], body: Optional[dict] = None) -> requests.Response:
    r = requests.put(url, headers=headers, json=body or {}, timeout=30)
    logging.info("%s -> %s | body=%s", url, r.status_code, body)
    return r


# =========================
#  FUNÇÕES DE CONSULTA
# =========================

def listar_pedidos_pendentes(data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retorna somente pedidos realmente pendentes de autorização:
    - status = PENDING
    - authorized = false
    - disapproved = false  (evita mostrar reprovados)
    - consistency = CONSISTENT
    """
    url = f"{BASE_URL}/purchase-orders?status=PENDING&authorized=false&consistency=CONSISTENT"
    if data_inicio:
        url += f"&startDate={data_inicio}"
    if data_fim:
        url += f"&endDate={data_fim}"

    r = _get(url, json_headers)
    if r.status_code != 200:
        logging.warning("Falha ao listar pedidos: %s", r.text)
        return []

    data = r.json() or {}
    results = data.get("results", []) or []
    # Filtra fora reprovados (alguns PENDING aparecem com disapproved=true)
    results = [p for p in results if not p.get("disapproved", False)]

    # Ordena por data desc (se existir)
    try:
        results.sort(key=lambda p: p.get("date") or "", reverse=True)
    except Exception:
        pass

    logging.info("🧾 %s pedidos pendentes encontrados.", len(results))
    return results


def buscar_pedido_por_id(purchase_order_id: int) -> Optional[Dict[str, Any]]:
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}"
    r = _get(url, json_headers)
    if r.status_code == 200:
        return r.json()
    return None


def itens_pedido(purchase_order_id: int) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/items"
    r = _get(url, json_headers)
    if r.status_code == 200:
        return (r.json() or {}).get("results", []) or []
    return []


def autorizar_pedido(purchase_order_id: int, observacao: Optional[str] = None) -> bool:
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/authorize"
    if observacao:
        # PATCH com corpo (quando há observação)
        r = requests.patch(url, headers=json_headers, json={"observation": observacao}, timeout=30)
        logging.info("%s -> %s | body=%s", url, r.status_code, {"observation": observacao})
        return r.status_code in (200, 204)
    # PUT sem corpo
    r = _put(url, json_headers)
    return r.status_code in (200, 204)


def reprovar_pedido(purchase_order_id: int, observacao: Optional[str] = None) -> bool:
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/disapprove"
    if observacao:
        r = requests.patch(url, headers=json_headers, json={"observation": observacao}, timeout=30)
        logging.info("%s -> %s | body=%s", url, r.status_code, {"observation": observacao})
        return r.status_code in (200, 204)
    r = _put(url, json_headers)
    return r.status_code in (200, 204)


def gerar_relatorio_pdf_bytes(purchase_order_id: int) -> Optional[bytes]:
    """
    PDF OFICIAL do Sienge:
    GET /purchase-orders/{id}/analysis/pdf
    Necessita Accept: application/pdf (senão 406).
    """
    url = f"{BASE_URL}/purchase-orders/{purchase_order_id}/analysis/pdf"
    r = _get(url, pdf_headers)
    if r.status_code == 200 and r.content:
        return r.content
    logging.warning("Falha ao gerar PDF: status=%s, body=%s", r.status_code, getattr(r, "text", ""))
    return None


# === Extras (opcionais/robustos) ===

def buscar_fornecedor(supplier_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not supplier_id:
        return None
    url = f"{BASE_URL}/suppliers/{supplier_id}"
    r = _get(url, json_headers)
    if r.status_code == 200:
        return r.json()
    return None


def buscar_centro_custo(cost_center_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not cost_center_id:
        return None
    url = f"{BASE_URL}/cost-centers/{cost_center_id}"
    r = _get(url, json_headers)
    if r.status_code == 200:
        return r.json()
    return None


def buscar_obra(building_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not building_id:
        return None
    url = f"{BASE_URL}/buildings/{building_id}"
    r = _get(url, json_headers)
    if r.status_code == 200:
        return r.json()
    return None
