"""
ARIA Cloud Brain
================
FastAPI server designed for Render.com free tier.
Uses Groq API (free) for AI — no GPU needed, runs 24/7 in the cloud.
Data persisted in Supabase (free tier).

Deploy: push to GitHub → connect to Render → done.
"""

import os, json, asyncio, tempfile
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Free tier
GROQ_WHISPER  = "whisper-large-v3-turbo"                             # Free STT
GROQ_BASE     = "https://api.groq.com/openai/v1"

HA_URL        = os.getenv("HA_URL",   "")
HA_TOKEN      = os.getenv("HA_TOKEN", "")

SUPABASE_URL  = os.getenv("SUPABASE_URL",  "")
SUPABASE_KEY  = os.getenv("SUPABASE_ANON_KEY", "")

APP_PASSWORD  = os.getenv("APP_PASSWORD", "")   # Simple auth to protect your AI
PORT          = int(os.getenv("PORT", 8000))

# ── Startup / keep-alive ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background keep-alive ping (so Render free tier stays awake)
    async def keep_alive():
        app_url = os.getenv("RENDER_EXTERNAL_URL", "")
        if not app_url:
            return
        while True:
            await asyncio.sleep(240)  # Ping every 4 minutes
            try:
                async with httpx.AsyncClient() as c:
                    await c.get(f"{app_url}/healthz", timeout=5)
            except:
                pass
    asyncio.create_task(keep_alive())
    yield

app = FastAPI(title="ARIA Cloud", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve static files and frontend
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Module routing ────────────────────────────────────────────────────────────
MODULES = {
    "work":     ["test","bug","qa","regression","playwright","jira","ticket","defect","sprint","deploy","code","review","selenium","coverage"],
    "home":     ["light","device","thermostat","temperature","lock","door","camera","home","turn on","turn off","scene","fan","switch"],
    "health":   ["workout","exercise","steps","sleep","weight","heart","fitness","run","gym","calories burned","training","stretch"],
    "food":     ["eat","food","meal","recipe","calories","nutrition","protein","carb","breakfast","lunch","dinner","snack","diet","macro","grocery"],
    "planning": ["remind","schedule","calendar","todo","task","meeting","appointment","plan","agenda","tomorrow","today","week","deadline"],
}

def route(msg: str) -> str:
    lower = msg.lower()
    scores = {m: sum(1 for kw in kws if kw in lower) for m, kws in MODULES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"

# ── System prompts ────────────────────────────────────────────────────────────
def get_system(module: str) -> str:
    base = f"Today is {datetime.now().strftime('%A, %B %d, %Y')}. "
    prompts = {
        "work":     base + "You are ARIA, a QA engineering assistant. Help with Playwright/Selenium tests, bug triage, test plans, coverage analysis, and sprint planning. Be technical, precise, use code examples.",
        "home":     base + "You are ARIA, a smart home assistant. Control devices via Home Assistant. For control actions output JSON: {\"ha_action\":\"turn_on\"|\"turn_off\"|\"set_temperature\", \"entity\":\"entity_id\", \"value\":optional}. Then confirm in plain English.",
        "health":   base + "You are ARIA, a personal health and fitness coach. Help with workouts, sleep optimisation, habit building, and progress tracking. Be encouraging, data-driven, and practical.",
        "food":     base + "You are ARIA, a nutrition coach and meal planner. Help with meal ideas, macro tracking, recipes, grocery lists, and dietary goals. Be practical and specific.",
        "planning": base + "You are ARIA, a personal productivity assistant. Help with scheduling, tasks, prioritisation, and daily planning. Be organised and proactive.",
        "general":  base + "You are ARIA, a personal AI assistant. You help with QA work, smart home, health, nutrition, and daily planning. Be helpful, direct, and concise.",
    }
    return prompts.get(module, prompts["general"])

# ── Auth middleware (optional password protection) ────────────────────────────
async def check_auth(request: Request) -> bool:
    if not APP_PASSWORD:
        return True
    token = request.headers.get("X-Auth-Token") or request.query_params.get("token")
    return token == APP_PASSWORD

# ── Groq chat ─────────────────────────────────────────────────────────────────
async def groq_chat(messages: list, stream: bool = False):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set. Add it in Render environment variables.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model":    GROQ_MODEL,
        "messages": messages,
        "stream":   stream,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    return headers, payload

# ── REST chat endpoint ────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []
    module: str = "auto"
    token: str = ""

@app.post("/chat")
async def chat(req: ChatRequest):
    if APP_PASSWORD and req.token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    module = req.module if req.module != "auto" else route(req.message)
    system = get_system(module)

    messages = [{"role": "system", "content": system}]
    for t in req.history[-12:]:
        messages.append({"role": t["role"], "content": t["content"]})
    messages.append({"role": "user", "content": req.message})

    headers, payload = await groq_chat(messages, stream=False)

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{GROQ_BASE}/chat/completions", headers=headers, json=payload)
        data = r.json()

    if "error" in data:
        return JSONResponse({"error": data["error"]["message"]}, status_code=500)

    reply = data["choices"][0]["message"]["content"]

    if module == "home":
        await _execute_ha(reply)

    # Persist to Supabase
    asyncio.create_task(_persist_message(req.message, reply, module))

    return {"reply": reply, "module": module, "timestamp": datetime.now().isoformat()}

# ── WebSocket streaming ───────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    history = []
    authed = not APP_PASSWORD

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            # Auth handshake
            if not authed:
                if data.get("token") == APP_PASSWORD:
                    authed = True
                    await ws.send_text(json.dumps({"type": "auth_ok"}))
                else:
                    await ws.send_text(json.dumps({"type": "auth_fail"}))
                continue

            msg = data.get("message", "")
            if not msg:
                continue

            module = route(msg)
            system = get_system(module)

            messages = [{"role": "system", "content": system}]
            messages += history[-12:]
            messages.append({"role": "user", "content": msg})

            headers, payload = await groq_chat(messages, stream=True)

            full = ""
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", f"{GROQ_BASE}/chat/completions",
                                         headers=headers, json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            await ws.send_text(json.dumps({"done": True, "module": module}))
                            break
                        try:
                            d = json.loads(chunk)
                            token = d["choices"][0].get("delta", {}).get("content", "")
                            if token:
                                full += token
                                await ws.send_text(json.dumps({"token": token, "module": module, "done": False}))
                        except:
                            pass

            history.append({"role": "user",      "content": msg})
            history.append({"role": "assistant",  "content": full})
            history = history[-24:]

            if module == "home":
                await _execute_ha(full)

            asyncio.create_task(_persist_message(msg, full, module))

    except WebSocketDisconnect:
        pass

# ── Voice: transcribe with Groq Whisper (free) ───────────────────────────────
@app.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not configured"}

    audio_bytes = await file.read()
    ext = file.filename.split(".")[-1] if file.filename else "webm"

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{GROQ_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": (f"audio.{ext}", audio_bytes, f"audio/{ext}")},
            data={"model": GROQ_WHISPER, "language": "en"},
        )
    data = r.json()
    return {"text": data.get("text", "").strip()}

# ── Home Assistant ────────────────────────────────────────────────────────────
async def _execute_ha(reply: str):
    import re
    if not HA_TOKEN or not HA_URL:
        return
    match = re.search(r'\{.*?"ha_action".*?\}', reply, re.DOTALL)
    if not match:
        return
    try:
        action = json.loads(match.group())
        svc_map = {
            "turn_on":         ("homeassistant", "turn_on"),
            "turn_off":        ("homeassistant", "turn_off"),
            "set_temperature": ("climate",       "set_temperature"),
            "lock":            ("lock",          "lock"),
            "unlock":          ("lock",          "unlock"),
        }
        domain, svc = svc_map.get(action["ha_action"], ("homeassistant", "turn_on"))
        body = {"entity_id": action.get("entity", "")}
        if "value" in action:
            body["temperature"] = action["value"]
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{HA_URL}/api/services/{domain}/{svc}",
                         headers={"Authorization": f"Bearer {HA_TOKEN}"}, json=body)
    except Exception as e:
        print(f"HA error: {e}")

# ── Supabase persistence ──────────────────────────────────────────────────────
async def _persist_message(user_msg: str, ai_reply: str, module: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                f"{SUPABASE_URL}/rest/v1/conversations",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={
                    "user_message": user_msg,
                    "ai_reply":     ai_reply,
                    "module":       module,
                    "created_at":   datetime.now().isoformat(),
                },
            )
    except:
        pass  # Don't crash if DB is unavailable

# ── Data endpoints (health/planning) ─────────────────────────────────────────
class LogEntry(BaseModel):
    type: str       # meal | workout | sleep | weight | task | habit
    data: dict
    token: str = ""

@app.post("/log")
async def log_entry(entry: LogEntry):
    if APP_PASSWORD and entry.token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if SUPABASE_URL and SUPABASE_KEY:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                f"{SUPABASE_URL}/rest/v1/logs",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={"type": entry.type, "data": entry.data, "created_at": datetime.now().isoformat()},
            )
    return {"status": "logged", "type": entry.type}

@app.get("/logs/{log_type}")
async def get_logs(log_type: str, token: str = "", limit: int = 50):
    if APP_PASSWORD and token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not SUPABASE_URL:
        return {"logs": [], "note": "Supabase not configured"}
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(
            f"{SUPABASE_URL}/rest/v1/logs",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={"type": f"eq.{log_type}", "order": "created_at.desc", "limit": limit},
        )
    return {"logs": r.json()}

# ── Health / keep-alive ───────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/status")
async def status():
    return {
        "status":     "online",
        "model":      GROQ_MODEL,
        "groq_ready": bool(GROQ_API_KEY),
        "ha_ready":   bool(HA_TOKEN),
        "db_ready":   bool(SUPABASE_URL),
        "modules":    list(MODULES.keys()),
        "timestamp":  datetime.now().isoformat(),
    }

# ── Serve frontend ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    html_file = Path(__file__).parent.parent / "static" / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text())
    return HTMLResponse("<h1>ARIA is running. Static files not found.</h1>")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
