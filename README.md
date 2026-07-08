# Procrastination Profiler

A **local-first AI agent** that builds a personal model of *how* you procrastinate. It combines
three data sources — your task list, passive activity (ActivityWatch), and 2-minute natural-language
check-ins — then surfaces non-obvious patterns about *when, why, and how* you avoid specific kinds of
work. Not a nag. A curious scientist for your own behavior.

> Local-first. No cloud. Your data stays on your machine.
> Useless on day 1, genuinely interesting after 30 days.

![stack](https://img.shields.io/badge/backend-FastAPI-009688) ![stack](https://img.shields.io/badge/db-SQLite-003B57) ![stack](https://img.shields.io/badge/llm-Groq-F55036) ![stack](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB)

---

## What's inside

| Layer | Tech |
|-------|------|
| Backend API | Python 3.11 · FastAPI · Uvicorn |
| Database | SQLite (`backend/data/profiler.db`) |
| LLM | **Groq** (OpenAI-compatible) — `llama-3.3-70b-versatile` (agent) + `llama-3.1-8b-instant` (extraction) |
| Stats engine | scipy + numpy (real correlation, not LLM guessing) |
| Scheduler | APScheduler (hourly sync, daily check-ins, weekly report) |
| CLI | Typer |
| Frontend | React · Vite · Tailwind · Recharts (dark, data-dense dashboard) |

Three data sources, combined by a **procrastination event detector**:

- **Task list** — what was delayed, for how long (Todoist API *or* a plain-text file *or* manual).
- **ActivityWatch** — what you did *instead* (the "displacement signature"). Fully optional.
- **Daily check-in** — energy, stress, emotion, why it felt hard. Free text → structured by the LLM.

---

## Quickstart

### 1. Backend

```bash
cd backend
cp .env.example .env          # then paste your Groq key into GROQ_API_KEY
uv venv --python 3.11
uv pip install -e .
uv run uvicorn api.main:app --reload --port 8000
```

> A `.env` with a working Groq key may already be present. Get a free key at
> <https://console.groq.com/keys>. **Without a key the app still runs** — check-in parsing falls back
> to regex heuristics and the agent reports it needs a key; all statistics/charts work regardless.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
```

Open **http://localhost:5173**.

### 3. (Optional) See it populated immediately

The database starts **empty** by design. To load ~30 days of synthetic data:

```bash
cd backend
uv run python seed_demo.py            # or: uv run python seed_demo.py --wipe
```

---

## CLI

```bash
cd backend
uv run python -m cli.main status
uv run python -m cli.main task add "Write Q3 report" --type administrative --est 90 --stakes high
uv run python -m cli.main task list
uv run python -m cli.main log-event <task_id> --delay 26 --displacement entertainment_escape --energy 2
uv run python -m cli.main checkin "three back-to-back calls, exhausted 2/5, kept opening twitter"
uv run python -m cli.main query "why do I avoid administrative tasks?"
uv run python -m cli.main report weekly
uv run python -m cli.main sync
```

---

## The four screens

- **Dashboard** — KPI cards, a 7×24 temporal heatmap (when you avoid), avoidance-rate-by-task-type
  bars, a displacement donut (what you do instead), unlock-trigger effectiveness, plus inline task &
  event logging so the whole loop works without the CLI.
- **Check-in** — chat-style. Type how your day went; the agent extracts energy/stress/emotion/context.
- **Ask** — freeform chat with the analyst agent. It calls real tools over your data before answering.
- **Profile** — your evolving model: confidence level, active hypotheses, avoidance breakdown, and a
  generated weekly insight report.

---

## API

`GET /api/status` · `GET /api/dashboard` · `GET /api/profile` · `POST /api/profile/refresh` ·
`GET/POST /api/tasks` · `GET/POST /api/events` · `POST /api/checkin` · `GET /api/checkin/prompt` ·
`POST /api/query` · `GET /api/report/weekly` · `GET /api/insights` · `POST /api/sync`

Interactive docs at **http://localhost:8000/docs**.

---

## Optional integrations

- **ActivityWatch** — install from <https://activitywatch.net/downloads/>. When it's running at
  `localhost:5600`, the enricher auto-links what you were doing during a delay. When it's not, the app
  simply reports displacement as `unknown`.
- **Todoist** — set `TODOIST_API_TOKEN` in `.env` to sync your real tasks hourly.
- **Plain text** — point `TASKS_FILE` at a markdown task file:
  `- [ ] Write the proposal @type:creative @est:90m @stakes:high`

---

## Tests

```bash
cd backend && uv run pytest -q
```

---

## How avoidance is detected

A task that sits longer than `max(2× its estimate, 4h)` while still `pending` becomes a
**procrastination event**. The enricher attaches the displacement signature from ActivityWatch; the
check-in attaches emotional context; the stats engine computes avoidance rates, temporal clusters,
displacement distribution, trigger effectiveness, and context↔delay correlations. The LLM agent
*interprets* these numbers and proposes causal hypotheses — it never invents the numbers.

## Project layout

```
backend/   FastAPI app, agent, analysis engine, services, CLI, tests
frontend/  React + Vite dashboard (dark, data-dense)
```

*The agent gets smarter the more honestly you use it.*
