# Freedom Ford — Dealer AI MVP

A dealership AI concierge that helps customers search inventory, sketch
realistic payments, compare vehicles, and hand off lead context to sales.

- **Customer demo**: `http://localhost:5173/dealer-ai-demo`
- **Manager dashboard**: `http://localhost:5173/dealer-ai-admin`
- **Demo runbook**: see [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)

## Stack

- **Backend**: Django 5 + Django REST Framework, Postgres (SQLite fallback for dev)
- **LLM**: Switchable provider — local **Ollama** (default) or **OpenAI**
- **Frontend**: React 18 + Vite + Tailwind + shadcn-style UI

## Quick start (clean machine → live demo)

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                        # edit if you want OpenAI etc.
python manage.py migrate
python manage.py seed_demo_vehicles         # 16 demo vehicles
python manage.py seed_demo_scenarios        # 5 demo chats + leads (optional)
python manage.py runserver                  # http://localhost:8000

# 2. LLM (local, free) — separate terminal
ollama pull llama3.1                        # one-time
ollama serve                                # http://localhost:11434

# 3. Frontend — separate terminal
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

If everything is running, the demo page should match a vehicle within ~2
seconds of typing a prompt. If it shows a fallback message about reaching the
local AI model, Ollama isn't running — start it and try again.

## LLM provider

The provider is selected via `DEALER_AI_LLM_PROVIDER` in `backend/.env`. The
default is `ollama`, which makes zero paid API calls.

| Provider | Cost | Setup |
| --- | --- | --- |
| `ollama` (default) | Free, local | `ollama pull llama3.1 && ollama serve` |
| `openai` | Pay per token | Set `OPENAI_API_KEY` in `.env` |

Switch to OpenAI by editing `backend/.env`:

```
DEALER_AI_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

If the configured provider is unavailable (e.g. Ollama not running), the chat
returns a clear fallback message — the app stays up and the rest of the page
keeps working. Inventory search, payment math, and dashboard reads do not
depend on the LLM.

## Frontend

```bash
cd frontend
npm install
npm run dev    # dev server with /api proxied to localhost:8000
npm run build  # production bundle to dist/
```

Vite proxies `/api/*` → `http://localhost:8000` in dev so CORS is a non-issue.

## API surface

### Customer-facing
| Method | Path                                           | Body |
| ------ | ---------------------------------------------- | ---- |
| POST   | `/api/dealer-ai/chat/start/`                   | `{ customer_name?, customer_email?, customer_phone?, initial_message? }` |
| POST   | `/api/dealer-ai/chat/message/`                 | `{ session_id, message }` |
| POST   | `/api/dealer-ai/leads/`                        | lead fields (see Lead capture below) |
| GET    | `/api/dealer-ai/vehicles/<id>/`                | optional `?session_id=&target_monthly_payment=&down_payment=` |
| POST   | `/api/dealer-ai/vehicles/<id>/ask/`            | `{ question, session_id?, target_monthly_payment?, down_payment? }` |

### Manager / dashboard
| Method | Path                                           | Notes |
| ------ | ---------------------------------------------- | ----- |
| GET    | `/api/dealer-ai/admin/trends/`                 | full snapshot |
| GET    | `/api/dealer-ai/admin/leads/?limit=`           | recent leads list |
| GET    | `/api/dealer-ai/admin/lead/<id>/`              | lead + vehicles + transcript + profile |
| POST   | `/api/dealer-ai/admin/lead/<id>/handoff/`      | `{ mark_handed_off?: bool }` → handoff packet + plain-text |
| GET    | `/api/dealer-ai/admin/chat-sessions/?limit=`   | recent sessions list |
| GET    | `/api/dealer-ai/chat/session/<uuid>/`          | full session detail |

### Demo controls
| Method | Path                                  | Body |
| ------ | ------------------------------------- | ---- |
| POST   | `/api/dealer-ai/demo/reset/`          | `{ reload_demo_vehicles?: bool, delete_imported_vehicles?: bool }` |
| POST   | `/api/dealer-ai/demo/scenarios/`      | `{ reset?: bool }` → seeds 5 scripted demo conversations |

### Lead capture body
```json
{
  "name": "Chris D.",
  "phone": "(405) 555-0199",
  "email": "chris@example.com",
  "target_monthly_payment": 600,
  "down_payment": 5000,
  "trade_in": "2018 Escape ~75,000 miles",
  "credit_range": "good",
  "urgency": "this_week",
  "interested_vehicles": [12, 14],
  "session": "<uuid>"
}
```

## Inventory import (CSV)

Bring real dealership inventory in via the management command. Demo data is
isolated under `source="demo_seed"` — CSV imports never touch it.

```bash
# Validate without writing
python manage.py import_inventory --file path/to/inventory.csv --dry-run

# Real import (upserts by stock_number, falling back to VIN)
python manage.py import_inventory --file path/to/inventory.csv

# JSON output (pipe into anything)
python manage.py import_inventory --file path/to/inventory.csv --json
```

Required CSV columns (others optional):
`stock_number, vin, year, make, model, trim, condition, price, mileage,
body_style, drivetrain, fuel_type, exterior_color, interior_color,
transmission, engine, msrp, image_url, url, description, features`

`features` accepts JSON arrays (`["Tow", "Sync 4"]`) or pipe-separated
strings (`Tow|Sync 4`). Vehicles missing from a subsequent run of the same
`--source` are marked unavailable but never deleted.

## Demo controls

- **Reset demo** — wipes chat sessions and leads; reloads bundled demo
  vehicles. Imported (CSV) vehicles are preserved unless you opt in.
  Available as a button on `/dealer-ai-admin` and inside the Demo controls
  panel on `/dealer-ai-demo`.
- **Load demo scenarios** — populates the dashboard with 5 hand-crafted
  customer chats (budget mismatch, used SUV under $30k, service question,
  trade-in + fair credit, family camping). Available in the Demo controls
  panel on `/dealer-ai-demo`.

## Tests

```bash
cd backend
source .venv/bin/activate
python manage.py test dealer_ai
```

Frontend type-check and production build:
```bash
cd frontend
npx tsc --noEmit
npm run build
```

## Roadmap (post-MVP)

- pgvector semantic inventory search
- Streaming chat responses (SSE/WebSocket)
- Real DMS inventory feed (push from CRM/DMS, not CSV upload)
- Email/SMS delivery from the handoff modal
- Sales-rep handoff into CRM
