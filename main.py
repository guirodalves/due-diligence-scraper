from fastapi import FastAPI
import time
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.responses import FileResponse
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
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

    # =========================
    # DADOS MOCK (por enquanto)
    # =========================
    razao_social = "EMPRESA EXEMPLO LTDA"
    data_consulta = datetime.now().strftime('%d/%m/%Y')
    
    # simulação de tabela de sanções
    dados_tabela = [
        ["Tipo de Sanção", "Início", "Fim", "Órgão"],
    ]
    
    if has_restrictions:
        dados_tabela.append(["Suspensão", "01/01/2023", "01/01/2025", "CGU"])
    else:
        dados_tabela.append(["Nenhuma restrição encontrada", "-", "-", "-"])
    
    # =========================
    # CABEÇALHO
    # =========================
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "CERTIDÃO DE SANÇÕES - CEIS")
    
    c.setFont("Helvetica", 10)
    c.drawString(100, 730, "Cadastro Nacional de Empresas Inidôneas e Suspensas")
    
    # linha
    c.setStrokeColor(colors.grey)
    c.line(100, 720, 500, 720)
    
    # =========================
    # DADOS DA EMPRESA
    # =========================
    c.setFont("Helvetica", 11)
    c.drawString(100, 690, f"CNPJ: {cnpj}")
    c.drawString(100, 670, f"Razão Social: {razao_social}")
    c.drawString(100, 650, f"Data da consulta: {data_consulta}")
    
    # =========================
    # STATUS DESTACADO
    # =========================
    if has_restrictions:
        c.setFillColor(colors.red)
        status_text = "COM RESTRIÇÕES"
    else:
        c.setFillColor(colors.green)
        status_text = "SEM RESTRIÇÕES"
    
    c.rect(100, 600, 300, 25, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(110, 607, f"STATUS: {status_text}")
    
    # reset cor
    c.setFillColor(colors.black)
    
    # =========================
    # TABELA
    # =========================
    table = Table(dados_tabela, colWidths=[120, 80, 80, 120])
    
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
    ]))
    
    table.wrapOn(c, 100, 500)
    table.drawOn(c, 100, 500)
    
    # =========================
    # QR CODE
    # =========================
    qr_data = f"https://due-diligence-scraper.onrender.com/files/{filename}"
    
    qr = qrcode.make(qr_data)
    qr_path = os.path.join(FILES_DIR, f"qr_{filename}.png")
    qr.save(qr_path)
    
    c.drawImage(qr_path, 400, 600, width=100, height=100)
    
    # =========================
    # RODAPÉ
    # =========================
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(100, 100, "Documento gerado automaticamente para fins de due diligence.")
    c.drawString(100, 85, "Este documento não substitui consulta oficial.")
    
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
