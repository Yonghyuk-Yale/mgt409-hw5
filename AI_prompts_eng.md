# AI Prompts Log — Homework 5

This document records, problem by problem, the instructions I wrote myself for the AI assistant (Claude Code) while working on MGT 409 Homework 5.

The logging rules are:

- Each problem gets its own section with the problem number and title.
- Each section keeps at least one original prompt that I typed myself.
- When a follow-up prompt was needed, it is recorded together with one sentence on what the previous response was missing.
- Sections for Problem 2 onward are added as the work progresses.

The prompts were originally written in Korean. The Korean originals are in `AI_prompts.md`; this file is a faithful English translation.

---

## Problem 1: Create the AI Prompts Log

### Prompt 1

Starting HW 5

> **What was missing:** At this point the `HW 5` folder was empty, so the first response could not decide what to build and had to ask me for the assignment scenario, tech stack, data, and submission method. A follow-up instruction was needed in which I added `data.zip` and stated the scope of Problem 1 myself.

### Prompt 2

I've put data.zip in for now. Do the AI_prompts, and let's go with a .venv and gpt-6-luna.
Problem 1 is about AI_prompts. (Same for every HW.)

### What this problem produced

- `AI_prompts.md` / `AI_prompts_eng.md` — the Korean and English versions of this log.
- `data/` — the contents of `data.zip`: a single `campus_customs.db`.
- `.venv/` — a dedicated Python 3.14 virtual environment for HW 5.
- `requirements.txt` — the base packages for now: `pydantic-ai-slim[openai]` and `python-dotenv`. More packages will be added in the problem where the tech stack is decided.

### What was checked

- The packages were installed with the `.venv` Python, and `PORTKEY_API_KEY` was read from the project-root `.env` to make one real call to `gpt-6-luna` through the Portkey gateway, which returned a response (about 2.5 seconds).
- `campus_customs.db` was opened read-only to check only the table names and row counts. It has the same file name as in HW 4 but is a different database. The tables are `cash_accounts` (1), `desk` (1), `inventory` (10), `invoices` (1), `leases` (1), `payments` (0), `pricing` (4), `tickets` (3), and `vendors` (3). The meaning of each field will be analyzed in the relevant problem.

---

## Problem 2: Database Analysis and Working Copy

### Prompt 1

Let's start Problem 2. Open @1_Homework/HW 5/data/campus_customs.db and take a good look at every table and field. Make a copy named campus_customs_new.db; in the following problems we'll write updates to the _new.db file when needed. Look carefully at the three open tickets and study how they connect to the other tables. Create harness.md (Korean) and harness_eng.md, and for each table list its fields and write a brief one-line note on why that table matters to the agents. I'll keep updating these two Korean and English harness files on request in later work.

### What this problem produced

- `data/campus_customs_new.db` — a working copy identical to the original `campus_customs.db`; the two files' SHA-256 hashes were confirmed to match. Tools in later problems change only this file.
- `output/harness.md` / `output/harness_eng.md` — the fields (type and meaning) of all 9 tables, with a one-line note on why each table matters to the agents.

### What was checked

- The original database was opened read-only and the schema and every row of every table were inspected.
- The three open tickets connect to the other tables as follows.
  - **101 (customer order, 1 tee in S):** `inventory` shows 0 in size S. The apparel restock vendor is Bulldog Print Co (5-day lead time), but invoice 501 ($840), linked from the ticket, is unpaid and past its due date (08-28), so it must be paid before that vendor will ship.
  - **102 (rent notice):** Lease 1, $2,400 per month, due 09-02 (two days after today, 08-31, so not yet overdue).
  - **103 (bulk discount on 20 hoodies):** Only 8 are in stock in size M, a shortfall of 12. The restock vendor is the same Bulldog Print Co as in 101, so it is blocked by invoice 501 too. Unit cost $22, list price $58.
- The only cash is `checking` at $3,400. Paying both invoice 501 and the rent leaves $160. If the restock cost of 12 hoodies ($264) had to be paid right away, there would not be enough cash. This prioritization question is handled in the problem where the agents are built.

---

## Problem 3: Build the MCP Server (Three Ticket Tools)

### Prompt 1

We're moving on to Problem 3, but before that, briefly explain what the tickets are and briefly explain to me how the .db is organized.

Problem 3 is building an MCP server: write an MCP server using FastMCP in an mcp_server folder. It will communicate with @1_Homework/HW 5/data/campus_customs_new.db. There's no need to connect or run it right away in this problem. In this HW5, every agent will use the tools in this MCP server. We'll keep adding many more tools later. For now we'll write only 3 tools for the tickets in the database. Name them clearly, and don't invent any data — use only the information in the DB. Then write up the 3 MCP tools in each of the 2 harness files. For every tool, record which tables it reads, which ticket it helps open (101, 102, or 103), and one line on why this tool is the best fit for that ticket. Don't use vague descriptions like "reads inventory"; tie each tool tightly to its ticket. Create a README.md in the mcp_server folder we just made, and briefly add what this MCP server exists for, which database file it uses, and a description of the 3 tools in it.

### What this problem produced

- `mcp_server/server.py` — a FastMCP server (`campus-customs-ops`). It opens only `data/campus_customs_new.db`, in read-only mode, and has three tools, one per ticket.
  - `check_stock_for_size(sku, size, qty_needed)` — Ticket 101: stock in that size, the shortfall, and the other sizes' stock from `inventory`.
  - `get_rent_due_for_lease(lease_id)` — Ticket 102: rent and due date from `leases`, plus days left and overdue status measured from `desk.date_today`.
  - `get_price_and_margin_for_sku(sku)` — Ticket 103: unit cost and list price from `pricing`, plus the margin per unit at list price.
- `mcp_server/README.md` — why the server exists, the database file it uses, the three tools, and how to run it.
- `output/harness.md` / `output/harness_eng.md` — added a "2. MCP Tools" section. For each tool: the tables it reads, the ticket it helps open, and why it is the best fit for that ticket.
- Added `fastmcp` to `requirements.txt` and installed it in the HW 5 `.venv` (fastmcp 4.1.0).

### What was checked

- The server was not actually started or connected to an agent. Instead, the tool list and call results were checked with FastMCP's in-memory client.
  - 101: 0 in size S, short by 1, cannot be filled now.
  - 102: $2,400, due 09-02, 2 days left, not overdue.
  - 103: unit cost $22, list price $58, margin $36 per unit (62.1%).
- With a nonexistent SKU, size, or lease, the tools returned `found: false` with a reason instead of making up values.
- After testing, the hashes of the original DB and `_new.db` were unchanged, confirming the read-only tools did not modify the database.

---

## Problem 4: Connect the MCP Server to Claude Code and Smoke-Test It

### Prompt 1

Problem 4 says to add my MCP server to this project so that you, Claude Code, can use my tools, but I don't really understand it. Do it and help me understand. It says to save this connection information in a .mcp.json file at the project root path. There's already an @.mcp.json file, so maybe it means adding this to it.

Once it's connected, test that each of the 3 MCP tools works properly. Save the test results and evidence to mcp_smoke.json in the @1_Homework/HW 5/output folder. For every tool: the prompt I gave the vibe coder, the tool name, and the tool result (it must match the values in @1_Homework/HW 5/data/campus_customs_new.db).

### Prompt 2 (New Session, Tool Tests)

Claude Code reads `.mcp.json` only when a session starts, so I opened a new session and asked one question per tool myself.

I'm continuing HW 5 and opened a new session to test the tools.

Do we have 1 white tee in size S in stock?

What's the rent and due date on lease 1, and is it overdue?

What are the unit cost, list price, and margin on the navy hoodie?

### Prompt 3

Yes, create a .mcp.json in the HW 5 repo too.

### What this problem produced

- In the existing `.mcp.json` at the project root (`AI Foundation/`), the three existing servers (`yale-som-courses`, `outlook`, `gmail`) were left as they were, and a `campus-customs-ops` entry was added. It runs `mcp_server/server.py` over stdio with the HW 5 `.venv` Python.
- `HW 5/.mcp.json` — registers the same server with relative paths (`.venv/Scripts/python.exe`, `mcp_server/server.py`) so the connection can be reproduced from the submission repo. Launching the server with exactly this command from the `HW 5` folder showed all three tools and a working tool call. `mcp_server/README.md` now explains how to connect and the macOS/Linux path (`.venv/bin/python`).
- `output/mcp_smoke.json` — for each tool: the question I wrote, the tool name, the call arguments, the tool result, the SQL and DB values used for comparison, and whether they match (`matches_tool`). The closing `summary` records that all three tools match the DB.

### What was checked

- `.mcp.json` was confirmed to be valid JSON. Launching the server with exactly the command written in it and connecting over stdio showed all three tools.
- In the new session, `campus-customs-ops` connected. Claude Code called the tools over the real MCP connection, then queried the same values directly from `campus_customs_new.db` with SQL for comparison.
  - 101 `check_stock_for_size(CC-TEE-WHITE, S, 1)`: 0 in size S, short by 1, cannot be filled now. Other sizes M 5, L 3, XL 2, location Aisle B. Matches the `inventory` query.
  - 102 `get_rent_due_for_lease(1)`: Chapel Street shop, Elm City Properties, $2,400, due 2026-09-02. 2 days left measured from `desk.date_today` (2026-08-31), not overdue. Matches the `leases` and `desk` queries and the days-left value recomputed from them.
  - 103 `get_price_and_margin_for_sku(CC-HOOD-NAVY)`: Basic Hoodie Big Yale, unit cost $22, list price $58, margin $36 per unit (62.1%). Matches the `pricing` query and the margin recomputed from it.
- By the real date (2026-10-11) the lease 1 rent would already be overdue, but per the assignment rules `desk.date_today` was used as "today."

---

## Problem 5: Build the Agent Team (PydanticAI)

### Prompt 1

Let's start Problem 5. We're building an agentic team: using PydanticAI, build the Boss, Inventory, Accounting, Facilities, and Customer Service agents. Including prompts, models, and agent loops, let's make them connect well, work together, hand work back and forth, and work as one team. Create backend and frontend folders; in backend/prompts we'll have one prompt file per agent. Create backend/models.py with the data types, and build the agent files in the backend folder. (I'll leave the file structure up to you, as long as the 5 roles are clearly separated.) Every agent uses gpt-6-luna.

Now let's write good prompts for the roles and rules the shop needs from its agents. The more detailed the better, and it would be good to cover every aspect of the agents' work.

Let's build the tools the agents need on the MCP server so they can handle the tickets well. Shop facts come from the MCP server over @1_Homework/HW 5/data/campus_customs_new.db — you must not bypass MCP and invent some second shop-tools layer. Create output/audit_trail.json, record every agent loop, and make it possible to audit later. Keep accumulating it. Take a look at the previous assignment's audit_trail.json file and figure it out.

In the 2 harness files, write up each agent, which MCP tools are used and which tables those tools use, and add a brief safety section. Assume a real business handling real customers and real money, and build the guardrails thoroughly. Also add limits on token usage. Finally, update @1_Homework/HW 5/mcp_server/README.md so the list of tools you now have is properly recorded.

Boss — reads tickets well, defines which agents should take the work, what deliverable each produces and in what sequence they ping-pong the work, and brings the final conclusion to me. And as the person responsible for safety (including token usage), manages the outputs, customer information, and money well.
Inventory — not only knows the items, stock, and goods well, but also holistically manages which vendor to contact for more stock, that vendor's status and response time, and the stock arrival schedule. It should know the popular products by size and track not just shortages but declining stock and dead stock. Goods must be there when needed, and no stock should sit too long; I think it should also be able to suggest alternative products from a stock perspective and give an opinion on discount rates based on stock.
Accounting — cash, invoices, margins, paying vendors, and, by contacting me through Boss, placing orders too, under human approval. It should take requests from the Inventory and Facilities agents, judge them, and pass its opinion as the accounting owner to Boss. It should manage sales, profit, and liquidity. I think it should also do reporting and performance management on financial results such as sales targets and profit margins — of course through approval and coordination with Boss and the other agents.
Facilities — as the owner of buildings and space such as rent and leases, it must check payments; as a payment date approaches, it keeps checking ahead of time with the Accounting and Boss agents whether payment on time is possible, and if there's a problem, it reports to the human through Boss. That way a decision can be made.
Customer Service — writes messages to customers and, when there's a problem, knows how to apologize and offer alternatives. It should know each customer's preferences, tastes, and characteristics, and pass replies and feedback received from customers to the other agents and the human, proposing ways to keep updating the system. It is the eyes and ears for the other agents and the human, and the only agent that thinks from the customer's side and can build customers' trust. Give this agent's opinion real weight. It must not be treated as just one more agent.

That's as far as I've thought it through. If you have concerns, overlaps, or gray areas, point them out and let's add them together.

### My decisions on the gray areas

Before building, the AI raised four questions; I chose the recommended option for each.

- **Duties the database cannot support** (best sellers, aged stock, customer preferences, sales targets): keep them in the roles, and have agents say when the data does not exist.
- **Scope of payment tools**: agents only file requests. The real payment tool lives on the MCP server, but only the backend calls it, after human approval. It refuses when cash is short.
- **Discount floor**: never below cost; a margin under 40% needs human approval. Every discount proposal goes to the human.
- **Token limits**: 150k tokens, 12 agent loops, and at most 3 levels of hand-off per ticket.

### What this problem produced

- `mcp_server/server.py` — tools grew from 3 to 24.
  - 16 read tools: tickets, customer history, stock overview, vendor status, restock estimate, discount check, cash position, payment history, leases, and the board.
  - 5 request tools: payment, purchase-order, and discount requests, and saving and revising customer drafts. Amounts come from the database; below-cost, duplicate, and nonexistent targets are refused.
  - 3 human-only tools (`human_only`): record a decision, execute an approved request, change ticket status. They refuse when cash is short, when ordering from a vendor with an unpaid invoice, and when paying twice.
  - The board tables `approval_requests` and `customer_drafts` are created in `_new.db` on first use.
- `backend/models.py` — agent output types (TicketPlan, FinalReport, four specialist reports), the team result, and audit entry types.
- `backend/prompts/` — one per agent (`boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md`) plus the team-wide rules in `shared_rules.md`.
- `backend/agents/` — one file per agent plus a shared `base.py` (the agent loop, `ask_teammate` delegation, budget enforcement, audit recording).
- `backend/team.py` — the ticket flow: Boss plans → specialists work in order (and can ask each other) → CS review (required on customer tickets) → Boss's final report.
- `backend/guardrails.py` (limits, delegation rules, privacy masking), `backend/llm.py` (fixed to gpt-6-luna), `backend/mcp_tools.py` (MCP connection, per-agent tool allowlists), `backend/audit.py` (cumulative audit trail), `backend/run_ticket.py` (command to run it).
- `frontend/` — empty folder (`.gitkeep`). The dashboard will be built in the problem that covers it.
- `output/audit_trail.json` — accumulates one entry per agent loop and one summary per ticket run.
- `output/harness.md` / `output/harness_eng.md` — added sections 3–7: the agent team, the full MCP tool list with tables, Safety, token limits, and the audit trail.
- `mcp_server/README.md` — updated with the full list of 24 tools.

### What was checked

- Every MCP tool was called without an LLM. Amounts come only from the database. An agent name cannot approve. Execution before approval is refused. Purchase orders from a vendor with an unpaid invoice are refused. Payments are refused when cash is short. Below-cost discounts and duplicate requests are refused.
- Each ticket was run once with the real gpt-6-luna (DB reset before each run).
  - 102 (~72k tokens): Facilities asked Accounting directly, and Accounting filed the rent request (ping-pong). Boss reported the invoice → rent order and the $160 left over.
  - 103 (~110k tokens): the team found the 12-unit shortfall, the vendor blocked by invoice 501, and that a restock would leave cash $104 short. Because of that, Accounting filed no request. CS drafted a message with an apology and a size-mix alternative.
  - 101 (~97k tokens): Accounting filed an invoice payment request ($840) and a blocked purchase-order request ($8). The CS draft promised no date. Boss passed every request and draft to the human.
- Problems fixed during testing:
  - An output-type error in Boss's final report; the fallback report went out instead at the time.
  - Real-clock timestamps confused the agents; they are now hidden.
  - Duplicate drafts piled up; a revise tool was added.
  - Another ticket's customer name stayed in the audit trail.
  - Phone-number masking hid dates.
  - Part of a name ("Hi Tauhid") was left unmasked.
- The first audit trail, which had the masking bug, was moved to `output/audit_trail.dev-tests-2026-10-12.json`, and `audit_trail.json` was started fresh.
- At the end, `_new.db` was reset to the original.

---

## Problem 6: Expected Plans for the Three Tickets (desk_tickets.html)

### Prompt 1

Let's start Problem 6. It's about making a plan for the three tickets.

Before wiring the backend, I'm writing down what I expect from the team on each ticket. Create output/desk_tickets.html; it's a one-page HTML file that, when double-clicked, shows one tab per ticket. Also make Cash and Reflection tabs and leave them empty. (We'll fill them in the next problems.)

Each ticket tab has an Expected section and an Actual section. The Actual section will be filled in later as we run the agents; for now let's fill in only the Expected section.

I'll give you the content for the Expected section in my own words, and you polish the writing and put it up.
What it must contain:
1) The agent Boss should call first, and why
2) Every agent delegation I expect — not "Boss calls everyone"
3) Which MCP tools I expect to be used

Don't run anything yet; first pull up exactly what is in the tickets again. Then, when I give you my expected plan for them, carry it out together with this prompt.

### Prompt 2 (my draft of the expected plans)

101: Boss will call the inventory agent first, because we have to start by checking whether the tee is in stock. Then if the inventory agent tells Boss there's no tee, Boss will send it to the inventory and accounting agents to see whether stock can be secured, and I think it would be good for the two of them to talk it over and bring Boss a way to resolve the invoice. And the inventory agent should recommend another size that is in stock or a similar tee in S, or, if that doesn't work, give notice that it can't be sold or will be delayed. They discuss this with Boss and the customer service agent, get the recommendation decided by the human, and once it's decided, the customer service agent will write a message draft about it.

102: Boss will call the Facilities agent first, because we have to check that our lease and the landlord's notice match. Then I think it will work with the Accounting agent to discuss when it's best to pay the rent. In this process it also needs to coordinate well with the other agents. In particular, Boss has to weigh the priority against the other tickets, so it needs analysis from a much wider view.

103: First it will call the inventory agent to check whether we can supply the quantity the customer wants in the exact size and model, regardless of the discount. Then, if the quantity is there, it discusses with the Accounting agent to set the discount rate and reports to Boss → the human. If the quantity isn't there, like 101, it should talk with the inventory agent about whether there's an alternative or whether to give notice of a delay/no sale, and it would be good to ask for Customer Service's opinion at the end too. Then Boss sends the leading option to the human for a decision, and according to that decision, Customer Service posts a draft of the message to send to the customer.

This is my draft; combine in the MCP tools, strengthen and revise it, and put it up in the HTML.

### What this problem produced

- `output/desk_tickets.html` — a one-page HTML file that opens on double-click. It works with no external files and has Yale Blue branding bars at the top and bottom.
  - Tabs: Ticket 101, Ticket 102, Ticket 103, Cash, Reflection. Cash and Reflection are left empty.
  - Each ticket tab has a card with the ticket's original content, an Expected section, and an Actual section. Actual is left empty with "Not run yet."
  - Each Expected section follows my draft in three parts: (1) the agent Boss calls first and why, (2) step-by-step delegation (Boss → A, and direct collaboration such as A ↔ B), and (3) a table of MCP tools by agent.
  - Each Expected section also ends with the decisions the human makes and what the team is not expected to do.
- Written in English only, because the assignment names this file and graders read it.

### What the AI added

- 101: pointed out that invoice 501 is the payment for reprinting this exact size-S tee. Whether paying 501 releases tees already printed or a new order is needed is not in the database, so the team must raise it as a question instead of guessing. Also noted that the catalogue has no other tee, so no "similar tee in S" exists.
- 102: since the notice email states no amount, Facilities checks it against the lease. Because the shop records no revenue and waiting brings in no cash, the rule is to pay before the due date (09-02). Also recorded the cross-ticket conflict: rent + invoice 501 + a hoodie restock ($3,504) exceeds the $3,400 cash.
- 103: split into stock available (A) and not available (B). B includes a restock (12 units, $264, blocked by 501), a size mix (32 units in all), partial shipment first, and delay or decline. Recorded the discount floor as $36.67 (40% margin, at most 36.8% off).

### Prompt 3 (order change, at the start of the Problem 7 message)

"What I should tell you in advance: in your plan, CS writes the draft after the human decides. Right now the backend has CS write the draft in advance while reviewing, before the decision. We need to decide in the problem that wires the backend whether to match this order. If we don't, the Actual section will come out differently from Expected." Thinking about it, I think it's also fine to send CS's draft up to the human together, because then it can be acted on right away. Revise it to match the backend.

### What was changed

- Aligned the Expected flow for 101 and 103 in `desk_tickets.html` with the backend order: CS writes the draft for the recommended option first, and Boss sends it up to the human together with the recommendation. If the human picks a different option, CS revises the same draft.

---

## Problem 7: Backend Design (FastAPI Routes)

### Prompt 1

Next, Problem 7 is designing the backend. Problem 8 is the frontend design, so this fills in the backend that will go into it.

Use FastAPI in backend/main.py and add routes to do the items below.

1) Show the 3 tickets and mark whether each is open or resolved.
2) Given a ticket ID, run the Agent Team on that ticket.
3) Show the recent agent events (what each agent is saying, which tools are in use) — I'd like the board to keep refreshing with the latest events.
4) After the human clicks approve, approve the payment or purchase (the agent only needs to get ready to pay; this route is what actually changes the cash).
5) Show the current checking balance from the cash_accounts file.
6) If I want to start over (a Refresh button), reset the database back to its initial values (I guess this database means _new.db?).

Do up to here, then type "uvicorn main:app --reload --port 8000" into the terminal from the @1_Homework/HW 5/backend folder and run it. Make sure it works whether I or the grader do it. I think the backend will run at http://localhost:8000 (tell me if it conflicts with my previous assignments or my personal project; this is for grading, so I think this assignment should run on 8000). The frontend dashboard must be able to call these routes. Finally, in the 2 harness files, list each route with one line on what URL it is and what it does — really simply.

### What this problem produced

- `backend/main.py` — the FastAPI app and routes.
  - 1) `GET /api/tickets`: the tickets with open/resolved state.
  - 2) `POST /api/tickets/{id}/run`: runs the team in the background and returns a `run_id` right away; `GET /api/runs/{run_id}` shows the result.
  - 3) `GET /api/events?after=<seq>`: the live event feed.
  - 4) `POST /api/approvals/{id}/approve` and `.../reject`: the human's approval or rejection; approving executes it and changes cash.
  - 5) `GET /api/cash`: the checking balance.
  - 6) `POST /api/reset`: resets the DB.
  - Also added `GET /`, `/api/health`, `/api/tickets/{id}`, `/api/tickets/{id}/resolve`, `/api/approvals`, `/api/drafts`, and `/api/runs`.
  - CORS is open so the dashboard (localhost on another port) can call the API.
- `backend/events.py` — the live event feed. It records loop starts, tool calls and results, questions to teammates, reports, and failures, each with a sequence number (seq). The board fetches only events after the last seq it saw.
- `backend/ops_loop.py` — on Windows, `uvicorn --reload` runs the app on an event loop that cannot start subprocesses. So everything that launches the MCP server (team runs and the API's MCP calls) runs on a loop in a separate thread.
- Added `list_tickets` (all tickets) and `reset_working_db` (human-only) to the MCP server, bringing it to 26 tools. The backend does not open the DB directly either.
- Added `fastapi` and `uvicorn[standard]` to `requirements.txt`. Also created `backend/README.md` (setup, run, routes) and `.env.example`.
- Added section 8, "Backend API Routes" (one line per route), to both harness files, and updated the section 4 tool tables and `mcp_server/README.md`.

### What was checked

- Ran `uvicorn main:app --reload --port 8000` (the uvicorn in the HW 5 `.venv`) in the terminal; http://localhost:8000 responded with 200.
- Editing a file made `--reload` restart, and the API kept working afterwards.
- Port conflicts:
  - 8000 was kept for the HW 4 backend, but HW 4 is not running now, so there was no conflict.
  - The personal project (8420/5620) and Lecture 12 (8012/5412) do not overlap with 8000.
- Real run (ticket 102, ~73k tokens):
  - The event feed showed, live: Boss plans → Facilities asks Accounting → Accounting files the rent request → Boss reports.
  - Starting another ticket or resetting during the run was blocked with 409.
- Human approval:
  - Approving with an agent's name returned 403.
  - Approving with a person's name paid $2,400, and the balance went from $3,400 to $1,000.
  - Approving the same request again returned 409; a nonexistent request returned 404.
  - A resolved ticket dropped out of the open list, and running it again returned 409.
- Reset:
  - It first failed because Windows cannot replace a DB file that is open.
  - Fixed it so the MCP server always closes its connections and reset overwrites the contents with SQLite backup instead of swapping the file.
  - After the fix, reset brought the balance back to $3,400 and all 3 tickets back to open, with every table and row matching the original DB.

---

## Problem 8: Frontend Dashboard (React + Vite + TypeScript)

### Prompt 1

Problem 8 is the frontend.

In the @1_Homework/HW 5/frontend folder we'll build a frontend dashboard with React + Vite + TypeScript. It has to call the backend routes made in Problem 7. For now I'll specify the minimum features below. (Let's discuss and decide anything else needed together. Let's make it fun and varied.)

1) List the 3 tickets.
2) When I pick one ticket (click), have the agent team work on it.
3) Show each of the agents (I think it'd be good for the agent design to follow Marvel's Avengers), and show in speech bubbles what they are saying or doing (while working the ticket's mission). Since the bubbles only show the latest action, let me open a window at the bottom of the page or with a tab to see all the bubbles so far, plus the interactions between agents and their outputs, accumulated.
4) When the work is done and the human's decision is complete, mark the ticket resolved (slam a cool stamp on it).
5) Also show a short summary of what each agent did on the ticket.
6) Let the human decide on payments/purchases (when Boss brings the final options). If I Deny, I'd like to be able to enter a short reason and re-run the agents based on that feedback. (The backend will probably need changes too.) Add cool animations for Approve/Deny. And could you also make the agents' facial expressions or reactions respond to it?
7) Always show the checking balance somewhere. It must reflect the real current balance — cash decreases on purchases or payments. Add an animation of the cash going down too. And let me see the accumulated transactions when I press a button.

The dashboard should look good, be readable, and be easy to take in at a glance. Make it creative — a screen people would actually want to sit down and work at.

Make the frontend communicate well with the backend (http://localhost:8000), and in the backend allow the Vite page (usually port 5173, but use a port not used by my other projects or assignments) so the browser can call the routes. The board must start with "npm run dev". Make sure this command works in the terminal for both me and the grader.

Create output/design.md and explain well how I designed my dashboard frontend and why (including the special features).

Before building, let's talk through more ideas to make the frontend design richer, and then carry it out.

### Prompt 2

Can you do it in Korean?

### Prompt 3

Show me what the 4 things are.

### Design decisions (my choices on the AI's four questions)

- **Heroes**: original Avengers-inspired characters. The repository is public, so no Marvel names, logos, or artwork.
- **Theme**: a bright Yale Blue HQ (white + Yale Blue).
- **Re-run after a deny**: only when a button is pressed (saves tokens).
- **Extra features**: token fuel gauge, cash outlook bars, Expected vs Actual comparison, sound effects (can be turned off). All of them, with feedback after trying it.

### What this problem produced

- `frontend/` — React 19 + Vite 8 + TypeScript.
  - `npm run dev` → http://127.0.0.1:5455. Port 5455 is not used by any other project, so it is fixed in `vite.config.ts`.
  - Screen layout: mission board (3 tickets, Assemble button), hero bay (5 heroes, speech bubbles, light beams when work is handed over, token fuel gauge), decision desk (Boss's recommendation, voice of the customer, approve/deny, CS draft), comms log drawer (all bubbles, per-hero summary, Expected vs Actual), an always-visible balance (odometer animation and transaction list), and cash outlook bars.
  - Heroes: Captain Yale (Boss), Iron Stock (Inventory), Doctor Margin (Accounting), The Fortress (Facilities), Friendly Neighbor (Customer Service). All are hand-drawn SVGs with six expressions.
  - Animations:
    - Approve: APPROVED/PAID stamp, coins, the number rolling down, heroes happy.
    - Deny: DENIED stamp, the card shakes, heroes look worried.
    - Done: MISSION COMPLETE stamp.
  - Sound effects are synthesized in the browser and off by default.
- Backend additions:
  - Re-run with deny reasons (`feedback` on `POST /run`, an OWNER FEEDBACK block in Boss's and the team's prompts).
  - `GET /api/transactions` and `GET /api/runs/{id}/trace`.
  - Finished run results are saved in `output/team_runs/` (they survive a restart).
  - Live events now carry the team's running token total and loop count.
  - CORS lists 5455 explicitly.
- `output/design.md` (English; a file the assignment names) — concept, layout, visual language, how each requirement is met, special features, safety, and accessibility.
- Updated `frontend/README.md` and the route tables in both harness files and `backend/README.md`.

### What was checked

- Ran `npm run dev` in the terminal. http://127.0.0.1:5455 and http://localhost:5455 returned 200, and CORS allowed 5455.
- The TypeScript check (`tsc --noEmit`) and `npm run build` passed.
- Checked the whole flow in the browser with ticket 102.
  - Assemble showed the LIVE badge, speech bubbles, a Facilities → Accounting beam, and the fuel gauge.
  - When Boss's report arrived, a toast appeared and the decision desk filled in.
  - Entering a deny reason stamped DENIED and showed the re-run panel.
  - Re-ran with feedback. The reason was passed through as written, and Boss answered "hold until 09-02; the $300 cushion is $140 short."
  - The approve animation was checked with a TEST rent request created through the MCP tool. The balance went from $3,400 to $1,000, the ticket was stamped MISSION COMPLETE automatically, and one transaction appeared.
  - The comms log, summary, and Expected vs Actual tabs worked (102 re-run: first call matched, hand-offs 2/3, tools 5/6).
- Problems found and fixed:
  - Newer browsers return a Promise from `scrollIntoView`. It was being handed to React as a cleanup function, which blanked the page; fixed.
  - Speech bubbles overlapped, so the heroes were spread out and bubbles were limited to 4 lines.
- Usage: this testing used about 137k tokens (first run ~67k + re-run ~70k). The DB was reset after testing.

### Prompt 4 (feedback after trying it)

The agents' conversations and wording cover each other up and are hard to see; can we improve it with design or layout? And for cash, the current balance matters, but I'd also like a visual history of what was spent on what, and how much, out of the whole starting budget (in a cumulative form). It would also be good to write our mission in the Campus Customs HQ title at the top. And the total tokens are nice, but it'd be good to show each agent's token usage too. And when a mission is complete, it'd be good to also show the cash and tokens that went into it (small).

### What was changed

- **Speech bubbles covering each other**: rearranged the hero bay.
  - Boss sits on top with a wide speech box beside him.
  - The four specialists each have their own column with a fixed speech box under the avatar, so they cannot overlap.
  - Added a "Hand-offs between heroes" feed underneath. It shows, as chat lines, who asked whom (asks), who answered (answers), and who reported to Boss (reports to).
  - Beams are drawn between the measured avatar positions, and specialist-to-specialist beams are curved.
- **Budget history**: one bar for the starting budget (current balance + everything paid so far), cut cumulatively into each payment in its own color (rent green, invoice red, purchase order amber, remaining balance blue). Below it is a step list showing the running balance after each payment.
- **Mission statement**: added "Our mission: get every customer the right gear, keep the shop's doors open, and never spend a dollar the owner hasn't approved." under the title.
- **Tokens per agent**:
  - Each hero has a 🪙 token chip.
  - The fuel gauge is split by hero color, with a legend.
  - The backend's live report events now carry the agent's own tokens (excluding teammates it delegated to).
- **Usage on completed cards**: under the MISSION COMPLETE stamp, a small line such as "💵 $2,400.00 paid · ⛽ 137k tokens (2 runs)". The backend's `GET /api/tickets` returns `cash_spent`, `tokens_used`, and `runs` for each ticket.
- Updated `output/design.md` for the new layout and features.

### What was checked

- `tsc` and `npm run build` passed; no console errors.
- The user had reset the DB, so there was no real data. Fake events and transactions were therefore fed only into the check browser tab to verify the screen. The backend and DB were untouched, and no tokens were used.
  - Speech boxes did not overlap.
  - The hand-off feed, per-hero tokens, the budget bar and step list ($3,400 → −$840 → −$2,400 → −$8 → $152), and the usage line on the completed card all appeared.
- The servers the user started (8000, 5455) kept responding.

### Prompt 5 (running it myself)

I'd like to test the terminal commands from Problems 7 and 8 myself.

### What was done

- So I could run them myself, the AI shut down the backend (8000) and dashboard (5455) it had started, and confirmed the ports were free with no processes left behind.
- I was given the commands to run in two terminals, in order: activate the virtual environment → `uvicorn main:app --reload --port 8000` in `backend`, and `npm run dev` in `frontend`.

---

## Problem 9: Real Runs on the Three Tickets and the Results

### Prompt 1

Let's go to Problem 9. Before testing the agents on the 3 tickets, reset @1_Homework/HW 5/data/campus_customs_new.db so we can start fresh. Show all the tickets properly on the dashboard. (This is a functional addition: when a ticket is resolved it moves down, and tickets still open are shown at the top of the list — you get what I mean? Can it be done with only a frontend change?) Open @1_Homework/HW 5/output/desk_tickets.html and add content to the Actual section of each ticket tab (which agents did the work, what they delegated, which tools they used). Keep the Expected section and write in the Actual section. In the Cash tab of @1_Homework/HW 5/output/desk_tickets.html, itemize the money:
1) the starting checking balance after the reset, 2) for each ticket, when it was resolved, how cash changed and why (which payment? which purchase? $ amount), 3) the ending balance — this must match the value in the working DB's cash_accounts.

output/resolved_tickets.json — for each ticket, record the id, final status, a short outcome, what each agent contributed, the human approvals, and so on.
output/resolved_board.html — a page that opens on double-click; I think screenshots of the React board showing each ticket resolved would do. (You can do this too, right?)

Also record the results of the real runs in @1_Homework/HW 5/output/audit_trail.json, and finish the 2 harness files. The harness files must cover the tables, MCP tools, the five agents, API routes, the dashboard, and the safety rules well.

Here's something that came up while I was using it: I denied the rent and, as the deny reason, asked whether a discount was possible. Of course a discount isn't possible. So the agents concluded "nothing we can do" and the final result ended as a denial — doesn't that make no sense? Since a discount isn't possible, shouldn't they ask for approval again? In the end it's something that has to be paid, right?

### My decisions (human approvals)

After the three tickets were run for real, I decided as follows based on the AI's summary of the recommendations. The approver name was recorded as Yonghyuk Choi.

- 101: approved both the invoice 501 payment ($840) and the purchase order for one size-S tee ($8).
- 102: approved the $2,400 rent.
- 103: gave feedback on the first result (no discount, ask about a size mix) and re-ran it. The feedback was "Please propose a concrete bulk discount price within the 40% margin policy for the hoodies we can actually supply (for example a size mix from stock), so I can approve a quote for the club." I approved the second result, discount request #4 ($36.67 × 20 = $733.40, M 8 + L 12).

### What this problem produced and fixed

- **Fixed the rent-denial problem**: rent and an open vendor invoice are *obligations*, so a denial does not make them go away.
  - Changed the prompts (`shared_rules.md`, `boss.md`, `accounting.md`) and the re-run feedback block. When the owner's alternative is not possible, the team explains why and files a new payment request.
  - Added a check to Boss's final report (`unrequested_obligations`). If linked rent or an invoice is unpaid with no request waiting, the report is sent back.
- **Dashboard**:
  - Open tickets now sort to the top and resolved ones to the bottom. Only the frontend changed.
  - Added URL parameters (`?ticket=`, `&drawer=`) for screenshots.
  - An approved discount is now stamped APPROVED, not PAID.
- **Runs**: reset the DB and ran 101, 102, and 103 (including the re-run) for real. The 4 runs used 358,510 tokens.
- `output/desk_tickets.html`:
  - Each ticket's Actual section records the first agent called, the delegation flow and tools per loop, the comparison with Expected, and the owner's decisions and outcome.
  - The Cash tab records the $3,400 starting balance, the 3 payments with reasons, the discount (no cash change), and the $152 ending balance, checked against the DB.
- `output/resolved_tickets.json` — per ticket: final status, a short outcome, run records, each agent's contribution (what it did, tools, tokens), delegations, the owner's decisions, drafts, and cash spent.
- `output/resolved_board.html` — 5 dashboard screenshots taken with headless Edge (the 3 tickets, the hero summary, Expected vs Actual), embedded in one file that opens on double-click.
- `output/audit_trail.json`:
  - The loops and summaries of the real runs are recorded.
  - Added a `human_decision` entry type so the owner's decisions are kept too (the backend logs approvals, rejections, closes, and resets).
  - The 7 decisions in this run were backfilled from the DB.
- Finished both harness files: a table of contents, the ticket status flow, owner decisions and re-runs, the obligations-vs-choices rule, 2 new safety rows, actual token usage, the audit entry types, section 9 (dashboard), and section 10 (run results).

### What was checked

- Right after the reset, every table and row of the working DB matched the original.
- The obligation check was tested without an LLM: it flags when there is no request, passes once a request exists, and flags again after a denial.
- The $152.00 ending balance matched `cash_accounts` (checking): 3 payments totaling $3,248, invoice 501 `paid`, and the lease's next due date 2026-10-02.
- The audit trail contains no customer names, and only gpt-6-luna is recorded as the model.

---

## Problem 10: Reflection (desk_tickets.html Reflection tab)

### Prompt 1

Problem 10 is the Reflection. Open the Reflection tab in @1_Homework/HW 5/output/desk_tickets.html and write it in my own vibe — detailed and thorough. It must cover:

* How I would evaluate the agents' performance on each ticket, and why I'd evaluate it that way
* For each ticket, how do Actual and Expected compare?
* Compared with one agent with tools, which is simpler? Why?
* Based on the tools you built, describe 3 new problems Campus Customs could solve.
* Based on the tools you built, describe 3 problems Campus Customs probably could not solve (including the tools and agents needed to solve them)

I need to do this, but let me think about it first. Don't do it yet either — let's do it together!

### Prompt 2 (my thoughts)

Let's leave #4 as it is. Let's talk about the Reflection.

For ticket #101, I think I'd evaluate whether the team properly considers constraints like not being able to place a new apparel order before the invoice is handled, and whether those actions avoid creating a cash shortage or constraint for handling the other tickets. The reason is that this is clearly a task with an order to it, and the ability to handle it in that order matters. On top of that, I think explaining the reason to the customer well and suggesting suitable alternatives is also a skill. (A thought that just came to me — this might mean fixing the backend and frontend and retaking the screenshots — but to recommend a different product's S or another size of the same product to a customer because of the size shortage, should we offer a coupon or a price discount?)

For ticket #102, I think what matters is handling it at the right time — not late, but not too early either — and since a large amount of money goes out, it's important to check the ordering against the other tickets and the cash flow.

For ticket #103, I'd like the team to propose an appropriate discount rate while also checking the inventory accurately. Since not all of the customer's requested sizes are available, the team has to explain the situation well and present a special discount to persuade the customer. And it's important that the logic behind the discount proposal is solid, because it drives revenue and profit.

For Actual vs. Expected, I think the tool use matched the plan well, but the communication and delegation between agents was quite different. It was somewhat different from my original plan. I wanted them to think one level deeper, offer more options, and have a longer-term view, but the current agents don't seem to. They seemed more focused on clearing the tickets at hand.

Splitting the work like this definitely makes the code lighter, and because you can see exactly which part calls which tool for which task, and how the division of work, the order, and the discussion went, it's easier to understand the process and make decisions.

3 problems it can solve: gather customer history and give a Warning or OK sign on appropriate stock levels; set Black Friday discount rates by product and size based on stock levels; shortlist candidate office buildings to move to within the budget.

3 problems it probably can't solve: predict how revenue and profit change with the discount rate to set the optimal discount (it would need forecasting logic and to be able to solve an economic equation); predict the business impact of adding or removing product lines (also hard — it would need tools similar to the previous problem, something like a Sales Agent?); for product purchases, work out the right quantity to buy and negotiate the purchase cost by quantity (it would need a purchasing-department agent).

That's what I've thought through; organize it well, capture what I mean, and put it in the Reflection.

### What this problem produced

- Filled in the Reflection tab of `output/desk_tickets.html`. It is a file the assignment names and graders read, so it is written in English, in my voice ("I"). Each point is backed by evidence from the real runs.
  1. **Evaluation criteria and results per ticket**: turned my criteria into rubric tables with a grade (Strong / Adequate / Weak) and evidence.
     - 101: ordering and cash discipline Strong, customer explanation Adequate, thinking one level deeper Weak.
     - 102: verification and cash flow Strong, payment-timing reasoning Adequate. Also records the rent-denial fix.
     - 103: inventory accuracy Strong. Discount logic and persuasion Adequate: the team gave a single value at the policy floor, with no tiered options.
  2. **Actual vs. Expected**: the first agent matched on all three; tools 9/12, 7/9, 10/12. Delegation was mostly Boss assigning steps in order, with only one direct conversation (102). Recorded concrete examples of the missing depth and long-term view, and their causes in the design.
  3. **One agent vs. the team**: the team is easier to understand, control, and trust, and safer through separated permissions. One agent is easier to build and uses fewer tokens (the team used 83k–96k per run, 358,510 in total). Conclusion: "the single agent is simpler to make; the team is simpler to manage."
  4. **3 solvable problems**: a stock Warning/OK signal from customer demand, Black Friday discounts by stock level, and shortlisting new space within budget, each with the tools it uses. The third carries a condition ("if the candidates are posted as a ticket"), because the DB has no listings.
  5. **3 unsolvable problems**: the profit-maximizing discount, the impact of adding or dropping product lines, and purchase quantity and price negotiation, each with the new tools and new agent it needs (Pricing / Sales Analyst, Sales / Merchandising, Procurement).
- My idea for 101 (offering a coupon or small discount when recommending a substitute size) went into the Reflection as a next improvement, without changing the system.

---

## Problem 11: GitHub Submission

### Prompt 1

No, I don't think I have room to invest another 1–2 hours here. I wrote the reflection well, so I think that will be taken into account. If I were really building the system I would fix it, but this is an assignment. Later, in the Final Project, I think I'll have to do this kind of thing by going around the iteration loop many times.

Let's move on to Problem 11. Now we push to GitHub. I'll push and submit only that URL for the assignment, and also save the URL separately in output/github_url.txt. For the gitignore, refer to HW 4, but this time I'll also push the @1_Homework/HW 5/data folder, so the grader can evaluate faster. The README should cover: that you must copy the Original DB to make the Working Copy and run on it, starting the MCP server, starting the FastAPI backend, starting the React board, and resetting the DB (before running all 3 tickets? I'm not sure what this means. I'd understand it if it were about how to reset after running them all, but it says "Before a full 3-ticket run"). The capture is the Expected layout for HW5. I don't think extra parts matter, as long as they aren't unnecessary files. If anything is missing it'll be a problem, so check it.

(I also sent a capture of the expected folder layout given by the assignment.)

### What this problem produced

- Compared against the expected layout. Created the 3 missing items: `.gitignore`, the root `README.md`, and `output/github_url.txt`. Everything else was present; the extras are the English versions of the docs and supporting code.
- `.gitignore` — based on HW 4, but the `data/` folder (the original DB and the working copy) is pushed. Left out: `.env`, the virtual environment, `node_modules`, build output, `data.zip`, SQLite temporary files, and the development audit log that had the masking bug.
- Root `README.md` (English) — what it is, requirements, setup, then in the order I asked: 1) copy the original DB to make the working copy, 2) start the MCP server, 3) start the FastAPI backend, 4) start the React board, 5) reset the DB before a full run (4 ways, plus how to get the final state back after a reset). It also has a table pointing to the deliverables.
- What "Before a full 3-ticket run" means: reset the working DB to the original values **before** running all three tickets from the start. That way every full run starts from the same point (cash $3,400, all tickets open) and the results can be compared. It is the same as the shop rule "reset before a full ticket-resolving run."
- The working DB that is pushed is in its final state after the Problem 9 run (balance $152, all three tickets resolved), so the grader can see the results right away.
- `output/github_url.txt` — https://github.com/Yonghyuk-Yale/mgt409-hw5

### Prompt 2 (final check from the grader's side)

It looks like it uploaded fine. Now, from the grader's point of view, clone the contents of that URL into a virtual space and grade it. Check carefully against the grading criteria I've sent you, whether it runs well, whether there are any problems, and whether the results come out like the output. It's the final check, so do it accurately and thoroughly!

### What the final check did

- Cloned the GitHub URL fresh into a temporary folder and followed the README in order: virtual environment → install → copy `.env` → MCP server (the `.mcp.json` command and HTTP mode) → backend → dashboard install, build, and run. All worked. Only the ports were changed to avoid ones in use.
- All 15 backend routes responded as expected: a nonexistent ticket returned 404; re-running a resolved ticket and re-approving an executed payment returned 409.
- Did one real run in the clone: reset per the README → run 102 (74,214 tokens) → an approval under an agent's name was refused → approving under the grader's name moved cash from $3,400 to $1,000 → closed the ticket. Every step was written to the audit trail, and the run result was saved to a file.
- An automated cross-file check of 97 items all passed: DB amounts, result JSON fields, runs and tokens in the audit trail, HTML tabs / placeholders / external files, harness figures, smoke-test values, model names (only gpt-6-luna), no customer names in the audit trail, required prompt files, and the Problem 1–11 logs.
- Fixed one thing: the dashboard's Expected vs Actual tab showed 8/9 for 101's tool match, which differed from the 9/12 in `desk_tickets.html`. The dashboard now counts the same Expected table row by row (9/12, 7/9, 10/12), the matching screenshot in `resolved_board.html` was retaken, and the fix was pushed to GitHub.
