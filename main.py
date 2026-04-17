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
    
    return {
        "status": "completed",
        "file_url": "https://example.com/fake.pdf",
        "metadata": {
            "has_restrictions": False
        }
    }
