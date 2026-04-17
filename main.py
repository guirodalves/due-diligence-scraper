from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from datetime import datetime
import requests

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

import qrcode

app = FastAPI()

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)

BASE_URL = "https://due-diligence-scraper.onrender.com"
SCRAPER_URL = "https://duediligence-scraper-service-production.up.railway.app/collect"


# 🔥 HEADER + FOOTER
def draw_header_footer(canvas, doc):
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(30, 800, "CONTROLADORIA-GERAL DA UNIÃO")

    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(200 * mm, 10 * mm, f"Página {canvas.getPageNumber()}")
    canvas.drawString(30, 10 * mm, "Documento gerado automaticamente")


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

    response = requests.post(SCRAPER_URL, json={"cnpj": cnpj}, timeout=60)
    result = response.json()

    print("SCRAPER RESPONSE:", result)

    if result.get("status") == "error":
        return result

    resultados = result.get("data", [])
    has_restrictions = result.get("has_restrictions", False)

    if not resultados:
        resultados = [["Nenhuma restrição encontrada", "-", "-", "-"]]

    filename = f"{cnpj}_CEIS_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    file_url = f"{BASE_URL}/files/{filename}"

    # QR CODE
    qr_path = os.path.join(FILES_DIR, f"{cnpj}_qr.png")
    qr = qrcode.make(file_url)
    qr.save(qr_path)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=60,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # 🔥 ESTILO CUSTOM
    title_style = ParagraphStyle(
        name="TitleCustom",
        fontSize=16,
        leading=20,
        alignment=1
    )

    status_style = ParagraphStyle(
        name="Status",
        fontSize=12,
        leading=14,
        alignment=1
    )

    elements = []

    # TÍTULO
    elements.append(Paragraph("CERTIDÃO NEGATIVA CORRECIONAL", title_style))
    elements.append(Spacer(1, 20))

    # DADOS
    elements.append(Paragraph(f"<b>CNPJ:</b> {cnpj}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Data de emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # STATUS
    if has_restrictions:
        status_text = '<font color="red"><b>SITUAÇÃO: COM RESTRIÇÕES</b></font>'
    else:
        status_text = '<font color="green"><b>SITUAÇÃO: REGULAR (NADA CONSTA)</b></font>'

    elements.append(Paragraph(status_text, status_style))
    elements.append(Spacer(1, 20))

    # TABELA
    table_data = [["Tipo", "Início", "Fim", "Órgão"]] + resultados

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#052415")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    elements.append(table)

    # QR
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Valide este documento:", styles["Normal"]))
    elements.append(Image(qr_path, width=90, height=90))

    # BUILD
    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)

    return {
    "status": "completed",
    "file_url": file_url,
    "metadata": {
        "tipo": "CEIS",
        "cnpj": cnpj,
        "has_restrictions": has_restrictions,
        "data_emissao": datetime.now().isoformat()
    }
}
