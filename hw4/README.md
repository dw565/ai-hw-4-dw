# Campus Customs — AI Shop Assistant (Homework 4)

A customer website for **Campus Customs**, Yale's Bulldog Blue store, with a
helpful chatbot. Shoppers can browse products, create an account, chat about
merch, see matching items appear on the page, and get honest price and stock
answers straight from a local SQLite database.

- **Frontend:** React + Vite + TypeScript (8-bit Yale theme)
- **Backend:** Python FastAPI, whose brain is a PydanticAI agent using
  `gpt-5.6-luna` through Portkey

Full system documentation is in [`output/harness.md`](output/harness.md).

## Folder layout

```
hw4/
├── AI_prompts.md          # prompts used for each problem (vibe-coding log)
├── requirements.txt       # Python dependencies
├── .env.example           # copy to .env and fill in (never commit .env)
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app — run with: uvicorn main:app --reload --port 8000
│   ├── agent.py           # PydanticAI agent wiring + one chat turn
│   ├── tools.py           # agent tools (search, details, stock, alternatives)
│   ├── models.py          # Pydantic / PydanticAI structured types
│   ├── prompts/prompt.md  # system prompt
│   └── auth.py, db.py, memory.py, safety.py, audit.py   # accounts, data, chat memory, safety checks, audit log
├── tests/                 # app_check.py (live browser check), safety_check.py
├── output/                # harness.md, design.md, usability.md, app_check.html (+ images), audit_trail.json
└── data/                  # LOCAL ONLY, not in git (see below)
```

## 1. Add the local data pack (not in git)

The database and product photos are **not** in this repo. Download the course
`data.zip` and unzip it **inside this `hw4/` folder** so you have:

```
hw4/data/
├── campus_customs.db      # catalogue, inventory, users, chat_messages
└── products/              # product images referenced by the catalogue
```

`data/` is listed in `.gitignore`, so it stays local. The backend reads
`hw4/data/campus_customs.db` and serves images from `hw4/data/products/`.

## 2. Configure the API key

```bash
cp .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY` to your key. Optional settings:
- `SESSION_SECRET`: keeps logins valid across server restarts.
- `CHAT_MODEL`: overrides the model (default `gpt-5.6-luna`).

`.env` is git-ignored. Never commit it.

## 3. Install dependencies

Requires Python 3.12+ and Node 20+.

```bash
# from hw4/
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

## 4. Run the backend and frontend

Use two terminals, both starting in `hw4/`.

**Backend** (FastAPI + agent, port 8000):
```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend** (Vite dev server, port 5173):
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server forwards `/api` and
`/images` requests to the backend at `http://127.0.0.1:8000`. If you run the
backend on a different port, start the frontend with
`BACKEND_PORT=<port> npm run dev`.

Seed test account: `test@campuscustoms.yale.edu` / `password` (or create a
new account on the site).

## 5. Optional: run the checks

With both servers running:

```bash
python -m playwright install chromium   # first time only
python tests/app_check.py                # live app check → output/app_check.html
python tests/safety_check.py             # safety, limits and audit-trail checks
```

## What to look at

| File | What it shows |
|---|---|
| `output/harness.md` | Architecture, models, tools, safety rules and enforcement, limits, audit trail, how to run |
| `output/usability.md` | The 4 usability improvements |
| `output/design.md` | The 8-bit Yale design and why it helps |
| `output/app_check.html` | Live app check with screenshots (open in a browser) |
| `output/audit_trail.json` | Append-only log of agent-loop steps (time, tool, args, result, stop reason) |
| `AI_prompts.md` | Prompts used for each problem and what needed fixing |
