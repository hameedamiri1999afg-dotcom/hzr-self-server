
import os
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="HZR SELF API",
    version="3.0.0"
)

DB_PATH = "hzr_self.db"
API_KEY = os.getenv("HZR_API_KEY", "")


def initialize_database():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


initialize_database()


class RulesPayload(BaseModel):
    rules: list[dict]


def check_key(x_api_key):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Server API key is not configured"
        )

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


@app.get("/")
def home():
    return {
        "service": "HZR SELF",
        "version": "3.0.0",
        "message": "HZR SELF server is running"
    }


@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "HZR SELF",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/rules")
def get_rules(x_api_key: str = Header(default="")):
    check_key(x_api_key)

    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT data FROM rules WHERE id = 1"
        ).fetchone()

    if row is None:
        return {"rules": []}

    import json
    return {"rules": json.loads(row[0])}


@app.put("/rules")
def save_rules(
    payload: RulesPayload,
    x_api_key: str = Header(default="")
):
    check_key(x_api_key)

    import json

    for rule in payload.rules:
        if not isinstance(rule.get("question"), str):
            raise HTTPException(
                status_code=400,
                detail="Each rule needs a question"
            )

        if not isinstance(rule.get("answer"), str):
            raise HTTPException(
                status_code=400,
                detail="Each rule needs an answer"
            )

    data = json.dumps(
        payload.rules,
        ensure_ascii=False
    )

    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            INSERT INTO rules (id, data, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
        """, (data, now))

    return {
        "success": True,
        "saved_rules": len(payload.rules),
        "updated_at": now
    }
