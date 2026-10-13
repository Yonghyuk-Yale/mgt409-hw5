# MGT 409 — Homework 5: Campus Customs Multi-Agent Operations

**Start here.** This file explains what the submission is, how to run it, and where to read next.

Yonghyuk Choi · Yale School of Management

---

## What this is

An AI operations team that runs the **Campus Customs** shop's ticket board, plus a dashboard where the owner watches the agents work and makes every money decision.

- **MCP server** (`mcp_server/`): the single source of shop facts. 26 tools over the shop database, split into read tools, request tools (agents file approval requests and customer drafts; no money moves), and human-only tools (record a decision, execute an approved payment, reset).
- **Five agents** (`backend/`, PydanticAI): Boss, Inventory, Accounting, Facilities, Customer Service. Every agent uses only `gpt-6-luna` through the Portkey gateway. Boss plans, specialists work and ask each other, Customer Service reviews every customer-facing ticket, and Boss reports to the owner.
- **FastAPI backend** (`backend/main.py`): runs the team and exposes the routes the dashboard calls.
- **React dashboard** (`frontend/`, React + Vite + TypeScript): the owner's "HQ": tickets, the agent team live, approvals, cash, and the full history.
- **Safety**: agents can never pay; only the owner's Approve executes a payment, and it is refused if cash would go negative or the vendor still has an unpaid invoice. Every agent loop and every human decision is written to `output/audit_trail.json`.

---

## Requirements

| Tool | Version |
|---|---|
| Python | 3.13 or newer (tested on 3.14) |
| Node.js | 20.19+ or 22.12+ (required by Vite 8; tested on 24) |
| Portkey API key | Needed for agent runs (`PORTKEY_API_KEY`). Without it, the board, cash, approvals, and reset still work. |

---

## Setup (once)

All commands start from the repository folder (the folder this README is in). Commands are for Windows PowerShell; macOS/Linux equivalents are noted.

```powershell
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                 # macOS/Linux: cp .env.example .env
```

Then open `.env` and set `PORTKEY_API_KEY`. `PORTKEY_MODEL` may stay `gpt-6-luna` (the only model allowed).

---

## 1. The database: original and working copy

`data/` is included in this repository.

| File | Role |
|---|---|
| `data/campus_customs.db` | The **original** shop database. Never modified. |
| `data/campus_customs_new.db` | The **working copy**. The MCP server, and therefore every agent and the backend, reads and writes only this file. |

The working copy is made by copying the original:

```powershell
copy data\campus_customs.db data\campus_customs_new.db      # macOS/Linux: cp data/campus_customs.db data/campus_customs_new.db
```

If the working copy is missing, the MCP server creates it from the original on first use.

> **The included working copy is in its final graded state.** After the Problem 9 run, invoice 501 and the rent are paid, the discount is approved, all three tickets are resolved, and checking is **$152.00**. This matches the Cash tab of `output/desk_tickets.html` and `output/resolved_tickets.json`. Start the backend and dashboard to see it as-is. Reset (section 5) only when you want to run the tickets again.

---

## 2. Start the MCP server

The backend starts the MCP server by itself (over stdio) whenever it needs it, so **you do not have to start it separately to use the dashboard.** To run it on its own:

```powershell
.venv\Scripts\python.exe mcp_server\server.py                        # stdio (an MCP client launches this)
.venv\Scripts\python.exe mcp_server\server.py --http --port 8100     # or Streamable HTTP on a free port
```

**Claude Code:** `.mcp.json` registers the server as `campus-customs-ops`. Open Claude Code in this folder and approve the server. On macOS/Linux, change the command in `.mcp.json` to `.venv/bin/python`. The tool list is in `mcp_server/README.md`.

---

## 3. Start the FastAPI backend

In a terminal with the virtual environment active:

```powershell
cd backend
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000 (route list) · interactive docs: http://localhost:8000/docs
- Routes (tickets, run the team, live events, approve/reject, cash, transactions, reset) are listed in `backend/README.md` and in section 8 of `output/harness.md`.

---

## 4. Start the React board

In a second terminal:

```powershell
cd frontend
npm install        # first time only
npm run dev
```

Open **http://127.0.0.1:5455** (port fixed in `frontend/vite.config.ts`; the backend's CORS allows it). The board expects the backend at http://localhost:8000.

---

## 5. Reset the database (before a full 3-ticket run)

The shop rule: **before running all three tickets from the start, reset the working copy to the original values** (cash $3,400.00, all tickets open, invoice 501 unpaid, no approval requests or drafts). Every full run then starts from the same state and its results can be compared.

Any one of these works:

| How | Command / action |
|---|---|
| Dashboard | Click **⟳ Refresh** (top right) and confirm. |
| API | `curl -X POST http://localhost:8000/api/reset` |
| Command line (no server needed) | `cd backend` then `python run_ticket.py 101 102 103 --reset` (resets, then runs the team on all three tickets) |
| By hand (servers stopped) | Copy the original over the working copy (section 1). |

To get the graded final state back after a reset: `git checkout -- data/campus_customs_new.db`.

### A full run, step by step

1. Reset (above).
2. On the board, select ticket #101 and press **Assemble!** Watch the heroes, the speech boxes, and the hand-off feed.
3. When Boss's report arrives, approve or deny each request on the decision desk (a deny asks for a reason and offers **Re-run with feedback**). Approving a payment changes the checking balance.
4. When the decisions are done, the ticket gets the **MISSION COMPLETE** stamp.
5. Repeat for #102 and #103.

---

## Where to read next

| File | What it is |
|---|---|
| `output/desk_tickets.html` | One page, opens on double-click. Per ticket: **Expected** plan and **Actual** run; **Cash** (itemized, matches the DB); **Reflection** |
| `output/resolved_tickets.json` | Per ticket: final status, outcome, what each agent contributed, the owner's approvals, cash spent |
| `output/resolved_board.html` | Screenshots of the dashboard with every ticket resolved (opens on double-click) |
| `output/audit_trail.json` | Cumulative audit: every agent loop (tools, arguments, results, tokens) and every human decision |
| `output/harness.md` (`harness_eng.md`) | Tables, MCP tools, the five agents, safety rules, token limits, API routes, dashboard, run results (Korean / English) |
| `output/design.md` | Dashboard design and the reasons behind it |
| `output/mcp_smoke.json` | Problem 4 smoke test of the MCP tools against the database |
| `output/team_runs/` | Saved results of each team run (the board shows them after a restart) |
| `AI_prompts.md` (`AI_prompts_eng.md`) | My prompts for every problem (Korean / English) |
| `backend/prompts/` | One prompt per agent, plus `shared_rules.md` for the whole team |
| `mcp_server/README.md`, `backend/README.md`, `frontend/README.md` | Details for each part |
