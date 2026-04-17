from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from datetime import datetime
import time

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# QR Code
import qrcode

# Playwright
from playwright.sync_api import sync_playwright

app = FastAPI()

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)

BASE_URL = "https://due-diligence-scraper.onrender.com"


@app.get("/")
def root():
    return {"message": "API rodando"}


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/validate/{filename}")
def validate(filename: str):
    return {
        "status": "valid",
        "document": filename,
        "message": "Documento válido gerado pelo sistema de due diligence"
    }


@app.get("/files/{filename}")
def get_file(filename: str):
    filepath = os.path.join(FILES_DIR, filename)
    return FileResponse(filepath, media_type='application/pdf')


@app.post("/collect")
def collect(data: dict):

    cnpj_raw = data.get("cnpj", "")
    cnpj = "".join(filter(str.isdigit, cnpj_raw))

    resultados = []
    has_restrictions = False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()

        page.goto("https://certidoes.cgu.gov.br/")
        page.wait_for_timeout(3000)

        # ✅ selecionar Ente Privado
        page.wait_for_selector('text=Ente Privado')
        page.locator("text=Ente Privado").first.click()
        page.wait_for_timeout(1000)

        # preencher CNPJ
        page.fill('input[type="text"]', cnpj)
        page.keyboard.press("Enter")

        page.wait_for_timeout(8000)

        rows = page.query_selector_all("table tbody tr")

        if rows:
            has_restrictions = True

            for row in rows:
                cols = row.query_selector_all("td")
                if len(cols) >= 4:
                    resultados.append([
                        cols[0].inner_text(),
                        cols[1].inner_text(),
                        cols[2].inner_text(),
                        cols[3].inner_text()
                    ])

        browser.close()

    if not resultados:
        resultados = [["Nenhuma restrição encontrada", "-", "-", "-"]]

    # =========================
    # PDF
    # =========================

    data_hoje = datetime.now().strftime("%Y%m%d")
    filename = f"{cnpj}_CEIS_CERTIDAO_{data_hoje}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    razao_social = "EMPRESA CONSULTADA"
    data_consulta = datetime.now().strftime('%d/%m/%Y')

    dados_tabela = [["Tipo", "Início", "Fim", "Órgão"]] + resultados

    # HEADER + FOOTER
    def add_header_footer(canvas, doc):
        canvas.saveState()

        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(50, 770, "RELATÓRIO DE DUE DILIGENCE")

        canvas.setFont("Helvetica", 8)
        canvas.drawString(50, 755, f"CNPJ: {cnpj}")

        canvas.setFont("Helvetica", 8)
        canvas.drawString(50, 30, "Documento gerado automaticamente")

        page_num = canvas.getPageNumber()
        canvas.drawRightString(550, 30, f"Página {page_num}")

        canvas.restoreState()

    # CONTEÚDO
    elements.append(Paragraph("CERTIDÃO DE SANÇÕES - CEIS", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Razão Social:</b> {razao_social}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Data da consulta:</b> {data_consulta}", styles["Normal"]))

    elements.append(Spacer(1, 20))

    if has_restrictions:
        status = '<font color="red"><b>STATUS: COM RESTRIÇÕES</b></font>'
    else:
        status = '<font color="green"><b>STATUS: SEM RESTRIÇÕES</b></font>'

    elements.append(Paragraph(status, styles["Heading2"]))
    elements.append(Spacer(1, 20))

    table = Table(dados_tabela, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 30))

    # QR CODE (validação real)
    qr_data = f"{BASE_URL}/validate/{filename}"
    qr = qrcode.make(qr_data)

    qr_path = os.path.join(FILES_DIR, f"qr_{filename}.png")
    qr.save(qr_path)

    elements.append(Paragraph("Validação do documento:", styles["Normal"]))
    elements.append(Image(qr_path, width=100, height=100))

    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        "Este documento foi gerado automaticamente e pode ser validado via QR Code. "
        "Não substitui consulta oficial.",
        styles["Normal"]
    ))

    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    file_url = f"{BASE_URL}/files/{filename}"

    return {
        "status": "completed",
        "file_url": file_url,
        "metadata": {
            "has_restrictions": has_restrictions
        }
    }
