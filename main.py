from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from datetime import datetime
import requests

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

app = FastAPI()

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)

BASE_URL = "https://due-diligence-scraper.onrender.com"
SCRAPER_URL = "https://duedilligence-scraper.railway.app/collect"


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
    response = requests.post(SCRAPER_URL, json={"cnpj": cnpj})
    result = response.json()

    resultados = result.get("data", [])
    has_restrictions = result.get("has_restrictions", False)

    if not resultados:
        resultados = [["Nenhuma restrição encontrada", "-", "-", "-"]]

    # =========================
    # GERAR PDF (AQUI É O LUGAR CERTO)
    # =========================

    filename = f"{cnpj}_CEIS_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("CERTIDÃO DE SANÇÕES - CEIS", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"CNPJ: {cnpj}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    if has_restrictions:
        status = '<font color="red"><b>COM RESTRIÇÕES</b></font>'
    else:
        status = '<font color="green"><b>SEM RESTRIÇÕES</b></font>'

    elements.append(Paragraph(status, styles["Heading2"]))
    elements.append(Spacer(1, 20))

    table_data = [["Tipo", "Início", "Fim", "Órgão"]] + resultados

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ]))

    elements.append(table)

    doc.build(elements)

    file_url = f"{BASE_URL}/files/{filename}"

    return {
        "status": "completed",
        "file_url": file_url,
        "metadata": {
            "has_restrictions": has_restrictions
        }
    }
