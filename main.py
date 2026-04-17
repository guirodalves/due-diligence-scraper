from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API rodando"}

@app.get("/healthz")
def health():
    return {"status": "ok"}

@app.post("/collect")
def collect(data: dict):
    time.sleep(2)

    cnpj = data.get("cnpj", "")

    # lógica simples: par = sem restrição, ímpar = com restrição
    try:
        ultimo_digito = int(cnpj[-1])
    except:
        ultimo_digito = 0

    has_restrictions = ultimo_digito % 2 != 0

    return {
        "status": "completed",
        "file_url": f"https://example.com/ceis_{cnpj}.pdf",
        "metadata": {
            "has_restrictions": has_restrictions
        }
    }
