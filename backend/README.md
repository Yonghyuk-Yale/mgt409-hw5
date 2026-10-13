# Campus Customs Operations — Backend

FastAPI backend for the HW 5 dashboard. It runs the five-agent team (PydanticAI, `gpt-6-luna` via Portkey) and exposes the routes the dashboard calls. Every shop fact comes from the `campus-customs-ops` MCP server (`../mcp_server/server.py`), which the backend starts by itself.

## Setup (once)

From the `HW 5` folder:

```powershell
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Put the Portkey key in a `.env` file in `HW 5/` (or `backend/`), using `../.env.example` as the template:

```
PORTKEY_API_KEY=...
```

The working database `data/campus_customs_new.db` must exist (copy of `data/campus_customs.db`); `POST /api/reset` recreates its contents at any time.

## Run

With the virtual environment active, from this `backend` folder:

```powershell
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000 (route list) · interactive docs: http://localhost:8000/docs
- Dashboard: `../frontend` (`npm run dev` → http://127.0.0.1:5455); CORS allows that origin.
- On Windows, `--reload` serves the app on an event loop that cannot start subprocesses, so the agent team and all MCP calls run on a background loop of their own (`ops_loop.py`). Nothing extra is needed.
- `--reload` watches this folder only; after editing `../mcp_server/server.py`, restart the server.

## Routes

| Method | URL | What it does |
|---|---|---|
| GET | `/` | Service info and route list |
| GET | `/api/health` | API up, LLM key/model configured, team busy or not |
| GET | `/api/tickets` | All tickets, each `open` or `resolved`, with pending approvals and drafts |
| GET | `/api/tickets/{id}` | One ticket with linked rows, approval requests, drafts, latest run |
| POST | `/api/tickets/{id}/run` | Start the agent team on the ticket (background; 202 + `run_id`). Optional body `{"feedback": "..."}`; deny reasons on the ticket are added automatically |
| POST | `/api/tickets/{id}/resolve` | Human marks the ticket resolved |
| GET | `/api/runs` · `/api/runs/{run_id}` | Team runs; one run's status and full result (finished runs are saved in `../output/team_runs/`) |
| GET | `/api/runs/{run_id}/trace` | Per agent loop: agent, caller, tools, tokens (from the audit trail) |
| GET | `/api/events?after=<seq>` | Live agent events: who says what, which tool runs (poll every 1–2 s) |
| GET | `/api/approvals` | Approval requests on the board (`?status=pending_human`, `?ticket_id=`) |
| POST | `/api/approvals/{id}/approve` | Human approves; the payment / purchase order is executed and cash changes |
| POST | `/api/approvals/{id}/reject` | Human rejects; nothing moves |
| GET | `/api/drafts` | Customer message drafts (never sent by the system) |
| GET | `/api/cash` | Checking balance from `cash_accounts` |
| GET | `/api/transactions` | Every payment made, newest first |
| POST | `/api/reset` | Reset the working database to its starting values |

Approve/reject take an optional JSON body `{"decided_by": "Owner", "note": "..."}`; agent names are refused.

## Command-line run (no server)

```powershell
python run_ticket.py 102 --reset
```

## Files

| File | Role |
|---|---|
| `main.py` | FastAPI app and routes |
| `team.py` | How the team works one ticket (Boss plan → specialists → Customer Service review → Boss report) |
| `agents/` | One file per agent + `base.py` (agent loop, `ask_teammate`, budget, audit) |
| `prompts/` | One prompt per agent + `shared_rules.md` |
| `models.py` | Data types (agent outputs, team result, audit entries) |
| `mcp_tools.py` | MCP connection and each agent's tool allowlist |
| `guardrails.py` | Token/loop limits, delegation rules, privacy masking |
| `events.py` | Live event feed for the dashboard |
| `audit.py` | Cumulative audit trail (`../output/audit_trail.json`) |
| `ops_loop.py` | Background event loop for the team and MCP calls |
| `llm.py` | The single model: `gpt-6-luna` through Portkey |
