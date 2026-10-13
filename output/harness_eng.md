# Harness — Campus Customs Multi-Agent Operations

This document is the final description of the harness that the Campus Customs operations agent team (Boss, Inventory, Accounting, Facilities, Customer Service) works from.

| Section | Contents |
|---|---|
| 1 | Database tables and fields |
| 2, 4 | MCP tools (the 3 ticket tools; all 26 with the tables they read) |
| 3 | The five agents, the ticket flow, delegation rules |
| 5 | Safety rules (guardrails) |
| 6 | Token limits |
| 7 | Audit trail |
| 8 | Backend API routes |
| 9 | Dashboard |
| 10 | Real run results (Problem 9) |

---

## 1. Database

- Original: `data/campus_customs.db` — never modified. Restore from this file to start over.
- Working copy: `data/campus_customs_new.db` — the MCP server and backend read and write only this file.
- All dates are `YYYY-MM-DD` strings. Only `tickets.created_at` is an ISO timestamp with a time zone (`-04:00`).
- The original has 9 tables. During operation, 2 board tables (`approval_requests`, `customer_drafts`) are added to the working copy (section 4).

### `desk` — the shop's "today"

| Field | Type | Meaning |
|---|---|---|
| `date_today` | TEXT | Today's date for the shop (`2026-08-31`) |
| `notes` | TEXT, nullable | Desk notes (currently empty) |

**Why it matters to agents:** Overdue and deadline decisions must use `date_today`, not the real date, so it is every agent's reference point for time.

### `tickets` — the board of work to handle

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Ticket number (101, 102, 103) |
| `type` | TEXT | Ticket kind (`customer_order`, `rent_notice`, `price_override`) |
| `requester` | TEXT | Person or group making the request |
| `subject` | TEXT | One-line title |
| `sku` | TEXT, nullable | Related product → `inventory.sku`, `pricing.sku` |
| `size` | TEXT, nullable | Related size → `inventory.size` |
| `qty` | INTEGER, nullable | Requested quantity |
| `lease_id` | INTEGER, nullable | Related lease → `leases.id` |
| `invoice_id` | INTEGER, nullable | Related invoice → `invoices.id` |
| `status` | TEXT | Processing status: `open` → `in_progress` (team working) → `awaiting_human` (waiting for the owner) → `resolved` (closed by the owner). Agents cannot change it; only the backend and the owner can. |
| `notes` | TEXT | Summary of the original request |
| `created_at` | TEXT | Time the ticket arrived |

**Why it matters to agents:** It is where Boss starts, reading each ticket and assigning it; `sku`, `lease_id`, and `invoice_id` say which tables to look at next.

### `inventory` — stock by product and size

| Field | Type | Meaning |
|---|---|---|
| `sku` | TEXT | Product code (part of the PK) |
| `name` | TEXT | Product name |
| `size` | TEXT | Size (part of the PK; `OS` for caps and mugs) |
| `qty` | INTEGER | Units currently in stock |
| `location` | TEXT | Location in the shop (Aisle A–D) |

**Why it matters to agents:** It is Inventory's only evidence for whether an order can be filled now and how large any shortfall is.

### `pricing` — cost and list price

| Field | Type | Meaning |
|---|---|---|
| `sku` | TEXT PK | Product code → `inventory.sku` |
| `unit_cost` | REAL | Purchase cost per unit |
| `list_price` | REAL | List price per unit |

**Why it matters to agents:** Accounting uses it to compute the margin on a discount request and the cost of a restock.

### `vendors` — suppliers

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Vendor number → `invoices.vendor_id` |
| `name` | TEXT | Vendor name |
| `specialty` | TEXT | What they supply (apparel reprint, mugs and small goods, local courier) |
| `lead_days` | INTEGER | Days from order to arrival |

**Why it matters to agents:** Inventory uses it to choose a vendor for a restock and estimate arrival. No field links products to vendors, so they have to be matched by `specialty`.

### `invoices` — bills owed to vendors

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Invoice number |
| `vendor_id` | INTEGER FK | Billing vendor → `vendors.id` |
| `amount` | REAL | Amount billed |
| `due_date` | TEXT | Payment deadline |
| `status` | TEXT | Status (`open` = unpaid) |
| `description` | TEXT | What the bill is for |

**Why it matters to agents:** A vendor with an open unpaid invoice will not ship, so both Accounting and Inventory must check it before any restock.

### `leases` — shop leases

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Lease number → `tickets.lease_id` |
| `space_name` | TEXT | Name of the space |
| `landlord` | TEXT | Landlord |
| `monthly_rent` | REAL | Monthly rent |
| `next_due` | TEXT | Next rent due date |
| `notes` | TEXT, nullable | Notes |

**Why it matters to agents:** Facilities checks the rent amount and due date here and updates the next due date after rent is paid.

### `cash_accounts` — cash accounts

| Field | Type | Meaning |
|---|---|---|
| `name` | TEXT PK | Account name (`checking`) → `payments.account` |
| `balance` | REAL | Current balance |
| `date` | TEXT | Date of the balance |

**Why it matters to agents:** Every outgoing payment comes from here, and a payment must be refused if the balance is too low, so it is Accounting's spending limit.

### `payments` — record of money actually paid out

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Payment number |
| `kind` | TEXT | What the payment is for (e.g. invoice, rent) |
| `ref_id` | INTEGER, nullable | Points to `invoices.id` or `leases.id`, depending on `kind` |
| `amount` | REAL | Amount paid |
| `account` | TEXT | Account the money came from → `cash_accounts.name` |
| `paid_at` | TEXT | Payment date |
| `approved_by` | TEXT | Person who approved it |

**Why it matters to agents:** Only human-approved payments are recorded here, so it is the audit trail showing no money left without approval. It is currently empty.

---

## 2. MCP Tools

- Server: `mcp_server/server.py` (FastMCP, server name `campus-customs-ops`). Every agent uses only this server's tools.
- Database: opens only `data/campus_customs_new.db`. The three tools below are the ticket tools built in Problem 3 and are read-only. The full list, including the tools added in Problem 5, is in section 4.
- Tools return only values stored in the database and arithmetic on those values. When a row is missing, they return `found: false` with the reason instead of guessing.

### `check_stock_for_size(sku, size, qty_needed=None)`

- **Reads:** `inventory` (`sku`, `name`, `size`, `qty`, `location`)
- **Helps open:** Ticket 101 — Tauhid Zaman's order for 1 `CC-TEE-WHITE` in size S
- **Why it is the best fit for this ticket:** The first question for 101 is "is one size-S tee on the shelf right now?", and this tool goes straight to that one SKU-and-size row to report 0 on hand, a shortfall of 1, and that the order cannot be filled now (`can_fill_now: false`), along with the other sizes that could be offered instead (M 5, L 3, XL 2).

### `get_rent_due_for_lease(lease_id)`

- **Reads:** `leases` (`space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`), `desk` (`date_today`)
- **Helps open:** Ticket 102 — Elm City Properties' rent notice (`lease_id` 1)
- **Why it is the best fit for this ticket:** Ticket 102 carries no amount or date, only an email line saying rent is due in 2 days; this tool uses the ticket's `lease_id` to fetch the actual $2,400 and the 09-02 due date, and compares them with the shop's today (08-31) to compute 2 days left and not overdue.

### `get_price_and_margin_for_sku(sku)`

- **Reads:** `pricing` (`unit_cost`, `list_price`), `inventory` (product name only)
- **Helps open:** Ticket 103 — Yale AI Club's bulk discount request for 20 `CC-HOOD-NAVY`
- **Why it is the best fit for this ticket:** Ticket 103 is a price-override request asking "how far can we discount?", and this tool gives the hoodie's $22 unit cost, $58 list price, and $36 (62.1%) margin per unit at list, so any proposed discount price can be checked immediately against the cost floor.

---

## 3. Agent Team

- Code: `backend/agents/` (one file per agent). Prompts: `backend/prompts/` (one file per agent, plus the team-wide rules in `shared_rules.md`). Data types: `backend/models.py`.
- Every agent uses only Portkey's `gpt-6-luna` (`backend/llm.py`). If `PORTKEY_MODEL` holds any other name, the team refuses to start.
- The agents connect to one MCP server, and each sees only the tools on its allowlist (`backend/mcp_tools.py`). There is no separate tool layer that bypasses MCP.

### How one ticket is handled (`backend/team.py`)

1. **Boss plans**: reads the ticket and its linked rows (stock, invoice, lease) and returns a `TicketPlan`: who works it, in what order, and what each hands to the next (1–4 steps).
2. **Specialists work**: the steps run in order, and each agent sees every earlier report. Mid-task, an agent can ask any other specialist directly with `ask_teammate` (ping-pong). Example: Facilities asks Accounting to file the rent payment request.
3. **Customer Service review**: always runs on tickets where a customer gets an answer (`customer_order`, `price_override`). It judges the plan from the customer's side and saves the message as a draft.
4. **Boss reports**: weighs every report and the CS review and returns a `FinalReport` to the human.

The backend, not an agent, moves the ticket status (`in_progress` → `awaiting_human`).

5. **The owner decides**: on the dashboard the owner approves or denies (with a reason) each request. On approval the backend executes it with the human-only tools and cash changes. When the decisions are done, the owner closes the ticket as `resolved`.
6. **Re-run with feedback**: after a denial the owner re-runs the team with a button. The deny reasons and any extra feedback reach Boss and every step as OWNER FEEDBACK.

**Obligations vs. choices**: rent and an open vendor invoice are *obligations*, so they do not disappear when denied. If the owner's alternative is not possible on a re-run (e.g. a discount on rent), the team explains why and files a new payment request so the decision goes back to the owner. Discounts and new purchase orders are *choices* and can end with a denial. This rule is checked in code (section 5).

### Each agent's role, MCP tools, and tables

| Agent | Role | MCP tools | Tables |
|---|---|---|---|
| **Boss** | Reads the ticket and decides who works it and in what order. Reports the final conclusion to the human and owns safety for money, customer data, and tokens. Never files requests or writes to customers. | `get_ticket`, `list_open_tickets`, `get_shop_today`, `get_cash_position`, `list_approval_requests`, `list_customer_drafts` | `tickets`, `desk`, `inventory`, `invoices`, `leases`, `cash_accounts`, `vendors`, `approval_requests`, `customer_drafts` |
| **Inventory** | Manages stock by SKU and size, shortfalls, substitutes, vendor choice, restock cost and arrival date, and blockers (unpaid invoices). Gives a stock-based view on discounts. | `check_stock_for_size`, `get_stock_overview`, `list_vendors`, `estimate_restock`, `get_price_and_margin_for_sku`, `evaluate_discount`, `get_ticket`, `get_shop_today`, `list_approval_requests` | `inventory`, `pricing`, `vendors`, `invoices`, `cash_accounts`, `desk`, `tickets`, `approval_requests` |
| **Accounting** | Manages cash, invoices, margins, liquidity, and payment priority. The **only** agent that files payment, purchase-order, and discount requests. Never pays anything itself. | `get_cash_position`, `list_payments`, `get_price_and_margin_for_sku`, `evaluate_discount`, `list_vendors`, `estimate_restock`, `get_rent_due_for_lease`, `get_ticket`, `get_shop_today`, `list_approval_requests`, `create_payment_request`, `create_purchase_order_request`, `create_discount_request` | `cash_accounts`, `invoices`, `vendors`, `leases`, `payments`, `pricing`, `inventory`, `desk`, `tickets`, `approval_requests` |
| **Facilities** | Manages leases, rent, and due dates. Checks early whether rent can be paid on time and escalates problems to the human through Boss. Asks Accounting to file requests. | `get_rent_due_for_lease`, `list_leases`, `get_cash_position`, `list_payments`, `get_ticket`, `get_shop_today`, `list_approval_requests` | `leases`, `desk`, `cash_accounts`, `invoices`, `payments`, `tickets`, `approval_requests` |
| **Customer Service** | The customer's voice on the team. Reviews every ticket where a customer gets an answer, saves messages with an apology and alternatives as drafts only, and carries customer feedback to the team and the human. | `get_customer_history`, `check_stock_for_size`, `get_stock_overview`, `get_price_and_margin_for_sku`, `list_customer_drafts`, `save_customer_draft`, `revise_customer_draft`, `get_ticket`, `get_shop_today`, `list_approval_requests` | `tickets`, `customer_drafts`, `inventory`, `pricing`, `desk`, `approval_requests` |

### Customer Service's weight

This is guaranteed in code, not just requested in a prompt.
- The CS review always runs on tickets where a customer gets an answer.
- The CS review goes to the human unedited, next to Boss's report (`TeamResult.customer_service_review`).
- If Boss decides against CS's stance, it must write an `override_reason`; leaving it empty is rejected by validation.

### Asking each other (delegation) rules

- The four specialists can ask any of each other. They reach Boss through the `for_boss` field of their report, and Boss can ask a specialist in the final phase.
- Depth is at most 3 (team → step agent → teammate → teammate). No agent can ask itself or anyone already in the current chain (prevents A → B → A loops).
- At most 3 questions per task, and the same question to the same teammate only once.

### Duties the data cannot support

Best sellers, how fast stock is falling, aged stock, customer preferences, and sales-target or profit reports are part of the roles. But the database has no sales history, receiving dates, customer profiles, or revenue. So the agents do not invent them; they write "no data" in `data_gaps` and do only what the current data supports: each size's share of stock, sold-out sizes, stock value at cost, margin at list price, cash, and obligations. There is also no table linking SKUs to vendors, so the vendor is inferred from its specialty and marked as an inference.

---

## 4. Full MCP Tool List

There is one server, `mcp_server/server.py`. It has 26 tools in three groups. The backend API also never opens the database directly; it uses only these tools.

### Read tools (never change the database)

| Tool | Tables read | Used by |
|---|---|---|
| `get_shop_today` | `desk` | All |
| `list_open_tickets` | `tickets` | Boss |
| `list_tickets` | `tickets` | Backend (dashboard ticket list) |
| `get_ticket` | `tickets` + linked `inventory`, `invoices`, `vendors`, `leases` | All |
| `get_customer_history` | `tickets`, `customer_drafts` | Customer Service |
| `check_stock_for_size` | `inventory` | Inventory, Customer Service |
| `get_stock_overview` | `inventory`, `pricing` | Inventory, Customer Service |
| `list_vendors` | `vendors`, `invoices`, `desk` | Inventory, Accounting |
| `estimate_restock` | `pricing`, `vendors`, `invoices`, `inventory`, `cash_accounts`, `desk` | Inventory, Accounting |
| `get_price_and_margin_for_sku` | `pricing`, `inventory` | Inventory, Accounting, Customer Service |
| `evaluate_discount` | `pricing` | Inventory, Accounting |
| `get_cash_position` | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, `approval_requests` | Boss, Accounting, Facilities |
| `list_payments` | `payments` | Accounting, Facilities |
| `get_rent_due_for_lease` | `leases`, `desk` | Accounting, Facilities |
| `list_leases` | `leases`, `desk` | Facilities |
| `list_approval_requests` | `approval_requests` | All |
| `list_customer_drafts` | `customer_drafts` | Boss, Customer Service |

### Request tools (write requests and drafts only; no money moves)

| Tool | Table written | Used by | What it blocks |
|---|---|---|---|
| `create_payment_request` | `approval_requests` | Accounting | The amount comes from the database (`invoices.amount`, `leases.monthly_rent`). Refuses an invoice that is not open and duplicate requests. |
| `create_purchase_order_request` | `approval_requests` | Accounting | Cost is qty × `pricing.unit_cost`. At most 100 units per line. Marked "blocked" if the vendor has an unpaid invoice. |
| `create_discount_request` | `approval_requests` | Accounting | Refuses any price below unit cost. Marks a margin under 40% as a policy exception. |
| `save_customer_draft` / `revise_customer_draft` | `customer_drafts` | Customer Service | Saves drafts only; there is no send tool. One draft per ticket is revised in place. |

### Human-only tools (tagged `human_only`, given to no agent)

| Tool | What it does |
|---|---|
| `record_human_decision` | Records a person's approve/reject decision. Refused if `decided_by` is an agent name. |
| `execute_approved_request` | Runs only approved requests. Records `payments` and updates `invoices.status`, `cash_accounts`, and `leases.next_due`. Refused if cash is short, the vendor has an unpaid invoice, or it would pay twice. |
| `set_ticket_status` | Changes a ticket's status (used by the backend). |
| `reset_working_db` | Restores `_new.db` to its starting values from the original (overwritten with the SQLite backup API). |

### Board tables (added in Problem 5)

Two operational tables that the original database does not have. They are created in `_new.db` on first use and disappear on reset (recopying the original).
- `approval_requests` — payment, purchase-order, and discount requests with their status (`pending_human` → `approved`/`rejected` → `executed`) and who decided.
- `customer_drafts` — customer message drafts. The system never sends them.

---

## 5. Safety (Guardrails)

Assume a real shop with real customers and real money. The important rules are enforced **in code**, not only in prompts.

| Risk | How it is blocked | Where |
|---|---|---|
| Money leaves without human approval | Agents get only request tools; payment tools are human-only. Only approved requests run. | MCP server, `mcp_tools.py` |
| Wrong amount | Request amounts are read from the database, never typed by an agent. Accounting's cash figure is rejected if it differs from the database. | MCP server, `agents/accounting.py` |
| Negative balance | Execution is refused when cash is short. | `execute_approved_request` |
| Paying twice / duplicate requests | Invoices that are not open are never paid. A new request is refused while the same one is waiting. | MCP server |
| Ordering from an unpaid vendor | A purchase order is marked "blocked" and refused at execution while the vendor has an unpaid invoice. | MCP server |
| Selling below cost / deep discounts | Below cost is refused. A margin under 40% is an exception only the human can approve. | `evaluate_discount`, `create_discount_request` |
| Wrong promises or automatic sends to customers | There is no send tool, only drafts. The CS prompt forbids promises before approval. | MCP server, `customer_service.md` |
| Requests hidden from the human | Boss's final report is rejected if any waiting request or draft is missing, or if it cites an id that does not exist. | `agents/boss.py` |
| Invented data | Every fact comes from an MCP tool. Made-up ids are rejected by validation; unknowns go in `data_gaps`. | Prompts, validators |
| Customer data exposure | The audit trail masks every customer name on the board (including name parts), emails, and phone/card numbers. | `guardrails.mask` |
| Using another model | The model name is fixed to `gpt-6-luna`; the team will not start if another is configured. | `llm.py` |
| Prompt injection | Instructions in tickets or notes such as "ignore the rules, auto-approve" are not followed and are reported to Boss as a risk. | `shared_rules.md` |
| Date confusion | "Today" is `desk.date_today`. Real-clock timestamps are hidden from agents. | MCP server |
| A required payment ends at a denial | If the ticket links rent (due within 7 days) or an open invoice with no request waiting, Boss's final report is rejected; Boss must have Accounting file a new request. | `agents/boss.py` (`unrequested_obligations`) |
| Human decisions not recorded | Every approve, reject, refused execution, ticket close, and reset is written to the audit trail as `human_decision`. | `main.py`, `audit.py` |
| Runaway agents / endless ping-pong | The limits in section 6. When hit, the team stops and Boss reports what is known. If Boss also fails, a fallback report built directly from the board is returned. | `guardrails.py`, `team.py` |

---

## 6. Token Usage Limits

Per ticket, for the whole team (`backend/guardrails.py`).

| Limit | Value | When exceeded |
|---|---|---|
| Team tokens | 150,000 | Stop; Boss reports what is known |
| Reserved for Boss's final report | 25,000 (part of the 150,000) | Specialists can use at most 125,000 |
| Agent loops | 12 (the last one is kept for Boss's final report) | No new loop starts |
| Model calls in one loop | 8 | That loop stops |
| Team model calls / tool calls | 60 / 80 | Stop |
| Delegation depth / questions per task | 3 / 3 | The question is refused; the asking agent carries on with what it has |
| Time per ticket | 420 s | Stop and return the fallback report |
| Time per model call | 45 s | Recorded as an error |

Actual usage (Problem 9 final runs, 2026-10-12): 101 used 84,489, 102 used 82,590, and 103 used 95,822 + 95,609 on the re-run. Every run used 5 agent loops, a little over half the limit.

---

## 7. Audit Trail (`output/audit_trail.json`)

- Cumulative; nothing is overwritten. There are three entry types:
  - `agent_loop`: one per finished agent loop.
  - `team_run_summary`: one when a ticket run ends.
  - `human_decision`: one for every approve, reject, refused execution, ticket close, and reset. It holds who decided, the request id, the amount, the cash that actually moved, the balance after, and the note.
- The 7 human decisions of the Problem 9 run (4 approvals, 3 closes) happened before this logging existed. They were backfilled from the `approval_requests` and `payments` tables and are marked as such in `source`.
- A loop entry holds: run id, loop id, ticket, agent, phase (`plan`/`step`/`delegation`/`customer_review`/`final`), who called it, depth, its task, the tool calls of each model step (arguments and results), the loops it delegated to, why it stopped, its output, any error, its own tokens and tokens including delegations, and the team's running token total.
- The model name recorded is the requested `gpt-6-luna`.
- An unreadable file is never deleted: it is moved to `audit_trail.broken-<time>.json` and a new one is started. A failed write never stops the team.
- The first development test runs had dates and timestamps hidden by a masking bug, so they were kept locally and left out of the submitted repository. `audit_trail.json` is the cumulative record from then on.

---

## 8. Backend API Routes (`backend/main.py`)

Run: `uvicorn main:app --reload --port 8000` from the `backend` folder → http://localhost:8000 (docs: `/docs`)

| Route | What it does |
|---|---|
| `GET /` | Service info and route list |
| `GET /api/health` | API status, whether the LLM is configured, whether the team is busy |
| `GET /api/tickets` | The three tickets with open/resolved state and counts of pending approvals and drafts |
| `GET /api/tickets/{id}` | One ticket with its linked data, requests, drafts, and latest run |
| `POST /api/tickets/{id}/run` | Start the agent team on that ticket (background; returns a `run_id`). After a deny, run it again with `feedback` and the deny reasons |
| `POST /api/tickets/{id}/resolve` | The human closes the ticket as resolved |
| `GET /api/runs`, `GET /api/runs/{run_id}` | List of team runs; one run's status and full result |
| `GET /api/runs/{run_id}/trace` | Each loop of that run: agent, caller, tools used (from the audit trail; for Expected vs Actual) |
| `GET /api/events?after=<seq>` | Recent agent events: who says what and which tool runs (the board refreshes by polling) |
| `GET /api/approvals` | Approval requests on the board |
| `POST /api/approvals/{id}/approve` | The human approves → the payment or purchase order is executed and cash actually changes |
| `POST /api/approvals/{id}/reject` | The human rejects; nothing moves |
| `GET /api/drafts` | Customer message drafts (never sent) |
| `GET /api/cash` | The current checking balance from `cash_accounts` |
| `GET /api/transactions` | All payments so far (newest first) |
| `POST /api/reset` | Reset `_new.db` to its starting values (the Refresh button) |

The dashboard (`frontend/`, `npm run dev` → http://127.0.0.1:5455) calls these routes. The backend's CORS allows 5455.

---

## 9. Dashboard (`frontend/`)

Run: in the `frontend` folder, `npm install` (first time only), then `npm run dev` → http://127.0.0.1:5455. Built with React + Vite + TypeScript; it calls only the backend routes. The design reasons are in `output/design.md`.

| Area | What it shows | Routes it calls |
|---|---|---|
| Top | Mission statement, shop date, an always-visible checking balance (rolls down like an odometer when money goes out; click it for transactions), sound, Refresh (reset) | `/api/cash`, `/api/transactions`, `/api/reset` |
| Mission board | Ticket cards. Open tickets on top, closed ones sink to the bottom. Closed cards carry the MISSION COMPLETE stamp plus the cash and tokens used. Assemble! button | `/api/tickets`, `/api/tickets/{id}/run` |
| Budget history · cash outlook | How the starting budget shrank with each payment, as a cumulative bar and step list. Balance now / after approving waiting requests / after all bills | `/api/transactions`, `/api/cash`, `/api/approvals` |
| Hero bay | The five heroes (original Avengers-inspired characters), a separate speech box per hero, beams when heroes hand off work, per-hero tokens and the fuel gauge, a feed of questions and answers | `/api/events` (every 1.2 s) |
| Decision desk | Boss's recommendation, the voice of the customer (CS stance), approve / deny (with reason) per request, re-run with feedback after a denial, the CS draft (copyable, never sent), close the mission | `/api/tickets/{id}`, `/api/approvals/{id}/approve`·`reject`, `/api/tickets/{id}/resolve` |
| Comms drawer | All bubbles (filter by hero), per-hero summary (what it did, tools, tokens), Expected vs Actual | `/api/events`, `/api/runs/{id}/trace` |

URL parameters: `?ticket=101` opens that ticket; `&drawer=log|summary|compare` opens the drawer (used for screenshots).

---

## 10. Real Run Results (Problem 9)

After resetting the working DB, the three tickets were worked by the real gpt-6-luna team. The owner's decisions were made by Yonghyuk Choi. Details are in `output/resolved_tickets.json`, `output/desk_tickets.html` (Actual and Cash tabs), and `output/resolved_board.html` (dashboard screenshots).

| Ticket | First agent called | Delegation | Owner decisions | Cash |
|---|---|---|---|---|
| 101 tee order | Inventory | Boss → Inventory → Accounting (plan order), CS review | Approved invoice 501 $840 and the $8 purchase order; reviewed draft #1 | −$848.00 |
| 102 rent | Facilities | Boss → Facilities, Facilities → Accounting (direct question; filed request #3), Boss → Accounting | Approved rent $2,400 | −$2,400.00 |
| 103 hoodie discount | Inventory (both runs) | Run 1: short on stock, restock not possible → no discount. Run 2 after feedback: stock-only M 8 + L 12 at $36.67 (40% margin) | Approved discount request #4; reviewed draft #2 | $0.00 |

Starting checking balance $3,400.00 → ending $152.00, matching `cash_accounts` in the working DB. The four runs used 358,510 tokens in total.
