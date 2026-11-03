herefrom datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="HZR SELF API",
    description="Backend service for HZR SELF",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
