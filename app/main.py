"""
ARIA Cloud Brain v2
===================
Fixes:
  ✅ Persistent memory — remembers you across sessions via Supabase
  ✅ Image analysis — Llama 4 Scout vision (free, Groq)
  ✅ Real AI voice — Orpheus TTS (free, Groq) + Whisper STT
  ✅ Image generation — Gemini 2.5 Flash / Nano Banana (free, Google AI Studio)
"""

import os, json, asyncio, base64, re
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_CHAT_MODEL = os.getenv("GROQ_MODEL",    "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"   # Free vision
GROQ_WHISPER    = "whisper-large-v3-turbo"
GROQ_TTS_MODEL  = "canopylabs/orpheus-v1-english"
GROQ_TTS_VOICE  = os.getenv("ARIA_VOICE", "hannah")               # autumn|diana|hannah|austin|daniel|troy
GROQ_BASE       = "https://api.groq.com/openai/v1"

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")                 # Free at aistudio.google.com
GEMINI_IMG_MODEL = "gemini-2.0-flash-preview-image-generation"

SUPABASE_URL    = os.getenv("SUPABASE_URL",       "")
SUPABASE_KEY    = os.getenv("SUPABASE_ANON_KEY",  "")
APP_PASSWORD    = os.getenv("APP_PASSWORD",        "")
PORT            = int(os.getenv("PORT", 8000))

# ── Keep-alive ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def ping():
        url = os.getenv("RENDER_EXTERNAL_URL", "")
        if not url: return
        while True:
            await asyncio.sleep(240)
            try:
                async with httpx.AsyncClient() as c:
                    await c.get(f"{url}/healthz", timeout=5)
            except: pass
    asyncio.create_task(ping())
    yield

app = FastAPI(title="ARIA v2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Module routing ────────────────────────────────────────────────────────────
MODULES = {
    "work":     ["test","bug","qa","regression","playwright","jira","ticket","defect","sprint","code","review","selenium"],
    "home":     ["light","device","thermostat","temperature","lock","door","camera","home","turn on","turn off","fan"],
    "health":   ["workout","exercise","sleep","weight","heart","fitness","run","gym","calories burned","steps"],
    "food":     ["eat","food","meal","recipe","calories","nutrition","protein","carb","breakfast","lunch","dinner","snack","diet"],
    "planning": ["remind","schedule","calendar","todo","task","meeting","appointment","plan","agenda","tomorrow","today"],
}

def route(msg: str) -> str:
    lower = msg.lower()
    scores = {m: sum(1 for kw in kws if kw in lower) for m, kws in MODULES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"

# ── Supabase helpers ──────────────────────────────────────────────────────────
SB_HEADERS = lambda: {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

async def sb_get(table: str, params: dict = {}) -> list:
    if not SUPABASE_URL: return []
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/{table}",
                        headers=SB_HEADERS(), params=params)
        return r.json() if r.status_code == 200 else []

async def sb_post(table: str, data: dict):
    if not SUPABASE_URL: return
    async with httpx.AsyncClient(timeout=5) as c:
        await c.post(f"{SUPABASE_URL}/rest/v1/{table}",
                     headers=SB_HEADERS(), json=data)

async def sb_upsert(table: str, data: dict, on_conflict: str = "id"):
    if not SUPABASE_URL: return
    h = {**SB_HEADERS(), "Prefer": f"resolution=merge-duplicates,return=minimal"}
    async with httpx.AsyncClient(timeout=5) as c:
        await c.post(f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}",
                     headers=h, json=data)

# ── Memory system ─────────────────────────────────────────────────────────────
async def load_memory() -> dict:
    """Load user profile + recent conversation history from Supabase."""
    profiles = await sb_get("user_profile", {"limit": "1"})
    profile  = profiles[0] if profiles else {}

    history  = await sb_get("conversations",
                             {"order": "created_at.desc", "limit": "20"})
    history  = list(reversed(history))  # oldest first

    return {"profile": profile, "history": history}

async def save_message(user_msg: str, ai_reply: str, module: str):
    await sb_post("conversations", {
        "user_message": user_msg,
        "ai_reply":     ai_reply,
        "module":       module,
        "created_at":   datetime.now().isoformat(),
    })

async def update_profile(key: str, value):
    """Store a user fact (name, goal, preference) persistently."""
    await sb_upsert("user_profile", {"id": 1, key: value}, on_conflict="id")

async def extract_and_save_profile(user_msg: str, ai_reply: str):
    """Passively extract user facts from conversation and save them."""
    lower = user_msg.lower()
    if "my name is" in lower:
        name = user_msg.lower().split("my name is")[-1].strip().split()[0].capitalize()
        await update_profile("name", name)
    if "i weigh" in lower or "my weight is" in lower:
        nums = re.findall(r'\d+\.?\d*', user_msg)
        if nums: await update_profile("weight_kg", float(nums[0]))
    if "my goal is" in lower or "i want to" in lower:
        await update_profile("latest_goal", user_msg[:200])

def build_system_prompt(module: str, profile: dict) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    name  = profile.get("name", "")
    facts = []
    if name:                            facts.append(f"User's name: {name}")
    if profile.get("weight_kg"):        facts.append(f"Weight: {profile['weight_kg']}kg")
    if profile.get("daily_cal_goal"):   facts.append(f"Daily calorie goal: {profile['daily_cal_goal']} kcal")
    if profile.get("latest_goal"):      facts.append(f"Current goal: {profile['latest_goal']}")
    if profile.get("notes"):            facts.append(f"Notes: {profile['notes']}")

    memory_block = ""
    if facts:
        memory_block = "\n\nWhat you know about the user:\n" + "\n".join(f"- {f}" for f in facts)

    greeting = f"The user's name is {name}. " if name else ""

    base = f"Today is {today}. {greeting}You are ARIA, a personal AI assistant.{memory_block}\n\n"

    prompts = {
        "work":     base + "You are a QA engineering expert. Help with Playwright/Selenium tests, bug triage, test plans, and coverage analysis. Be technical and concise.",
        "home":     base + "You control smart home devices via Home Assistant. For actions output JSON: {\"ha_action\":\"turn_on\"|\"turn_off\"|\"set_temperature\", \"entity\":\"id\", \"value\":optional}. Then confirm in plain English.",
        "health":   base + "You are a health and fitness coach. Help with workouts, sleep, habits, and progress tracking. Be encouraging and data-driven.",
        "food":     base + "You are a nutrition coach. Help with meals, macros, recipes, and dietary goals. Be practical and specific.",
        "planning": base + "You are a personal productivity assistant. Help with tasks, scheduling, and daily planning. Be organised and proactive.",
        "general":  base + "You are ARIA, a helpful personal AI. Cover QA, home, health, food, planning, and general questions. Be direct and concise.",
    }
    return prompts.get(module, prompts["general"])

# ── Groq chat ─────────────────────────────────────────────────────────────────
def groq_headers():
    return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

# ── REST chat ─────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []
    module: str = "auto"
    token: str = ""

@app.post("/chat")
async def chat(req: ChatRequest):
    if APP_PASSWORD and req.token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    module  = req.module if req.module != "auto" else route(req.message)
    mem     = await load_memory()
    system  = build_system_prompt(module, mem["profile"])

    # Build messages: system + long-term memory + current session history
    messages = [{"role": "system", "content": system}]
    for row in mem["history"][-8:]:
        messages.append({"role": "user",      "content": row.get("user_message", "")})
        messages.append({"role": "assistant",  "content": row.get("ai_reply",    "")})
    for t in req.history[-6:]:
        messages.append({"role": t["role"], "content": t["content"]})
    messages.append({"role": "user", "content": req.message})

    payload = {"model": GROQ_CHAT_MODEL, "messages": messages,
               "stream": False, "max_tokens": 1024}

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/chat/completions",
                         headers=groq_headers(), json=payload)
    data = r.json()
    if "error" in data:
        return JSONResponse({"error": data["error"]["message"]}, status_code=500)

    reply = data["choices"][0]["message"]["content"]

    asyncio.create_task(save_message(req.message, reply, module))
    asyncio.create_task(extract_and_save_profile(req.message, reply))

    return {"reply": reply, "module": module, "timestamp": datetime.now().isoformat()}

# ── WebSocket streaming ───────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    session_history = []
    authed = not APP_PASSWORD

    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)

            if not authed:
                authed = data.get("token") == APP_PASSWORD
                await ws.send_text(json.dumps({"type": "auth_ok" if authed else "auth_fail"}))
                continue

            msg    = data.get("message", "")
            if not msg: continue

            module = route(msg)
            mem    = await load_memory()
            system = build_system_prompt(module, mem["profile"])

            messages = [{"role": "system", "content": system}]
            for row in mem["history"][-8:]:
                messages.append({"role": "user",     "content": row.get("user_message", "")})
                messages.append({"role": "assistant", "content": row.get("ai_reply",    "")})
            messages += session_history[-8:]
            messages.append({"role": "user", "content": msg})

            payload = {"model": GROQ_CHAT_MODEL, "messages": messages,
                       "stream": True, "max_tokens": 1024}
            full = ""
            async with httpx.AsyncClient(timeout=60) as c:
                async with c.stream("POST", f"{GROQ_BASE}/chat/completions",
                                    headers=groq_headers(), json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "): continue
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
                        except: pass

            session_history += [{"role": "user", "content": msg},
                                 {"role": "assistant", "content": full}]
            session_history = session_history[-20:]
            asyncio.create_task(save_message(msg, full, module))
            asyncio.create_task(extract_and_save_profile(msg, full))

    except WebSocketDisconnect: pass

# ── Voice: STT (Whisper) ──────────────────────────────────────────────────────
@app.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio = await file.read()
    ext   = (file.filename or "audio.webm").split(".")[-1]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/audio/transcriptions",
                         headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                         files={"file": (f"audio.{ext}", audio, f"audio/{ext}")},
                         data={"model": GROQ_WHISPER, "language": "en"})
    return {"text": r.json().get("text", "").strip()}

# ── Voice: TTS (Orpheus — real expressive AI voice) ───────────────────────────
@app.post("/voice/speak")
async def speak(body: dict):
    text  = body.get("text", "")[:4000]
    voice = body.get("voice", GROQ_TTS_VOICE)
    if not text:
        return JSONResponse({"error": "No text"}, status_code=400)

    payload = {"model": GROQ_TTS_MODEL, "input": text,
               "voice": voice, "response_format": "wav"}

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/audio/speech",
                         headers=groq_headers(), json=payload)

    if r.status_code != 200:
        return JSONResponse({"error": "TTS failed", "detail": r.text}, status_code=500)

    return Response(content=r.content, media_type="audio/wav")

# ── Image analysis (Llama 4 Scout vision) ─────────────────────────────────────
@app.post("/vision/analyze")
async def analyze_image(file: UploadFile = File(...), prompt: str = "Describe this image in detail."):
    img_bytes = await file.read()
    b64       = base64.b64encode(img_bytes).decode()
    mime      = file.content_type or "image/jpeg"

    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt},
        ]
    }]
    payload = {"model": GROQ_VISION_MODEL, "messages": messages, "max_tokens": 1024}

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/chat/completions",
                         headers=groq_headers(), json=payload)
    data = r.json()
    if "error" in data:
        return JSONResponse({"error": data["error"]["message"]}, status_code=500)
    return {"analysis": data["choices"][0]["message"]["content"]}

# ── Image generation (Gemini 2.5 Flash / Nano Banana — free) ──────────────────
@app.post("/image/generate")
async def generate_image(body: dict):
    prompt = body.get("prompt", "")
    token  = body.get("token",  "")
    if APP_PASSWORD and token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not prompt:
        return JSONResponse({"error": "No prompt"}, status_code=400)
    if not GEMINI_API_KEY:
        return JSONResponse({"error": "GEMINI_API_KEY not set. Get a free key at aistudio.google.com"}, status_code=500)

    url     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMG_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(url, json=payload)
    data = r.json()

    if "error" in data:
        return JSONResponse({"error": data["error"]["message"]}, status_code=500)

    # Extract image from response
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inlineData" in part:
                img_b64  = part["inlineData"]["data"]
                img_mime = part["inlineData"]["mimeType"]
                return {"image_b64": img_b64, "mime_type": img_mime,
                        "image_url": f"data:{img_mime};base64,{img_b64}"}
        return JSONResponse({"error": "No image in response"}, status_code=500)
    except (KeyError, IndexError) as e:
        return JSONResponse({"error": f"Parse error: {e}", "raw": data}, status_code=500)

# ── User profile ──────────────────────────────────────────────────────────────
@app.get("/profile")
async def get_profile(token: str = ""):
    if APP_PASSWORD and token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    profiles = await sb_get("user_profile", {"limit": "1"})
    return profiles[0] if profiles else {}

@app.post("/profile")
async def set_profile(body: dict):
    token = body.pop("token", "")
    if APP_PASSWORD and token != APP_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    await sb_upsert("user_profile", {"id": 1, **body}, on_conflict="id")
    return {"status": "saved"}

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/status")
async def status():
    return {
        "status":        "online",
        "chat_model":    GROQ_CHAT_MODEL,
        "vision_model":  GROQ_VISION_MODEL,
        "tts_model":     GROQ_TTS_MODEL,
        "tts_voice":     GROQ_TTS_VOICE,
        "groq_ready":    bool(GROQ_API_KEY),
        "gemini_ready":  bool(GEMINI_API_KEY),
        "db_ready":      bool(SUPABASE_URL),
        "timestamp":     datetime.now().isoformat(),
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    f = Path(__file__).parent.parent / "static" / "index.html"
    return HTMLResponse(f.read_text() if f.exists() else "<h1>ARIA v2 running</h1>")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
