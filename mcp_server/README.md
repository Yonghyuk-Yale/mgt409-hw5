# Campus Customs Operations MCP Server

## Why this server exists

Campus Customs is run by a team of AI agents — Boss, Inventory, Accounting, Facilities, and Customer Service — that work through the open tickets on the shop's board. This MCP server is the **single place where those agents get their tools**. Every agent reaches the shop's data through these tools, so the rules for reading and changing the data live in one place instead of being copied into each agent. There is no second tool layer: the backend connects to this server and gives each agent only the tools on its allowlist (`backend/mcp_tools.py`).

Tools return only what is stored in the database, plus simple arithmetic on those values (shortfall, days until due, margin, cash after obligations). When a row does not exist, the tool says so instead of guessing.

## Database file

- Uses **`../data/campus_customs_new.db`** — the working copy of the shop database.
- The original `../data/campus_customs.db` is never opened by this server, so it stays untouched for resetting.
- Read tools open the database in read-only mode. Request and human-only tools open it for writing.
- Two board tables are created on first write: `approval_requests` (payment, purchase-order, and discount requests waiting for a person) and `customer_drafts` (customer messages, never sent by the system). They are not in the original database, so a reset removes them.
- "Today" is always `desk.date_today`. Real-clock timestamps are stored for auditing but not shown to agents.

## Tools (26)

### Read tools — never change the database

| Tool | Reads | Used by |
|---|---|---|
| `get_shop_today()` | `desk` | All agents |
| `list_open_tickets()` | `tickets` | Boss |
| `list_tickets()` | `tickets` | Backend API (dashboard ticket list, with open/resolved) |
| `get_ticket(ticket_id)` | `tickets` + linked `inventory`, `invoices`, `vendors`, `leases` | All agents |
| `get_customer_history(requester)` | `tickets`, `customer_drafts` | Customer Service |
| `check_stock_for_size(sku, size, qty_needed=None)` | `inventory` | Inventory, Customer Service (built for ticket 101) |
| `get_stock_overview(sku=None)` | `inventory`, `pricing` | Inventory, Customer Service |
| `list_vendors()` | `vendors`, `invoices`, `desk` | Inventory, Accounting |
| `estimate_restock(sku, size, qty, vendor_id)` | `pricing`, `vendors`, `invoices`, `inventory`, `cash_accounts`, `desk` | Inventory, Accounting |
| `get_price_and_margin_for_sku(sku)` | `pricing`, `inventory` (name only) | Inventory, Accounting, Customer Service (built for ticket 103) |
| `evaluate_discount(sku, qty, discount_pct=None, unit_price=None)` | `pricing` | Inventory, Accounting |
| `get_cash_position()` | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, `approval_requests` | Boss, Accounting, Facilities |
| `list_payments()` | `payments` | Accounting, Facilities |
| `get_rent_due_for_lease(lease_id)` | `leases`, `desk` | Accounting, Facilities (built for ticket 102) |
| `list_leases()` | `leases`, `desk` | Facilities |
| `list_approval_requests(ticket_id=None, status=None)` | `approval_requests` | All agents |
| `list_customer_drafts(ticket_id=None)` | `customer_drafts` | Boss, Customer Service |

- **`get_ticket`** — the ticket plus the rows it links to, so the team sees hidden connections (e.g. a customer order tied to an unpaid vendor invoice).
- **`get_customer_history`** — the customer's tickets and drafts; the database has no customer profile, so this is the whole customer record.
- **`check_stock_for_size`** — units on hand and shelf location for one SKU in one size, the other sizes' stock, and (with `qty_needed`) the shortfall and whether the order can be filled now.
- **`get_stock_overview`** — every SKU's units by size, each size's share, sold-out sizes, and stock value at cost and at list. A snapshot only: no sales history or receiving dates exist.
- **`list_vendors`** — specialty, lead time, open invoices, whether the vendor will ship now, and the earliest arrival if ordered today. SKUs are not linked to vendors in the database; match by specialty.
- **`estimate_restock`** — cost at unit cost, arrival date, and any invoice blocking the vendor, plus cash on hand after the order.
- **`get_price_and_margin_for_sku`** — unit cost, list price, and margin per unit at list price.
- **`evaluate_discount`** — quoted price, total, gross profit, margin, whether it is within policy, the 40%-margin floor price, and the largest discount within policy.
- **`get_cash_position`** — cash, every open invoice (with days overdue), rent due within 30 days, cash after all obligations, and open requests that would move cash.
- **`list_payments`** — payments actually made, to avoid paying twice.
- **`get_rent_due_for_lease`** — the lease's space, landlord, monthly rent, next due date, the shop's today, days until due, and whether it is overdue.
- **`list_leases`** — every lease with days until due.
- **`list_approval_requests` / `list_customer_drafts`** — what is on the board, so nothing is requested or drafted twice.

### Request tools — file requests and drafts; no money moves

| Tool | Writes | Used by | Built-in checks |
|---|---|---|---|
| `create_payment_request(kind, ref_id, reason, requested_by, ticket_id=None)` | `approval_requests` | Accounting | `kind` is `invoice` or `rent`. Amount read from `invoices.amount` / `leases.monthly_rent`, never from the agent. Refuses an invoice that is not open and duplicates. Reports whether cash covers it. |
| `create_purchase_order_request(vendor_id, sku, size, qty, reason, requested_by, ticket_id=None)` | `approval_requests` | Accounting | Cost = qty × `pricing.unit_cost`. Qty 1–100. Marked blocked if the vendor has an open invoice. Refuses duplicates. |
| `create_discount_request(ticket_id, sku, qty, unit_price, reason, requested_by, size=None)` | `approval_requests` | Accounting | Refuses a price below unit cost. Marks a margin under 40% as a policy exception. Refuses duplicates. |
| `save_customer_draft(ticket_id, recipient, subject, body, written_by)` | `customer_drafts` | Customer Service | Saved as a draft; there is no send tool. |
| `revise_customer_draft(draft_id, subject, body, written_by)` | `customer_drafts` | Customer Service | Rewrites a draft in place so competing drafts do not pile up. |

`requested_by` / `written_by` must be one of the five agent names.

### Human-only tools — tagged `human_only`, never given to an agent

| Tool | What it does |
|---|---|
| `record_human_decision(request_id, decision, decided_by, note=None)` | Records a person's approve/reject decision. Refused if `decided_by` is an agent name. |
| `execute_approved_request(request_id)` | Carries out an approved request: records `payments`, marks the invoice paid, reduces `cash_accounts`, moves `leases.next_due` one month for rent. Refuses anything not approved, any payment the cash cannot cover (no negative balance), a purchase order while the vendor has an open invoice, and paying an invoice twice. |
| `set_ticket_status(ticket_id, status)` | Moves a ticket: `open`, `in_progress`, `awaiting_human`, `resolved`. Used by the backend. |
| `reset_working_db()` | Restores the working copy to the original's values with SQLite's backup API (in place, so it works while other clients have the file open). |

## Running

Packages come from the HW 5 `requirements.txt` (`fastmcp`), installed in the HW 5 `.venv`.

```powershell
# stdio (an agent or MCP client launches this)
..\.venv\Scripts\python.exe server.py

# Streamable HTTP on a free port (8000 is reserved by another project)
..\.venv\Scripts\python.exe server.py --http --port <free port>
```

The agent backend launches this server itself over stdio: one connection per ticket run (`backend/team.py`) and one long-lived connection for the API's own calls (`backend/ops_loop.py`). The backend API never opens the database directly.

### Connecting from Claude Code

`HW 5/.mcp.json` registers this server as `campus-customs-ops`. Open Claude Code with `HW 5` as the project folder and approve the server when prompted; it launches `.venv/Scripts/python.exe mcp_server/server.py` from that folder. On macOS/Linux, change the command to `.venv/bin/python`.
