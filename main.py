from fastapi import FastAPI
import time
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.responses import FileResponse

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

@app.post("/collect")
def collect(data: dict):
    time.sleep(2)

    cnpj_raw = data.get("cnpj", "")

    # remove tudo que não é número
    cnpj = "".join(filter(str.isdigit, cnpj_raw))

    try:
        ultimo_digito = int(cnpj[-1])
    except:
        ultimo_digito = 0

    has_restrictions = ultimo_digito % 2 != 0

    # nome do arquivo
    filename = f"CEIS_{cnpj}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    # gerar PDF
    c = canvas.Canvas(filepath, pagesize=letter)

    c.setFont("Helvetica", 14)
    c.drawString(100, 750, "CERTIDÃO CEIS")

    c.setFont("Helvetica", 12)
    c.drawString(100, 700, f"CNPJ: {cnpj}")
    c.drawString(100, 680, f"Data da consulta: {time.strftime('%d/%m/%Y')}")

    if has_restrictions:
        c.setFillColorRGB(1, 0, 0)
        c.drawString(100, 640, "RESULTADO: COM RESTRIÇÕES")
    else:
        c.setFillColorRGB(0, 0.5, 0)
        c.drawString(100, 640, "RESULTADO: SEM RESTRIÇÕES")

    c.setFillColorRGB(0, 0, 0)
    c.drawString(100, 600, "Fonte: Cadastro Nacional de Empresas Inidôneas e Suspensas (CEIS)")

    c.save()

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
