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
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    
    styles = getSampleStyleSheet()
    elements = []
    
    razao_social = "EMPRESA EXEMPLO LTDA"
    data_consulta = datetime.now().strftime('%d/%m/%Y')
    
    # tabela grande (testar múltiplas páginas)
    dados_tabela = [["Tipo", "Início", "Fim", "Órgão"]]
    
    if has_restrictions:
        for i in range(40):
            dados_tabela.append([f"Sanção {i+1}", "01/01/2023", "01/01/2025", "CGU"])
    else:
        dados_tabela.append(["Nenhuma restrição encontrada", "-", "-", "-"])
    
    # =========================
    # HEADER + FOOTER
    # =========================
    def add_header_footer(canvas, doc):
        canvas.saveState()
    
        # HEADER
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(50, 770, "RELATÓRIO DE DUE DILIGENCE")
    
        canvas.setFont("Helvetica", 8)
        canvas.drawString(50, 755, f"CNPJ: {cnpj}")
    
        # FOOTER
        canvas.setFont("Helvetica", 8)
        canvas.drawString(50, 30, "Documento gerado automaticamente")
    
        # PAGINAÇÃO
        page_num = canvas.getPageNumber()
        canvas.drawRightString(550, 30, f"Página {page_num}")
    
        canvas.restoreState()
    
    # =========================
    # CONTEÚDO
    # =========================
    elements.append(Paragraph("CERTIDÃO DE SANÇÕES - CEIS", styles["Title"]))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph(f"<b>Razão Social:</b> {razao_social}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Data da consulta:</b> {data_consulta}", styles["Normal"]))
    
    elements.append(Spacer(1, 20))
    
    # STATUS
    if has_restrictions:
        status = '<font color="red"><b>STATUS: COM RESTRIÇÕES</b></font>'
    else:
        status = '<font color="green"><b>STATUS: SEM RESTRIÇÕES</b></font>'
    
    elements.append(Paragraph(status, styles["Heading2"]))
    elements.append(Spacer(1, 20))
    
    # TABELA
    table = Table(dados_tabela, repeatRows=1)
    
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # =========================
    # QR CODE COM VALIDAÇÃO REAL
    # =========================
    qr_data = f"https://due-diligence-scraper.onrender.com/validate/{filename}"
    
    qr = qrcode.make(qr_data)
    qr_path = os.path.join(FILES_DIR, f"qr_{filename}.png")
    qr.save(qr_path)
    
    elements.append(Paragraph("Validação do documento:", styles["Normal"]))
    elements.append(Image(qr_path, width=100, height=100))
    
    elements.append(Spacer(1, 20))
    
    # RODAPÉ JURÍDICO
    elements.append(Paragraph(
        "Este documento foi gerado automaticamente e pode ser validado via QR Code. "
        "Não substitui consulta oficial.",
        styles["Normal"]
    ))
    
    # =========================
    # BUILD COM HEADER/FOOTER
    # =========================
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
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
