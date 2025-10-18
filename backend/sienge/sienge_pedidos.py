import requests
import logging
from base64 import b64encode
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# Configurações de autenticação da API Sienge
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2NaMNFoEoZOuOAqeSRy7bYWYDf85"

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"
token = b64encode(f"{usuario}:{senha}".encode()).decode()
headers = {
    "Authorization": f"Basic {token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

logging.basicConfig(level=logging.INFO)


# === FUNÇÕES BÁSICAS ===
def listar_pedidos_pendentes():
    url = f"{BASE_URL}/purchase-orders?status=PENDING&authorized=false"
    logging.info(f"listar_pedidos_pendentes: {url}")
    r = requests.get(url, headers=headers)
    return r.json().get("results", []) if r.status_code == 200 else []


def buscar_pedido_por_id(pedido_id):
    url = f"{BASE_URL}/purchase-orders/{pedido_id}"
    logging.info(f"buscar_pedido_por_id: {url}")
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None


def itens_pedido(pedido_id):
    url = f"{BASE_URL}/purchase-orders/{pedido_id}/items"
    logging.info(f"itens_pedido: {url}")
    r = requests.get(url, headers=headers)
    return r.json().get("results", []) if r.status_code == 200 else []


def buscar_centro_custo(cc_id):
    url = f"{BASE_URL}/cost-centers/{cc_id}"
    logging.info(f"buscar_centro_custo: {url}")
    r = requests.get(url, headers=headers)
    return r.json().get("description") if r.status_code == 200 else "Não informado"


def buscar_obra(obra_id):
    url = f"{BASE_URL}/buildings/{obra_id}"
    logging.info(f"buscar_obra: {url}")
    r = requests.get(url, headers=headers)
    return r.json().get("name") if r.status_code == 200 else "Não informado"


def buscar_fornecedor(fornecedor_id):
    url = f"{BASE_URL}/suppliers/{fornecedor_id}"
    logging.info(f"buscar_fornecedor: {url}")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        nome = data.get("name", "Não informado")
        cnpj = data.get("cnpj", "-")
        return f"{nome} (CNPJ {cnpj})"
    return "Não informado"


def buscar_totalizacao(pedido_id):
    url = f"{BASE_URL}/purchase-orders/{pedido_id}/totalization"
    logging.info(f"buscar_totalizacao: {url}")
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None


def autorizar_pedido(pedido_id):
    url = f"{BASE_URL}/purchase-orders/{pedido_id}/authorize"
    logging.info(f"autorizar_pedido: {url}")
    r = requests.put(url, headers=headers)
    return r.status_code


def reprovar_pedido(pedido_id):
    url = f"{BASE_URL}/purchase-orders/{pedido_id}/disapprove"
    logging.info(f"reprovar_pedido: {url}")
    r = requests.put(url, headers=headers)
    return r.status_code


# === GERAÇÃO DE PDF (em Base64) ===
def gerar_pdf_pedido_base64(pedido, itens, totalizacao):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica", 11)
    largura, altura = A4
    y = altura - 2 * cm

    pdf.drawString(2 * cm, y, f"Resumo do Pedido {pedido.get('id')}")
    y -= 0.8 * cm
    pdf.drawString(2 * cm, y, f"Data: {pedido.get('date', '-')}")
    y -= 0.5 * cm
    pdf.drawString(2 * cm, y, f"Comprador: {pedido.get('buyerId', '-')}")
    y -= 0.5 * cm
    pdf.drawString(2 * cm, y, f"Obra: {pedido.get('buildingId', '-')}")
    y -= 0.5 * cm
    pdf.drawString(2 * cm, y, f"Centro de Custo: {pedido.get('costCenterId', '-')}")
    y -= 0.5 * cm
    pdf.drawString(2 * cm, y, f"Fornecedor ID: {pedido.get('supplierId', '-')}")
    y -= 0.5 * cm
    pdf.drawString(2 * cm, y, f"Condição de Pagamento: {pedido.get('paymentCondition', '-')}")
    y -= 1 * cm

    pdf.drawString(2 * cm, y, "Itens do Pedido:")
    y -= 0.5 * cm
    for item in itens:
        descricao = item.get("resourceDescription", "Item")
        qtd = item.get("quantity", 0)
        preco = item.get("unitPrice", 0)
        pdf.drawString(2 * cm, y, f"- {descricao} ({qtd} un) - R$ {preco:,.2f}")
        y -= 0.4 * cm
        if y < 3 * cm:
            pdf.showPage()
            y = altura - 2 * cm

    total = totalizacao.get("itemsTotalAmount", pedido.get("totalAmount", 0)) if totalizacao else pedido.get("totalAmount", 0)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y - 1 * cm, f"Valor Total: R$ {total:,.2f}")

    pdf.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return b64encode(pdf_bytes).decode()
