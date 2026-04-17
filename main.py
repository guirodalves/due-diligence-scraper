from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from datetime import datetime
import requests

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm

import qrcode

app = FastAPI()

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)

BASE_URL = "https://due-diligence-scraper.onrender.com"
SCRAPER_URL = "https://duediligence-scraper-service-production.up.railway.app/collect"


def add_page_number(canvas, doc):
    canvas.drawRightString(200 * mm, 15 * mm, f"Página {canvas.getPageNumber()}")


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/files/{filename}")
def get_file(filename: str):
    filepath = os.path.join(FILES_DIR, filename)
    return FileResponse(filepath, media_type='application/pdf')


@app.post("/collect")
def collect(data: dict):

    cnpj_raw = data.get("cnpj", "")
    cnpj = "".join(filter(str.isdigit, cnpj_raw))

    # 🔥 CHAMA O SCRAPER (Railway)
    response = requests.post(SCRAPER_URL, json={"cnpj": cnpj}, timeout=60)
    result = response.json()

    print("SCRAPER RESPONSE:", result)

    # 🔥 TRATAMENTO DE ERRO
    if result.get("status") == "error":
        return {
            "status": "error",
            "message": result.get("message", "Erro no scraper")
        }

    resultados = result.get("data", [])
    has_restrictions = result.get("has_restrictions", False)

    if not resultados:
        resultados = [["Nenhuma restrição encontrada", "-", "-", "-"]]

    # =========================
    # GERAR PDF
    # =========================

    filename = f"{cnpj}_CEIS_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    file_url = f"{BASE_URL}/files/{filename}"

    # 🔥 QR CODE (agora no lugar correto)
    qr_path = os.path.join(FILES_DIR, f"{cnpj}_qr.png")
    qr = qrcode.make(file_url)
    qr.save(qr_path)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = []

    # HEADER
    elements.append(Paragraph("CONTROLADORIA-GERAL DA UNIÃO", styles["Heading2"]))
    elements.append(Paragraph("CERTIDÃO NEGATIVA CORRECIONAL", styles["Title"]))
    elements.append(Spacer(1, 10))

    # DADOS
    elements.append(Paragraph(f"CNPJ: {cnpj}", styles["Normal"]))
    elements.append(Paragraph(f"Data de emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # STATUS
    if has_restrictions:
        status = '<font color="red"><b>SITUAÇÃO: COM RESTRIÇÕES</b></font>'
    else:
        status = '<font color="green"><b>SITUAÇÃO: NADA CONSTA</b></font>'

    elements.append(Paragraph(status, styles["Heading2"]))
    elements.append(Spacer(1, 20))

    # TABELA
    table_data = [["Tipo", "Início", "Fim", "Órgão"]] + resultados

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ]))

    elements.append(table)

    # QR CODE
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Valide este documento:", styles["Normal"]))
    elements.append(Image(qr_path, width=100, height=100))

    # BUILD
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    return {
        "status": "completed",
        "file_url": file_url,
        "metadata": {
            "has_restrictions": has_restrictions
        }
    }
