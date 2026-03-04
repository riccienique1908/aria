# ARIA Cloud — Personal AI
### Free forever · Runs 24/7 · iPhone + any browser · No PC needed

---

## Total cost: $0/month

| Service | What it does | Cost |
|---|---|---|
| **Groq** | AI brain — Llama 3.3 70B (smarter than GPT-3.5) | FREE |
| **Groq Whisper** | Voice transcription | FREE |
| **Render** | Hosts the ARIA server 24/7 | FREE |
| **Supabase** | Stores your conversations & logs | FREE |
| **UptimeRobot** | Keeps Render awake (pings every 5 min) | FREE |

---

## Deploy in 6 steps (~20 minutes)

### Step 1 — Get your free Groq API key

1. Go to **https://console.groq.com**
2. Sign up (no credit card needed)
3. Click **API Keys → Create API Key**
4. Copy the key — starts with `gsk_...`

> Groq gives you **14,400 requests/day free** on Llama 3.3 70B.
> That's 400+ conversations per day — more than enough.

---

### Step 2 — Create free Supabase database

1. Go to **https://supabase.com** → Sign up free
2. New Project → choose a name and password
3. Once created, go to **SQL Editor** and run:

```sql
create table conversations (
  id bigserial primary key,
  user_message text,
  ai_reply text,
  module text,
  created_at timestamptz default now()
);

create table logs (
  id bigserial primary key,
  type text,
  data jsonb,
  created_at timestamptz default now()
);
```

4. Go to **Settings → API** and copy:
   - **Project URL** (looks like `https://abcxyz.supabase.co`)
   - **anon public** key

---

### Step 3 — Push to GitHub

1. Create a free account at **https://github.com** if you don't have one
2. Create a new repository called `aria` (can be **private**)
3. Upload all files from this folder, or use Git:

```bash
# In the aria-cloud folder:
git init
git add .
git commit -m "ARIA cloud setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/aria.git
git push -u origin main
```

---

### Step 4 — Deploy on Render (free)

1. Go to **https://render.com** → Sign up free (use GitHub login)
2. Click **New → Web Service**
3. Connect your GitHub repo `aria`
4. Settings:
   - **Name:** `aria-personal-ai`
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Click **Create Web Service**
6. Wait ~3 minutes for first deploy

Your ARIA URL will be: `https://aria-personal-ai.onrender.com`

---

### Step 5 — Add environment variables in Render

Go to your Render service → **Environment** tab → Add these:

```
GROQ_API_KEY          = gsk_your_key_here
GROQ_MODEL            = llama-3.3-70b-versatile
SUPABASE_URL          = https://your-project.supabase.co
SUPABASE_ANON_KEY     = your_anon_key_here
APP_PASSWORD          = pick_any_password_you_want
RENDER_EXTERNAL_URL   = https://aria-personal-ai.onrender.com
```

Optional (for smart home):
```
HA_URL                = https://your-ha-instance.com
HA_TOKEN              = your_home_assistant_token
```

Click **Save Changes** — Render will redeploy automatically.

---

### Step 6 — Keep ARIA awake (prevents Render sleeping)

Render's free tier sleeps after 15 minutes of no traffic.
Fix it for free with UptimeRobot:

1. Go to **https://uptimerobot.com** → Sign up free
2. **Add New Monitor:**
   - Type: **HTTP(s)**
   - Friendly Name: `ARIA Keep-Alive`
   - URL: `https://aria-personal-ai.onrender.com/healthz`
   - Monitoring Interval: **5 minutes**
3. Click **Create Monitor**

ARIA will now stay awake 24/7 at no cost.

---

## Access from your iPhone

1. Open Safari on your iPhone
2. Go to: `https://aria-personal-ai.onrender.com`
3. Enter your APP_PASSWORD
4. Tap the **Share button → Add to Home Screen**
5. ARIA now has its own icon — works like a native app

**Voice:** Tap the 🎙️ button → speak → ARIA transcribes and replies.
First time: Safari will ask for microphone permission — tap Allow.

---

## Access from anywhere

| Device | How |
|---|---|
| iPhone (as app) | Add to Home Screen → tap icon |
| iPhone (browser) | Open your Render URL in Safari |
| Android | Same URL in Chrome → Add to Home Screen |
| PC/Mac | Open your Render URL in any browser |
| Any device | Same URL — no install needed |

---

## How to use ARIA

### QA work
- *"Write Playwright tests for a login form"*
- *"Triage this bug: [paste bug description]"*
- *"Generate a test plan for the checkout feature"*
- *"Review my test coverage for the auth module"*

### Health & fitness
- *"Give me a 20-minute home workout"*
- *"I just ate chicken and rice — log it"*
- *"How many calories should I eat to lose weight?"*
- *"Create a weekly meal prep plan"*

### Daily planning
- *"What should I focus on today?"*
- *"Add a task: finish regression tests by Friday"*
- *"Set up a habit: drink 2L of water daily"*

### Smart home (if Home Assistant connected)
- *"Turn off the living room lights"*
- *"Set the thermostat to 70°F"*
- *"Lock the front door"*

---

## Upgrading later (still under $10)

If you want more power or no sleep delay:

| Upgrade | Cost | What you get |
|---|---|---|
| Render Starter | $7/month | No sleep, faster cold start |
| Groq paid | ~$2-5/month | Higher rate limits |
| Supabase Pro | $25/month | More storage (free is enough for personal use) |

**Recommended upgrade path:** Render Starter ($7/month) gives you always-on 
service with no spin-up delay. Still under your $10 budget.

---

## Troubleshooting

**"Service unavailable" when opening URL**
→ First deploy takes 3-5 minutes. Wait and refresh.
→ Check Render logs: Dashboard → your service → Logs

**AI not responding**
→ Check GROQ_API_KEY is set in Render environment variables
→ Visit `https://your-app.onrender.com/status` to see what's connected

**Voice not working on iPhone**
→ Must use Safari (Chrome on iOS doesn't support mic in web apps)
→ Go to iPhone Settings → Safari → Microphone → Allow

**ARIA falls asleep (slow first response)**
→ Set up UptimeRobot (Step 6) — fixes this permanently

**Wrong password / locked out**
→ In Render environment variables, change APP_PASSWORD
→ Or set it to empty string to remove password protection
