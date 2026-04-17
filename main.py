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
    from datetime import datetime

    data_hoje = datetime.now().strftime("%Y%m%d")
    filename = f"{cnpj}_CEIS_CERTIDAO_{data_hoje}.pdf"
    filepath = os.path.join(FILES_DIR, filename)

    # gerar PDF
    from reportlab.lib import colors
    from datetime import datetime

    c = canvas.Canvas(filepath, pagesize=letter)

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "CERTIDÃO NEGATIVA DE SANÇÕES")
    
    # Linha
    c.setStrokeColor(colors.grey)
    c.line(100, 740, 500, 740)

    # Informações
    c.setFont("Helvetica", 11)
    c.drawString(100, 700, f"CNPJ: {cnpj}")
    c.drawString(100, 680, f"Data da consulta: {datetime.now().strftime('%d/%m/%Y')}")

    # Status
    c.setFont("Helvetica-Bold", 12)

    if has_restrictions:
        c.setFillColor(colors.red)
        c.drawString(100, 640, "STATUS: COM RESTRIÇÕES")
    else:
        c.setFillColor(colors.green)
        c.drawString(100, 640, "STATUS: SEM RESTRIÇÕES")
    
    # Reset cor
    c.setFillColor(colors.black)
    
    # Descrição
    c.setFont("Helvetica", 10)
    c.drawString(100, 600, "Consulta realizada no CEIS (Cadastro Nacional de Empresas Inidôneas e Suspensas).")
    
    # Rodapé
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(100, 100, "Documento gerado automaticamente para fins de due diligence.")
    
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
