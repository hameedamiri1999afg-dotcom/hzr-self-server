
import os
import json
import time
import sqlite3
import asyncio

from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from telethon import TelegramClient, events
from telethon.sessions import StringSession


# ==========================================
# HZR SELF SERVER 3.0
# ==========================================

DB_PATH = "hzr_self.db"

API_KEY = os.getenv("HZR_API_KEY", "")

TG_API_ID = os.getenv("TG_API_ID", "")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_SESSION = os.getenv("TG_SESSION", "")

telegram_client = None
telegram_status = "OFFLINE"

reply_cooldowns = {}


# ==========================================
# DATABASE
# ==========================================

def initialize_database():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def load_rules():
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT data FROM rules WHERE id = 1"
        ).fetchone()

    if row is None:
        return []

    return json.loads(row[0])


def save_rules(rules):
    data = json.dumps(rules, ensure_ascii=False)

    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            INSERT INTO rules (id, data, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
        """, (data, now))


initialize_database()


# ==========================================
# TEXT MATCHING
# ==========================================

def normalize(text):
    return " ".join(text.strip().casefold().split())


# ==========================================
# TELEGRAM MESSAGE ENGINE
# ==========================================

async def handle_message(event):
    if not event.is_private:
        return

    message = event.raw_text or ""

    if not message.strip():
        return

    try:
        incoming = normalize(message)

        rules = load_rules()

        for rule in rules:
            question = normalize(rule.get("question", ""))
            answer = rule.get("answer", "")

            if not question or not answer.strip():
                continue

            if incoming == question:

                sender_id = event.sender_id
                cooldown_key = (sender_id, question)

                now = time.monotonic()
                previous = reply_cooldowns.get(
                    cooldown_key, 0
                )

                if now - previous < 10:
                    return

                reply_cooldowns[cooldown_key] = now

                await event.reply(answer)

                print(
                    f"HZR SELF: Replied to {sender_id}"
                )

                return

    except Exception as error:
        print("Message engine error:", str(error))


# ==========================================
# TELEGRAM CONNECTION
# ==========================================

async def connect_telegram():
    global telegram_client
    global telegram_status

    if not TG_API_ID or not TG_API_HASH or not TG_SESSION:
        telegram_status = "CONFIGURATION_MISSING"
        print("Telegram configuration is missing.")
        return

    try:
        telegram_client = TelegramClient(
            StringSession(TG_SESSION),
            int(TG_API_ID),
            TG_API_HASH
        )

        await telegram_client.connect()

        if not await telegram_client.is_user_authorized():
            telegram_status = "UNAUTHORIZED"
            print("Telegram session is not authorized.")
            await telegram_client.disconnect()
            return

        telegram_client.add_event_handler(
            handle_message,
            events.NewMessage(incoming=True)
        )

        telegram_status = "ONLINE"

        print("HZR SELF Telegram engine is ONLINE.")

    except Exception as error:
        telegram_status = "ERROR"
        print("Telegram connection error:", str(error))


# ==========================================
# FASTAPI LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    await connect_telegram()

    yield

    global telegram_status

    if telegram_client and telegram_client.is_connected():
        await telegram_client.disconnect()

    telegram_status = "OFFLINE"


app = FastAPI(
    title="HZR SELF API",
    version="3.0.0",
    lifespan=lifespan
)


# ==========================================
# SECURITY
# ==========================================

def check_key(x_api_key):

    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API key is not configured"
        )

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


# ==========================================
# DATA MODEL
# ==========================================

class RulesPayload(BaseModel):
    rules: list[dict]


# ==========================================
# ROUTES
# ==========================================

@app.get("/")
def home():

    return {
        "service": "HZR SELF",
        "version": "3.0.0",
        "message": "Server is running"
    }


@app.get("/health")
def health():

    return {
        "status": "online",
        "service": "HZR SELF",
        "telegram": telegram_status,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }


@app.get("/telegram/status")
def get_telegram_status(
    x_api_key: str = Header(default="")
):

    check_key(x_api_key)

    return {
        "telegram": telegram_status
    }


@app.get("/rules")
def get_rules(
    x_api_key: str = Header(default="")
):

    check_key(x_api_key)

    return {
        "rules": load_rules()
    }


@app.put("/rules")
def update_rules(
    payload: RulesPayload,
    x_api_key: str = Header(default="")
):

    check_key(x_api_key)

    for rule in payload.rules:

        question = rule.get("question")
        answer = rule.get("answer")

        if not isinstance(question, str):
            raise HTTPException(
                status_code=400,
                detail="Invalid question"
            )

        if not isinstance(answer, str):
            raise HTTPException(
                status_code=400,
                detail="Invalid answer"
            )

        if not question.strip() or not answer.strip():
            raise HTTPException(
                status_code=400,
                detail="Question and answer cannot be empty"
            )

    save_rules(payload.rules)

    return {
        "success": True,
        "saved_rules": len(payload.rules),
        "telegram": telegram_status
    }
