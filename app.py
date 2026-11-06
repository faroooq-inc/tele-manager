import os
import hmac
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import SQLiteSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
)

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
APP_API_KEY = os.getenv("APP_API_KEY", "")
SESSION_PATH = os.getenv("SESSION_PATH", "/var/data/telegram_manager")

client: Optional[TelegramClient] = None
pending_phone: Optional[str] = None
pending_code_hash: Optional[str] = None
twofa_pending = False


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not APP_API_KEY:
        raise HTTPException(status_code=503, detail="Server setup incomplete: APP_API_KEY is missing.")
    if not x_api_key or not hmac.compare_digest(x_api_key, APP_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    if API_ID and API_HASH:
        os.makedirs(os.path.dirname(SESSION_PATH) or ".", exist_ok=True)
        client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
        await client.connect()
    yield
    if client and client.is_connected():
        await client.disconnect()


app = FastAPI(
    title="Telegram Manager Backend",
    description="Single-owner MTProto + Telegram Bot API backend for an Android client.",
    version="1.0.0",
    lifespan=lifespan,
)


class PhoneRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=30)


class CodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20)


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class SendMessageRequest(BaseModel):
    peer: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class BotTokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class BotSendRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    chat_id: str
    text: str = Field(min_length=1, max_length=4000)


class BotUpdatesRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    offset: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)


@app.get("/health")
async def health():
    return {"ok": True, "service": "telegram-manager-backend"}


def get_client():
    if client is None or not client.is_connected():
        raise HTTPException(status_code=503, detail="MTProto is not configured or connected.")
    return client


@app.post("/auth/send-code", dependencies=[Depends(require_api_key)])
async def send_login_code(data: PhoneRequest):
    global pending_phone, pending_code_hash, twofa_pending
    tg = get_client()
    try:
        result = await tg.send_code_request(data.phone)
        pending_phone = data.phone
        pending_code_hash = result.phone_code_hash
        twofa_pending = False
        return {"ok": True, "message": "Telegram login code requested. Check your Telegram app/SMS."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not request login code: {type(exc).__name__}")


@app.post("/auth/verify-code", dependencies=[Depends(require_api_key)])
async def verify_login_code(data: CodeRequest):
    global pending_phone, pending_code_hash, twofa_pending
    tg = get_client()
    if not pending_phone or not pending_code_hash:
        raise HTTPException(status_code=400, detail="Request a login code first.")
    try:
        await tg.sign_in(phone=pending_phone, code=data.code, phone_code_hash=pending_code_hash)
        pending_phone = None
        pending_code_hash = None
        twofa_pending = False
        me = await tg.get_me()
        return {"ok": True, "authorized": True, "user": {"id": str(me.id), "first_name": me.first_name, "username": me.username}}
    except SessionPasswordNeededError:
        twofa_pending = True
        return {"ok": False, "needs_2fa_password": True, "message": "This account has Telegram two-step verification enabled."}
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        raise HTTPException(status_code=400, detail="Invalid or expired login code.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Login failed: {type(exc).__name__}")


@app.post("/auth/verify-2fa", dependencies=[Depends(require_api_key)])
async def verify_2fa(data: PasswordRequest):
    global twofa_pending
    tg = get_client()
    if not twofa_pending:
        raise HTTPException(status_code=400, detail="Two-step verification is not currently pending.")
    try:
        await tg.sign_in(password=data.password)
        twofa_pending = False
        me = await tg.get_me()
        return {"ok": True, "authorized": True, "user": {"id": str(me.id), "first_name": me.first_name, "username": me.username}}
    except PasswordHashInvalidError:
        raise HTTPException(status_code=400, detail="Incorrect two-step verification password.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"2FA login failed: {type(exc).__name__}")


@app.get("/auth/status", dependencies=[Depends(require_api_key)])
async def auth_status():
    tg = get_client()
    authorized = await tg.is_user_authorized()
    if not authorized:
        return {"authorized": False}
    me = await tg.get_me()
    return {"authorized": True, "user": {"id": str(me.id), "first_name": me.first_name, "username": me.username}}


@app.post("/auth/logout", dependencies=[Depends(require_api_key)])
async def logout():
    tg = get_client()
    await tg.log_out()
    return {"ok": True, "message": "Telegram session logged out."}


@app.get("/dialogs", dependencies=[Depends(require_api_key)])
async def dialogs(limit: int = 30):
    tg = get_client()
    if not await tg.is_user_authorized():
        raise HTTPException(status_code=401, detail="Telegram account is not logged in.")
    limit = max(1, min(limit, 100))
    result = []
    async for dialog in tg.iter_dialogs(limit=limit):
        entity = dialog.entity
        result.append({
            "id": str(dialog.id),
            "name": dialog.name,
            "unread_count": dialog.unread_count,
            "is_group": dialog.is_group,
            "is_channel": dialog.is_channel,
            "is_user": dialog.is_user,
            "username": getattr(entity, "username", None),
        })
    return {"ok": True, "dialogs": result}


@app.get("/messages", dependencies=[Depends(require_api_key)])
async def messages(peer: str, limit: int = 30):
    tg = get_client()
    if not await tg.is_user_authorized():
        raise HTTPException(status_code=401, detail="Telegram account is not logged in.")
    limit = max(1, min(limit, 100))
    try:
        entity = await tg.get_entity(int(peer) if peer.lstrip("-").isdigit() else peer)
        result = []
        async for msg in tg.iter_messages(entity, limit=limit):
            result.append({
                "id": msg.id,
                "date": msg.date.isoformat() if msg.date else None,
                "sender_id": str(msg.sender_id) if msg.sender_id else None,
                "text": msg.message or "",
                "out": msg.out,
            })
        return {"ok": True, "messages": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load messages: {type(exc).__name__}")


@app.post("/messages/send", dependencies=[Depends(require_api_key)])
async def send_user_message(data: SendMessageRequest):
    tg = get_client()
    if not await tg.is_user_authorized():
        raise HTTPException(status_code=401, detail="Telegram account is not logged in.")
    try:
        entity = await tg.get_entity(int(data.peer) if data.peer.lstrip("-").isdigit() else data.peer)
        sent = await tg.send_message(entity, data.message)
        return {"ok": True, "message_id": sent.id}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not send message: {type(exc).__name__}")


async def bot_api(token: str, method: str, payload: dict = None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=25) as http:
        response = await http.post(url, json=payload or {})
        try:
            data = response.json()
        except Exception:
            raise HTTPException(status_code=502, detail="Telegram Bot API returned an unreadable response.")
    if not data.get("ok"):
        raise HTTPException(status_code=400, detail=data.get("description", "Telegram Bot API request failed."))
    return data.get("result")


@app.post("/bot/validate", dependencies=[Depends(require_api_key)])
async def validate_bot(data: BotTokenRequest):
    result = await bot_api(data.token, "getMe")
    return {"ok": True, "bot": result}


@app.post("/bot/send-message", dependencies=[Depends(require_api_key)])
async def bot_send_message(data: BotSendRequest):
    result = await bot_api(data.token, "sendMessage", {"chat_id": data.chat_id, "text": data.text})
    return {"ok": True, "result": result}


@app.post("/bot/updates", dependencies=[Depends(require_api_key)])
async def bot_updates(data: BotUpdatesRequest):
    payload = {"limit": data.limit, "timeout": 0}
    if data.offset is not None:
        payload["offset"] = data.offset
    result = await bot_api(data.token, "getUpdates", payload)
    return {"ok": True, "updates": result}
