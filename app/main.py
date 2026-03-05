"""
<<<<<<< HEAD
ARIA v4 — Definitive fixes
===========================
Image gen : gemini-2.0-flash-exp-image-generation via generateContent
            Correct payload + robust response parsing
Voice     : /voice/conversation — Whisper → LLM → Orpheus in ONE request
            Returns base64 WAV + transcript + reply together
            Browser SpeechSynthesis fallback if Orpheus terms not yet accepted
=======
ARIA Cloud Brain v2
===================
Fixes:
  ✅ Persistent memory — remembers you across sessions via Supabase
  ✅ Image analysis — Llama 4 Scout vision (free, Groq)
  ✅ Real AI voice — Orpheus TTS (free, Groq) + Whisper STT
  ✅ Image generation — Gemini 2.5 Flash / Nano Banana (free, Google AI Studio)
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
"""

import os, json, asyncio, base64, re
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

<<<<<<< HEAD
import httpx, uvicorn
from fastapi import (FastAPI, WebSocket, WebSocketDisconnect,
                     UploadFile, File, Header, Depends, HTTPException)
=======
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD
GROQ_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_CHAT   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_STT    = "whisper-large-v3-turbo"
GROQ_TTS    = "canopylabs/orpheus-v1-english"
GROQ_VOICE  = os.getenv("ARIA_VOICE", "dan")   # autumn|diana|hannah|austin|daniel|troy|dan
GROQ_BASE   = "https://api.groq.com/openai/v1"

GEMINI_KEY  = os.getenv("GEMINI_API_KEY", "")
# ✅ Confirmed working free-tier model + endpoint
GEMINI_IMG  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp-image-generation:generateContent"

SB_URL  = os.getenv("SUPABASE_URL", "")
SB_ANON = os.getenv("SUPABASE_ANON_KEY", "")
SB_SVC  = os.getenv("SUPABASE_SERVICE_KEY", "")
PORT    = int(os.getenv("PORT", 8000))

# ── Lifespan / keep-alive ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def _ping():
=======
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
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
        url = os.getenv("RENDER_EXTERNAL_URL", "")
        if not url: return
        while True:
            await asyncio.sleep(240)
            try:
                async with httpx.AsyncClient() as c:
                    await c.get(f"{url}/healthz", timeout=5)
            except: pass
<<<<<<< HEAD
    asyncio.create_task(_ping())
    yield

app = FastAPI(title="ARIA v4", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_static = Path(__file__).parent.parent / "static"
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

# ── DB / auth helpers ─────────────────────────────────────────────────────────
def _gh():
    return {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}

def _sbh(jwt: str, svc: bool = False):
    k = SB_SVC if svc else SB_ANON
    return {"apikey": k, "Authorization": f"Bearer {jwt if not svc else k}",
            "Content-Type": "application/json", "Prefer": "return=representation"}

async def _get(table, params, jwt):
    if not SB_URL: return []
    async with httpx.AsyncClient(timeout=8) as c:
        r = await c.get(f"{SB_URL}/rest/v1/{table}", headers=_sbh(jwt), params=params)
        d = r.json(); return d if isinstance(d, list) else []

async def _post(table, data, jwt):
    if not SB_URL: return {}
    async with httpx.AsyncClient(timeout=8) as c:
        r = await c.post(f"{SB_URL}/rest/v1/{table}", headers=_sbh(jwt), json=data)
        d = r.json(); return d[0] if isinstance(d, list) and d else {}

async def _patch(table, data, match, jwt):
    if not SB_URL: return
    async with httpx.AsyncClient(timeout=8) as c:
        await c.patch(f"{SB_URL}/rest/v1/{table}", headers=_sbh(jwt),
                      params={k: f"eq.{v}" for k, v in match.items()}, json=data)

async def _del(table, match, jwt):
    if not SB_URL: return
    async with httpx.AsyncClient(timeout=8) as c:
        await c.delete(f"{SB_URL}/rest/v1/{table}", headers=_sbh(jwt),
                       params={k: f"eq.{v}" for k, v in match.items()})

async def get_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "): return {}
    jwt = authorization[7:]
    if not SB_URL: return {"id": "local", "jwt": jwt}
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{SB_URL}/auth/v1/user",
                        headers={"apikey": SB_ANON, "Authorization": f"Bearer {jwt}"})
        if r.status_code != 200: return {}
        u = r.json(); u["jwt"] = jwt; return u

# ── Module routing + system prompt ───────────────────────────────────────────
_MODS = {
    "work":     ["test","bug","qa","regression","playwright","jira","ticket","sprint","code","review","selenium","defect"],
    "home":     ["light","device","thermostat","temperature","lock","door","turn on","turn off","fan"],
    "health":   ["workout","exercise","sleep","weight","fitness","run","gym","calories burned","steps"],
    "food":     ["eat","food","meal","recipe","calories","nutrition","protein","breakfast","lunch","dinner","snack"],
    "planning": ["remind","schedule","calendar","todo","task","meeting","plan","agenda","tomorrow"],
=======
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
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
}

def _route(msg):
    lo = msg.lower()
    s = {m: sum(1 for kw in kws if kw in lo) for m, kws in _MODS.items()}
    b = max(s, key=s.get); return b if s[b] > 0 else "general"

<<<<<<< HEAD
def _skill_match(msg, skills):
    lo = msg.lower()
    return [s for s in skills if s.get("is_active") and
            any(w.lower() in lo for w in (s.get("trigger_words") or []))]

def _sys(module, profile, skills, voice=False):
    today = datetime.now().strftime("%A, %B %d, %Y")
    name  = profile.get("display_name", "")
    facts = [x for x in [
        f"Name: {name}" if name else None,
        f"Weight: {profile['weight_kg']}kg" if profile.get("weight_kg") else None,
        f"Daily calorie goal: {profile['daily_cal_goal']} kcal" if profile.get("daily_cal_goal") else None,
        f"Daily protein goal: {profile['daily_protein_g']}g" if profile.get("daily_protein_g") else None,
        f"Current goal: {profile['latest_goal']}" if profile.get("latest_goal") else None,
        f"QA stack: {profile['qa_stack']}" if profile.get("qa_stack") else None,
        f"Notes: {profile['notes']}" if profile.get("notes") else None,
    ] if x]
    mem = ("\n\nUser profile:\n" + "\n".join(f"- {f}" for f in facts)) if facts else ""
    sk  = ("\n\nActive skills:\n" + "\n".join(f"[{s['name']}]: {s['system_prompt']}" for s in skills)) if skills else ""
    vn  = "\n\nVOICE MODE: Keep reply to 2-3 sentences max. No markdown, no lists, no code blocks. Speak naturally." if voice else ""
    base = f"Today is {today}. {'The user is '+name+'. ' if name else ''}You are ARIA, a personal AI assistant.{mem}{sk}{vn}\n\n"
    ex = {
        "work":     "You are a QA engineering expert. Be technical and precise.",
        "home":     'For HA actions output JSON: {"ha_action":"turn_on"|"turn_off","entity":"id"}',
        "health":   "You are a health coach. Be encouraging and data-driven.",
        "food":     "You are a nutrition coach. Be practical with meals and macros.",
        "planning": "You are a productivity assistant. Help with tasks and scheduling.",
        "general":  "Be helpful, direct, and concise.",
=======
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
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
    }
    return base + ex.get(module, ex["general"])

<<<<<<< HEAD
async def _ctx(uid, jwt, msg):
    profile = await _get("profiles", {"id": f"eq.{uid}"}, jwt)
    profile = profile[0] if profile else {}
    history = await _get("conversations",
                         {"user_id": f"eq.{uid}", "order": "created_at.desc", "limit": "16"}, jwt)
    history = list(reversed(history))
    skills  = await _get("skills", {"is_active": "eq.true"}, jwt)
    return profile, history, _skill_match(msg, skills)

def _build_msgs(system, db_hist, sess, msg):
    out = [{"role": "system", "content": system}]
    for row in db_hist[-8:]:
        out += [{"role":"user","content":row.get("user_message","")},
                {"role":"assistant","content":row.get("ai_reply","")}]
    out += sess[-8:]
    out.append({"role":"user","content":msg})
    return out

# ── Auth endpoints ────────────────────────────────────────────────────────────
class _AR(BaseModel):
    email: str; password: str; display_name: str = ""

@app.post("/auth/signup")
async def signup(req: _AR):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{SB_URL}/auth/v1/signup",
                         headers={"apikey": SB_ANON, "Content-Type": "application/json"},
                         json={"email": req.email, "password": req.password,
                               "data": {"display_name": req.display_name or req.email.split("@")[0]}})
    d = r.json()
    if "error" in d: return JSONResponse({"error": d["error"]}, status_code=400)
    return {"message": "Check your email to confirm, then sign in."}

@app.post("/auth/login")
async def login(req: _AR):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{SB_URL}/auth/v1/token?grant_type=password",
                         headers={"apikey": SB_ANON, "Content-Type": "application/json"},
                         json={"email": req.email, "password": req.password})
    d = r.json()
    if "error" in d: return JSONResponse({"error": d.get("error_description", d["error"])}, status_code=401)
    return {"access_token": d["access_token"], "user": d.get("user", {})}

@app.post("/auth/logout")
async def logout(user: dict = Depends(get_user)):
    if user and SB_URL:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{SB_URL}/auth/v1/logout",
                         headers={"apikey": SB_ANON, "Authorization": f"Bearer {user.get('jwt','')}"})
    return {"ok": True}

# ── Profile ───────────────────────────────────────────────────────────────────
@app.get("/profile")
async def get_profile(user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    rows = await _get("profiles", {"id": f"eq.{user['id']}"}, user["jwt"])
    return rows[0] if rows else {}

@app.patch("/profile")
async def update_profile(body: dict, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    body.pop("id", None); body.pop("role", None)
    body["updated_at"] = datetime.now().isoformat()
    await _patch("profiles", body, {"id": user["id"]}, user["jwt"])
    return {"status": "saved"}

# ── Skills ────────────────────────────────────────────────────────────────────
@app.get("/skills")
async def list_skills(user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    own  = await _get("skills", {"owner_id": f"eq.{user['id']}"}, user["jwt"])
    glob = await _get("skills", {"is_global": "eq.true"}, user["jwt"])
    seen = set(); out = []
    for s in own + glob:
        if s["id"] not in seen: seen.add(s["id"]); out.append(s)
    return out

@app.post("/skills")
async def create_skill(body: dict, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    if body.get("is_global"):
        p = await get_profile(user)
        if p.get("role") != "admin": body["is_global"] = False
    body["owner_id"] = user["id"]
    return await _post("skills", body, user["jwt"])

@app.patch("/skills/{sid}")
async def update_skill(sid: int, body: dict, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    body.pop("owner_id", None)
    await _patch("skills", body, {"id": sid, "owner_id": user["id"]}, user["jwt"])
    return {"status": "updated"}

@app.delete("/skills/{sid}")
async def delete_skill(sid: int, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    await _del("skills", {"id": sid, "owner_id": user["id"]}, user["jwt"])
    return {"status": "deleted"}

# ── Chat REST ─────────────────────────────────────────────────────────────────
class _CR(BaseModel):
    message: str; history: list = []; module: str = "auto"
=======
# ── Groq chat ─────────────────────────────────────────────────────────────────
def groq_headers():
    return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

# ── REST chat ─────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []
    module: str = "auto"
    token: str = ""
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439

@app.post("/chat")
async def chat(req: _CR, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    module = _route(req.message) if req.module == "auto" else req.module
    profile, db_hist, skills = await _ctx(user["id"], user["jwt"], req.message)
    msgs = _build_msgs(_sys(module, profile, skills), db_hist, req.history, req.message)
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/chat/completions", headers=_gh(),
                         json={"model": GROQ_CHAT, "messages": msgs, "max_tokens": 1024})
    d = r.json()
    if "error" in d: return JSONResponse({"error": d["error"]["message"]}, status_code=500)
    reply = d["choices"][0]["message"]["content"]
    asyncio.create_task(_post("conversations",
        {"user_id": user["id"], "user_message": req.message, "ai_reply": reply, "module": module},
        user["jwt"]))
    return {"reply": reply, "module": module, "skills_used": [s["name"] for s in skills]}

<<<<<<< HEAD
# ── Chat WebSocket ─────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    user = {}; sess = []
=======
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

>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)
<<<<<<< HEAD
            if data.get("type") == "auth":
                jwt = data.get("jwt", "")
                async with httpx.AsyncClient(timeout=5) as c:
                    r = await c.get(f"{SB_URL}/auth/v1/user",
                                    headers={"apikey": SB_ANON, "Authorization": f"Bearer {jwt}"})
                if r.status_code == 200:
                    user = r.json(); user["jwt"] = jwt
                    await ws.send_text(json.dumps({"type": "auth_ok"}))
                else:
                    await ws.send_text(json.dumps({"type": "auth_fail"}))
                continue
            if not user: continue
            msg = data.get("message", "")
            if not msg: continue
            module = _route(msg)
            profile, db_hist, skills = await _ctx(user["id"], user["jwt"], msg)
            msgs = _build_msgs(_sys(module, profile, skills), db_hist, sess, msg)
            full = ""
            async with httpx.AsyncClient(timeout=60) as c:
                async with c.stream("POST", f"{GROQ_BASE}/chat/completions", headers=_gh(),
                                    json={"model": GROQ_CHAT, "messages": msgs,
                                          "stream": True, "max_tokens": 1024}) as resp:
=======

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
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "): continue
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            await ws.send_text(json.dumps(
                                {"done": True, "module": module,
                                 "skills": [s["name"] for s in skills]}))
                            break
                        try:
<<<<<<< HEAD
                            tok = json.loads(chunk)["choices"][0].get("delta",{}).get("content","")
                            if tok:
                                full += tok
                                await ws.send_text(json.dumps({"token": tok, "done": False}))
                        except: pass
            sess += [{"role":"user","content":msg},{"role":"assistant","content":full}]
            sess = sess[-20:]
            asyncio.create_task(_post("conversations",
                {"user_id": user["id"], "user_message": msg, "ai_reply": full, "module": module},
                user["jwt"]))
    except WebSocketDisconnect: pass

# ── ✅ Voice conversation — full pipeline in one request ───────────────────────
@app.post("/voice/conversation")
async def voice_conversation(file: UploadFile = File(...),
                             authorization: str = Header(default="")):
    """
    Whisper STT → Groq LLM → Orpheus TTS  — all in one server round-trip.
    Returns JSON: { transcript, reply, audio_b64, module, skills, tts_ok }
    audio_b64 is null if Orpheus TTS fails (terms not accepted) — client falls
    back to browser SpeechSynthesis automatically.
    """
    user = {}
    if authorization.startswith("Bearer ") and SB_URL:
        jwt = authorization[7:]
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{SB_URL}/auth/v1/user",
                            headers={"apikey": SB_ANON, "Authorization": f"Bearer {jwt}"})
            if r.status_code == 200: user = r.json(); user["jwt"] = jwt

    # 1 — Whisper STT
    audio = await file.read()
    ext   = (file.filename or "a.webm").rsplit(".", 1)[-1]
    async with httpx.AsyncClient(timeout=30) as c:
        stt = await c.post(f"{GROQ_BASE}/audio/transcriptions",
                           headers={"Authorization": f"Bearer {GROQ_KEY}"},
                           files={"file": (f"a.{ext}", audio, f"audio/{ext}")},
                           data={"model": GROQ_STT, "language": "en"})
    transcript = stt.json().get("text", "").strip()
    if not transcript or len(transcript) < 2:
        return JSONResponse({"error": "no_speech", "transcript": ""})

    # 2 — LLM
    profile, db_hist, skills = {}, [], []
    if user:
        try: profile, db_hist, skills = await _ctx(user["id"], user["jwt"], transcript)
        except: pass
    module = _route(transcript)
    msgs   = _build_msgs(_sys(module, profile, skills, voice=True), db_hist, [], transcript)
    async with httpx.AsyncClient(timeout=30) as c:
        llm = await c.post(f"{GROQ_BASE}/chat/completions", headers=_gh(),
                           json={"model": GROQ_CHAT, "messages": msgs, "max_tokens": 180})
    ld = llm.json()
    if "error" in ld:
        return JSONResponse({"error": ld["error"]["message"]}, status_code=500)
    reply = ld["choices"][0]["message"]["content"]
    if user:
        asyncio.create_task(_post("conversations",
            {"user_id": user["id"], "user_message": transcript,
             "ai_reply": reply, "module": module}, user["jwt"]))

    # 3 — Orpheus TTS
    speech = re.sub(r'[*_`#\[\]()\n]+', ' ', reply).strip()
    speech = re.sub(r'\s+', ' ', speech)[:700]
    tts_ok = False; audio_b64 = None

    async with httpx.AsyncClient(timeout=40) as c:
        tts = await c.post(f"{GROQ_BASE}/audio/speech", headers=_gh(),
                           json={"model": GROQ_TTS, "input": speech,
                                 "voice": GROQ_VOICE, "response_format": "wav"})
    if tts.status_code == 200:
        audio_b64 = base64.b64encode(tts.content).decode()
        tts_ok = True
    else:
        # Log the error so frontend can show a useful hint
        print(f"[TTS ERROR {tts.status_code}]: {tts.text[:300]}")

    return JSONResponse({
        "transcript": transcript,
        "reply":      reply,
        "audio_b64":  audio_b64,
        "tts_ok":     tts_ok,
        "tts_error":  None if tts_ok else tts.text[:200],
        "module":     module,
        "skills":     [s["name"] for s in skills],
    })

# ── STT only ──────────────────────────────────────────────────────────────────
@app.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio = await file.read()
    ext   = (file.filename or "a.webm").rsplit(".", 1)[-1]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/audio/transcriptions",
                         headers={"Authorization": f"Bearer {GROQ_KEY}"},
                         files={"file": (f"a.{ext}", audio, f"audio/{ext}")},
                         data={"model": GROQ_STT, "language": "en"})
    return {"text": r.json().get("text", "").strip()}

# ── TTS only ──────────────────────────────────────────────────────────────────
@app.post("/voice/speak")
async def speak(body: dict, user: dict = Depends(get_user)):
    text  = re.sub(r'[*_`#\n]+', ' ', body.get("text", ""))[:800].strip()
    voice = body.get("voice", GROQ_VOICE)
    if not text: return JSONResponse({"error": "no text"}, status_code=400)
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/audio/speech", headers=_gh(),
                         json={"model": GROQ_TTS, "input": text,
                               "voice": voice, "response_format": "wav"})
    if r.status_code != 200:
        return JSONResponse({"error": r.text[:200]}, status_code=500)
    return Response(content=r.content, media_type="audio/wav")

# ── Vision ────────────────────────────────────────────────────────────────────
@app.post("/vision/analyze")
async def analyze(file: UploadFile = File(...),
                  prompt: str = "Describe this image in detail.",
                  user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    img  = await file.read()
    b64  = base64.b64encode(img).decode()
    mime = file.content_type or "image/jpeg"
    msgs = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        {"type": "text", "text": prompt}
    ]}]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GROQ_BASE}/chat/completions", headers=_gh(),
                         json={"model": GROQ_VISION, "messages": msgs, "max_tokens": 1024})
    d = r.json()
    if "error" in d: return JSONResponse({"error": d["error"]["message"]}, status_code=500)
    return {"analysis": d["choices"][0]["message"]["content"]}

# ── ✅ Image generation — definitive fix ──────────────────────────────────────
@app.post("/image/generate")
async def gen_image(body: dict, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    prompt = body.get("prompt", "").strip()
    if not prompt:
        return JSONResponse({"error": "No prompt provided."}, status_code=400)
    if not GEMINI_KEY:
        return JSONResponse({
            "error": "GEMINI_API_KEY is not set.",
            "fix": "Add GEMINI_API_KEY in Render → Environment. Get a free key at aistudio.google.com"
        }, status_code=500)

    url     = f"{GEMINI_IMG}?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(url, json=payload, headers={"Content-Type": "application/json"})

    if r.status_code != 200:
        # Return the full Gemini error so we can see exactly what's wrong
        try:
            err = r.json()
        except Exception:
            err = {"raw": r.text[:500]}
        return JSONResponse({
            "error": f"Gemini returned HTTP {r.status_code}",
            "gemini_error": err
        }, status_code=500)

    data = r.json()

    # ✅ Robust parsing — Gemini may return text parts before the image part
=======
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
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inlineData" in part:
<<<<<<< HEAD
                mime = part["inlineData"]["mimeType"]
                b64  = part["inlineData"]["data"]
                return {
                    "image_url": f"data:{mime};base64,{b64}",
                    "mime_type": mime
                }
        # No inlineData found — collect any text Gemini returned for debugging
        texts = [p.get("text", "") for p in parts if "text" in p]
        return JSONResponse({
            "error": "Gemini responded but returned no image.",
            "gemini_text": " ".join(texts),
            "hint": "This usually means the prompt was blocked by safety filters. Try rephrasing."
        }, status_code=500)
    except (KeyError, IndexError) as e:
        return JSONResponse({
            "error": f"Unexpected Gemini response structure: {e}",
            "raw": str(data)[:600]
        }, status_code=500)

# ── Admin ─────────────────────────────────────────────────────────────────────
@app.get("/admin/users")
async def admin_list(user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    p = await get_profile(user)
    if p.get("role") != "admin": raise HTTPException(403)
    return await _get("profiles", {"order": "created_at.asc"}, user["jwt"])

@app.patch("/admin/users/{uid}")
async def admin_update(uid: str, body: dict, user: dict = Depends(get_user)):
    if not user: raise HTTPException(401)
    p = await get_profile(user)
    if p.get("role") != "admin": raise HTTPException(403)
    allowed = {k: v for k, v in body.items() if k in ["role", "display_name"]}
    if SB_SVC: await _patch("profiles", allowed, {"id": uid}, SB_SVC)
    return {"status": "updated"}
=======
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
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/status")
async def status():
    return {
<<<<<<< HEAD
        "version": "4.0",
        "groq_ready":   bool(GROQ_KEY),
        "gemini_ready": bool(GEMINI_KEY),
        "db_ready":     bool(SB_URL),
        "tts_voice":    GROQ_VOICE,
        "img_model":    "gemini-2.0-flash-exp-image-generation",
=======
        "status":        "online",
        "chat_model":    GROQ_CHAT_MODEL,
        "vision_model":  GROQ_VISION_MODEL,
        "tts_model":     GROQ_TTS_MODEL,
        "tts_voice":     GROQ_TTS_VOICE,
        "groq_ready":    bool(GROQ_API_KEY),
        "gemini_ready":  bool(GEMINI_API_KEY),
        "db_ready":      bool(SUPABASE_URL),
        "timestamp":     datetime.now().isoformat(),
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    f = Path(__file__).parent.parent / "static" / "index.html"
<<<<<<< HEAD
    return HTMLResponse(f.read_text() if f.exists() else "<h1>ARIA v4</h1>")
=======
    return HTMLResponse(f.read_text() if f.exists() else "<h1>ARIA v2 running</h1>")
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
