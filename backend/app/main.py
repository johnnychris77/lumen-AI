from fastapi import FastAPI

app = FastAPI(title="LumenAI")

@app.get("/health")
def health():
    return {"ok": True}
