from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(
    title="HZR SELF API",
    version="2.1.0"
)


@app.get("/")
def home():
    return {
        "service": "HZR SELF",
        "version": "2.1.0",
        "message": "HZR SELF server is running"
    }


@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "HZR SELF",
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
