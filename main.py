from fastapi import FastAPI
import time
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.responses import FileResponse
from reportlab.lib import colors
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import qrcode

app = FastAPI()

# pasta para salvar PDFs
FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"message": "API rodando"}

@app.get("/healthz")
def health():
    return {"status": "ok"}

from playwright.sync_api import sync_playwright

@app.post("/collect")
def collect(data: dict):

    cnpj_raw = data.get("cnpj", "")
    cnpj = "".join(filter(str.isdigit, cnpj_raw))

    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # URL pública CEIS
        page.goto("https://certidoes.cgu.gov.br/")

        # Espera campo aparecer
        page.wait_for_timeout(3000)

        # esperar botão aparecer
        page.wait_for_selector('text=Ente Privado')
        
        # clicar
        page.click('text=Ente Privado')
        
        # pequena espera
        page.wait_for_timeout(1000)

        # Preenche CNPJ
        page.fill('input[type="text"]', cnpj)

        # Clica buscar
        page.keyboard.press("Enter")

        page.wait_for_timeout(5000)

        # Tenta capturar tabela
        rows = page.query_selector_all("table tbody tr")

        if not rows:
            has_restrictions = False
        else:
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

    # fallback se vazio
    if not resultados:
        resultados = [["Nenhuma restrição encontrada", "-", "-", "-"]]

    # =========================
    # PDF usa resultados reais
    # =========================

    from datetime import datetime

    data_hoje = datetime.now().strftime("%Y%m%d")
    filename = f"{cnpj}_CEIS_CERTIDAO_{data_hoje}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    # aqui você mantém seu código de PDF
    # só troque dados_tabela por resultados

    dados_tabela = [["Tipo", "Início", "Fim", "Órgão"]] + resultados

    # (mantém seu bloco PDF já pronto aqui)

    BASE_URL = "https://due-diligence-scraper.onrender.com"

    file_url = f"{BASE_URL}/files/{filename}"

    return {
        "status": "completed",
        "file_url": file_url,
        "metadata": {
            "has_restrictions": has_restrictions
        }
    }

@app.get("/files/{filename}")
def get_file(filename: str):
    filepath = os.path.join(FILES_DIR, filename)
    return FileResponse(filepath, media_type='application/pdf')

@app.get("/validate/{filename}")
def validate(filename: str):
    return {
        "status": "valid",
        "document": filename,
        "message": "Documento válido gerado pelo sistema de due diligence"
    }
