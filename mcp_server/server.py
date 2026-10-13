"""Campus Customs operations MCP server — HW 5.

Every agent on the Campus Customs operations team (Boss, Inventory, Accounting,
Facilities, Customer Service) gets its tools from this server. The tools talk
only to the working copy ../data/campus_customs_new.db; the original
campus_customs.db is never opened here, so it stays clean for resets.

Tools only return what is in the database (plus arithmetic on those values).
When a row is missing they say so instead of guessing.

Three kinds of tools:
- read tools      — look things up; never change the database.
- request tools   — agents file approval requests and customer drafts. Money never
                    moves here: amounts are taken from the database, not from the agent.
- human-only tools (tag "human_only") — record a person's decision, execute an
                    approved payment, change ticket status. The backend never gives
                    these to an agent.

Run from this folder (stdio):  python server.py
Run (HTTP):                    python server.py --http --port <free port>
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"

# Shop policy, enforced here so no prompt can talk its way around it.
MIN_MARGIN_PCT = 40.0  # a quote below this margin is a policy exception the human must clear
MAX_ORDER_QTY = 100  # one purchase order line; larger orders are refused
AGENT_NAMES = ("boss", "inventory", "accounting", "facilities", "customer_service")
HUMAN_ONLY = {"human_only"}
# Real-clock timestamps stay in the database for auditing but are not shown to agents:
# the shop runs on desk.date_today, and a second calendar only confuses them.
_REAL_CLOCK_COLUMNS = {"created_at", "decided_at", "executed_at"}

mcp = FastMCP("campus-customs-ops")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"


def _check_db() -> None:
    """Make sure the working copy exists. A fresh checkout only has the original (from data.zip),
    so the first call creates the working copy from it; the original is only read."""
    if DB_PATH.exists():
        return
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(
            f"{ORIGINAL_DB} not found. Unzip the course's data.zip into the HW 5 folder first."
        )
    src = sqlite3.connect(f"file:{ORIGINAL_DB.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(DB_PATH)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()


@contextmanager
def _read_conn() -> Iterator[sqlite3.Connection]:
    """Open the working copy read-only and always close it (Windows keeps open files locked)."""
    _check_db()
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def _write_conn() -> Iterator[sqlite3.Connection]:
    """Open the working copy for writing, commit on success, roll back on error, always close.

    Also makes sure the board tables exist.

    `approval_requests` and `customer_drafts` are operational tables for the agent
    team. They are not in the original database, so they are created on first use
    (and disappear on reset, when the working copy is recopied from the original).
    """
    _check_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            ticket_id INTEGER,
            ref_id INTEGER,
            vendor_id INTEGER,
            sku TEXT,
            size TEXT,
            qty INTEGER,
            unit_price REAL,
            amount REAL NOT NULL,
            summary TEXT NOT NULL,
            reason TEXT NOT NULL,
            details TEXT,
            requested_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_human',
            shop_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            decision_note TEXT,
            executed_at TEXT,
            payment_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS customer_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            written_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            shop_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _shop_today(conn: sqlite3.Connection) -> str:
    """The shop's "today" comes from desk.date_today, never the real clock."""
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("desk table has no date_today row")
    return row["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _add_days(day: str, days: int) -> str:
    return date.fromordinal(date.fromisoformat(day).toordinal() + days).isoformat()


def _add_month(day: str) -> str:
    d = date.fromisoformat(day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, monthrange(year, month)[1])).isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _total_cash(conn: sqlite3.Connection) -> float:
    return float(conn.execute("SELECT COALESCE(SUM(balance), 0) FROM cash_accounts").fetchone()[0])


def _open_invoices(conn: sqlite3.Connection, today: str, vendor_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.status, i.description "
        "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open'"
    )
    args: tuple = ()
    if vendor_id is not None:
        sql += " AND i.vendor_id = ?"
        args = (vendor_id,)
    out = []
    for r in conn.execute(sql + " ORDER BY i.due_date", args):
        days_overdue = _days_between(r["due_date"], today)
        out.append({
            "invoice_id": r["id"],
            "vendor_id": r["vendor_id"],
            "vendor_name": r["vendor_name"],
            "amount": r["amount"],
            "due_date": r["due_date"],
            "description": r["description"],
            "days_overdue": max(0, days_overdue),
            "is_overdue": days_overdue > 0,
        })
    return out


def _margin(unit_cost: float, unit_price: float) -> dict:
    margin = unit_price - unit_cost
    pct = round(margin / unit_price * 100, 1) if unit_price > 0 else None
    return {"unit_margin": round(margin, 2), "margin_pct": pct}


def _floor_price(unit_cost: float) -> float:
    """Lowest unit price that still keeps MIN_MARGIN_PCT."""
    return round(unit_cost / (1 - MIN_MARGIN_PCT / 100), 2)


def _check_agent(name: str) -> str | None:
    if name not in AGENT_NAMES:
        return f"requested_by/written_by must be one of {list(AGENT_NAMES)}."
    return None


def _pending_commitments(conn: sqlite3.Connection) -> list[dict]:
    if not _table_exists(conn, "approval_requests"):
        return []
    rows = conn.execute(
        "SELECT id, kind, ticket_id, amount, summary, status FROM approval_requests "
        "WHERE status IN ('pending_human', 'approved') AND amount > 0 ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Read tools — tickets and the shop's day
# ---------------------------------------------------------------------------

@mcp.tool
def get_shop_today() -> dict:
    """Get the shop's "today" (`desk.date_today`) and any desk notes.

    Every agent must use this date — never the real calendar — to decide what is due,
    overdue, or late. Reads `desk`.
    """
    with _read_conn() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    return {"shop_today": row["date_today"], "notes": row["notes"]}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket on the board that is not resolved yet (id, type, requester, subject, status).

    Boss uses this to see the whole queue before planning. Reads `tickets`.
    """
    with _read_conn() as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, status, created_at FROM tickets "
            "WHERE status != 'resolved' ORDER BY created_at"
        ).fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket on the board, resolved or not, with its status.

    The dashboard's ticket list: id, type, requester, subject, status, and a plain
    open/resolved flag. Reads `tickets`.
    """
    with _read_conn() as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at "
            "FROM tickets ORDER BY id"
        ).fetchall()
    tickets = [{**dict(r), "is_resolved": r["status"] == "resolved"} for r in rows]
    return {"count": len(tickets), "tickets": tickets}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Read one ticket in full, plus the rows it links to.

    Reads `tickets`, and follows its links: `inventory` (sku/size), `invoices` (invoice_id),
    `leases` (lease_id). Use this first on every ticket — the links show which specialists
    the ticket really involves (e.g. ticket 101 is a customer order that is also tied to an
    unpaid vendor invoice).
    """
    with _read_conn() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"found": False, "ticket_id": ticket_id, "error": f"No ticket with id {ticket_id}."}
        today = _shop_today(conn)
        linked: dict = {}
        if t["sku"]:
            linked["inventory"] = [dict(r) for r in conn.execute(
                "SELECT size, qty, location FROM inventory WHERE sku = ? ORDER BY size", (t["sku"],))]
        if t["invoice_id"] is not None:
            inv = [i for i in _open_invoices(conn, today) if i["invoice_id"] == t["invoice_id"]]
            if inv:
                linked["invoice"] = inv[0]
            else:
                row = conn.execute("SELECT * FROM invoices WHERE id = ?", (t["invoice_id"],)).fetchone()
                linked["invoice"] = dict(row) if row else None
        if t["lease_id"] is not None:
            row = conn.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone()
            linked["lease"] = dict(row) if row else None
    return {"found": True, "shop_today": today, "ticket": dict(t), "linked": linked}


@mcp.tool
def get_customer_history(requester: str) -> dict:
    """Everything the shop has on one customer: their tickets and the drafts written to them.

    Customer Service uses this to understand who it is writing to. The database has no
    customer profile table, so tickets (type, subject, notes) and earlier drafts are the
    only record of a customer's needs and preferences. Reads `tickets`, `customer_drafts`.
    """
    with _read_conn() as conn:
        tickets = [dict(r) for r in conn.execute(
            "SELECT id, type, subject, sku, size, qty, status, notes, created_at FROM tickets "
            "WHERE requester = ? ORDER BY created_at", (requester,))]
        drafts = []
        if _table_exists(conn, "customer_drafts"):
            drafts = [dict(r) for r in conn.execute(
                "SELECT id, ticket_id, subject, status, shop_date FROM customer_drafts "
                "WHERE recipient = ? ORDER BY id", (requester,))]
    return {
        "requester": requester,
        "tickets": tickets,
        "drafts": drafts,
        "note": "No customer profile, purchase history, or preference data exists in the database.",
    }


# ---------------------------------------------------------------------------
# Read tools — inventory and vendors
# ---------------------------------------------------------------------------

@mcp.tool
def check_stock_for_size(sku: str, size: str, qty_needed: int | None = None) -> dict:
    """Check how many units of one SKU in one size are on the shelf.

    Use for customer orders (e.g. ticket 101: CC-TEE-WHITE, size S, qty 1).
    Reads `inventory`. Returns qty on hand and shelf location for that size,
    the stock of the SKU's other sizes (possible alternatives), and — if
    `qty_needed` is given — the shortfall and whether the order can be filled now.
    """
    sku, size = sku.strip().upper(), size.strip().upper()
    with _read_conn() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
            (sku,),
        ).fetchall()
    if not rows:
        return {"found": False, "sku": sku, "error": f"No inventory rows for SKU {sku}."}
    match = next((r for r in rows if r["size"] == size), None)
    if match is None:
        return {
            "found": False,
            "sku": sku,
            "size": size,
            "error": f"SKU {sku} is not stocked in size {size}.",
            "sizes_stocked": [r["size"] for r in rows],
        }
    result = {
        "found": True,
        "sku": sku,
        "name": match["name"],
        "size": size,
        "qty_on_hand": match["qty"],
        "location": match["location"],
        "other_sizes": [
            {"size": r["size"], "qty_on_hand": r["qty"]} for r in rows if r["size"] != size
        ],
    }
    if qty_needed is not None:
        result["qty_needed"] = qty_needed
        result["shortfall"] = max(0, qty_needed - match["qty"])
        result["can_fill_now"] = match["qty"] >= qty_needed
    return result


@mcp.tool
def get_stock_overview(sku: str | None = None) -> dict:
    """Snapshot of stock for every SKU (or one SKU): units by size, sold-out sizes, and stock value.

    Inventory uses this to spot sold-out sizes, thin sizes, and where units pile up, and to
    suggest substitutes. Reads `inventory` and `pricing`. This is a point-in-time count only:
    the database has no sales history and no receiving dates, so it cannot show what sells
    fastest or how long stock has sat on the shelf.
    """
    with _read_conn() as conn:
        sql = (
            "SELECT i.sku, i.name, i.size, i.qty, i.location, p.unit_cost, p.list_price "
            "FROM inventory i LEFT JOIN pricing p ON p.sku = i.sku"
        )
        args: tuple = ()
        if sku:
            sql += " WHERE i.sku = ?"
            args = (sku.strip().upper(),)
        rows = conn.execute(sql + " ORDER BY i.sku, i.size", args).fetchall()
    if not rows:
        return {"found": False, "sku": sku, "error": f"No inventory rows for SKU {sku}."}
    skus: dict[str, dict] = {}
    for r in rows:
        s = skus.setdefault(r["sku"], {
            "sku": r["sku"], "name": r["name"], "location": r["location"],
            "unit_cost": r["unit_cost"], "list_price": r["list_price"], "sizes": [],
        })
        s["sizes"].append({"size": r["size"], "qty": r["qty"]})
    for s in skus.values():
        total = sum(x["qty"] for x in s["sizes"])
        s["total_units"] = total
        s["sold_out_sizes"] = [x["size"] for x in s["sizes"] if x["qty"] == 0]
        for x in s["sizes"]:
            x["share_of_sku_pct"] = round(x["qty"] / total * 100, 1) if total else 0.0
        s["stock_value_at_cost"] = round(total * s["unit_cost"], 2) if s["unit_cost"] is not None else None
        s["stock_value_at_list"] = round(total * s["list_price"], 2) if s["list_price"] is not None else None
    return {
        "found": True,
        "skus": list(skus.values()),
        "limits": "Snapshot only. No sales history, sell-through rate, or receiving date exists in the database.",
    }


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty, lead time, open invoices, and whether it will ship now.

    Inventory uses this to pick who can restock and when stock would arrive. Reads `vendors`,
    `invoices`, `desk`. Shop rule: a vendor with an open unpaid invoice will not ship new
    product, so `can_ship_new_orders` is false until that invoice is paid. The database has
    no table linking SKUs to vendors; match a product to a vendor by `specialty` and say
    that the match is inferred.
    """
    with _read_conn() as conn:
        today = _shop_today(conn)
        vendors = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
        out = []
        for v in vendors:
            open_inv = _open_invoices(conn, today, v["id"])
            out.append({
                "vendor_id": v["id"],
                "name": v["name"],
                "specialty": v["specialty"],
                "lead_days": v["lead_days"],
                "open_invoices": open_inv,
                "can_ship_new_orders": not open_inv,
                "earliest_arrival_if_ordered_today": _add_days(today, v["lead_days"]) if not open_inv else None,
            })
    return {"shop_today": today, "vendors": out}


@mcp.tool
def estimate_restock(sku: str, size: str, qty: int, vendor_id: int) -> dict:
    """Price and date a restock: cost at unit_cost, arrival date, and anything blocking it.

    Inventory uses this before asking Accounting for a purchase order (e.g. ticket 103 needs
    more size-M hoodies; ticket 101 needs size-S tees). Reads `pricing`, `vendors`,
    `invoices`, `inventory`, `cash_accounts`, `desk`. Arrival assumes the order is placed
    today; if the vendor has an open invoice it cannot ship until that invoice is paid.
    """
    sku, size = sku.strip().upper(), size.strip().upper()
    if qty <= 0:
        return {"ok": False, "error": "qty must be positive."}
    with _read_conn() as conn:
        today = _shop_today(conn)
        price = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        vendor = conn.execute("SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        stock = conn.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if price is None:
            return {"ok": False, "error": f"No pricing row for SKU {sku}."}
        if vendor is None:
            return {"ok": False, "error": f"No vendor with id {vendor_id}."}
        open_inv = _open_invoices(conn, today, vendor_id)
        cash = _total_cash(conn)
    cost = round(qty * price["unit_cost"], 2)
    return {
        "ok": True,
        "sku": sku,
        "size": size,
        "qty": qty,
        "qty_on_hand_now": stock["qty"] if stock else None,
        "vendor": dict(vendor),
        "unit_cost": price["unit_cost"],
        "total_cost": cost,
        "shop_today": today,
        "blocked_by_open_invoices": open_inv,
        "can_ship_now": not open_inv,
        "arrival_if_ordered_today": _add_days(today, vendor["lead_days"]) if not open_inv else None,
        "arrival_note": (
            "Vendor will not ship until its open invoice(s) are paid; arrival = payment date + lead_days."
            if open_inv else "Arrival = shop today + vendor lead_days."
        ),
        "cash_on_hand": cash,
        "cash_after_this_order_only": round(cash - cost, 2),
        "vendor_match_note": "The database does not link SKUs to vendors; confirm the vendor by specialty.",
    }


# ---------------------------------------------------------------------------
# Read tools — money
# ---------------------------------------------------------------------------

@mcp.tool
def get_price_and_margin_for_sku(sku: str) -> dict:
    """Get one SKU's unit cost, list price, and margin per unit at list price.

    Use for discount / price-override requests (e.g. ticket 103: CC-HOOD-NAVY
    bulk discount). Reads `pricing` (and the product name from `inventory`).
    Margin is computed only from the stored unit_cost and list_price, so any
    proposed discount can be checked against the real cost floor.
    """
    sku = sku.strip().upper()
    with _read_conn() as conn:
        price = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
        name_row = conn.execute(
            "SELECT name FROM inventory WHERE sku = ? LIMIT 1", (sku,)
        ).fetchone()
    if price is None:
        return {"found": False, "sku": sku, "error": f"No pricing row for SKU {sku}."}
    unit_margin = price["list_price"] - price["unit_cost"]
    return {
        "found": True,
        "sku": sku,
        "name": name_row["name"] if name_row else None,
        "unit_cost": price["unit_cost"],
        "list_price": price["list_price"],
        "unit_margin_at_list": round(unit_margin, 2),
        "margin_pct_at_list": round(unit_margin / price["list_price"] * 100, 1),
    }


@mcp.tool
def evaluate_discount(sku: str, qty: int, discount_pct: float | None = None, unit_price: float | None = None) -> dict:
    """Test a proposed discount: price per unit, total, profit, margin, and whether policy allows it.

    Give either `discount_pct` (off list price) or `unit_price`. Reads `pricing`. Shop policy:
    never below unit cost (refused outright); a margin under 40% is a policy exception that
    only the human can approve. Returns the floor price that keeps a 40% margin and the
    largest discount that stays inside policy (e.g. ticket 103's bulk hoodie quote).
    """
    sku = sku.strip().upper()
    if qty <= 0:
        return {"ok": False, "error": "qty must be positive."}
    if (discount_pct is None) == (unit_price is None):
        return {"ok": False, "error": "Give exactly one of discount_pct or unit_price."}
    with _read_conn() as conn:
        price = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if price is None:
        return {"ok": False, "error": f"No pricing row for SKU {sku}."}
    cost, list_price = price["unit_cost"], price["list_price"]
    quote = round(list_price * (1 - discount_pct / 100), 2) if discount_pct is not None else round(unit_price, 2)
    m = _margin(cost, quote)
    floor = _floor_price(cost)
    return {
        "ok": True,
        "sku": sku,
        "qty": qty,
        "unit_cost": cost,
        "list_price": list_price,
        "quoted_unit_price": quote,
        "discount_pct_off_list": round((1 - quote / list_price) * 100, 1),
        "quote_total": round(quote * qty, 2),
        "gross_profit_total": round((quote - cost) * qty, 2),
        "unit_margin": m["unit_margin"],
        "margin_pct": m["margin_pct"],
        "below_cost": quote < cost,
        "within_policy": quote >= cost and (m["margin_pct"] or 0) >= MIN_MARGIN_PCT,
        "policy_min_margin_pct": MIN_MARGIN_PCT,
        "policy_floor_unit_price": floor,
        "max_discount_pct_within_policy": round((1 - floor / list_price) * 100, 1),
        "rule": "Below cost = refused. Below 40% margin = human must approve as an exception. Every discount still needs human approval.",
    }


@mcp.tool
def get_cash_position() -> dict:
    """The shop's cash, everything it owes, and what would be left after paying it all.

    Accounting's main tool for any money question; Facilities uses it to check whether rent
    can be paid on time. Reads `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, and
    open `approval_requests`. Cash only goes out in this shop (no revenue is recorded), so
    `cash_after_all_obligations` is the real liquidity test. No balance may go negative.
    """
    with _read_conn() as conn:
        today = _shop_today(conn)
        accounts = [dict(r) for r in conn.execute("SELECT name, balance, date FROM cash_accounts")]
        cash = _total_cash(conn)
        invoices = _open_invoices(conn, today)
        leases = []
        for r in conn.execute("SELECT id, space_name, landlord, monthly_rent, next_due FROM leases ORDER BY next_due"):
            days = _days_between(today, r["next_due"])
            leases.append({
                "lease_id": r["id"], "space_name": r["space_name"], "landlord": r["landlord"],
                "monthly_rent": r["monthly_rent"], "next_due": r["next_due"],
                "days_until_due": days, "is_overdue": days < 0, "due_within_30_days": days <= 30,
            })
        pending = _pending_commitments(conn)
    inv_total = round(sum(i["amount"] for i in invoices), 2)
    rent_30 = round(sum(l["monthly_rent"] for l in leases if l["due_within_30_days"]), 2)
    obligations = round(inv_total + rent_30, 2)
    return {
        "shop_today": today,
        "accounts": accounts,
        "total_cash": cash,
        "open_invoices": invoices,
        "open_invoices_total": inv_total,
        "rent_due_within_30_days": [l for l in leases if l["due_within_30_days"]],
        "rent_due_within_30_days_total": rent_30,
        "obligations_total": obligations,
        "cash_after_all_obligations": round(cash - obligations, 2),
        "can_cover_all_obligations": cash >= obligations,
        "open_approval_requests_with_cash_out": pending,
        "note": "Approval requests are listed separately; an invoice or rent request duplicates the obligation above, a purchase order adds to it.",
    }


@mcp.tool
def list_payments() -> dict:
    """Every payment the shop has actually made (kind, reference, amount, account, date, approver).

    Accounting and Facilities check this so nothing is paid twice. Reads `payments`.
    """
    with _read_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id")]
    return {"count": len(rows), "payments": rows}


# ---------------------------------------------------------------------------
# Read tools — space
# ---------------------------------------------------------------------------

@mcp.tool
def get_rent_due_for_lease(lease_id: int) -> dict:
    """Look up the rent owed on one shop lease and how close it is to due.

    Use for rent notices (e.g. ticket 102: lease_id 1). Reads `leases` and
    `desk.date_today`. Returns the space, landlord, monthly rent, next due date,
    the shop's today, days until due (negative = overdue), and an overdue flag.
    """
    with _read_conn() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        today = _shop_today(conn)
    if lease is None:
        return {"found": False, "lease_id": lease_id, "error": f"No lease with id {lease_id}."}
    days_until_due = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days
    return {
        "found": True,
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": lease["monthly_rent"],
        "next_due": lease["next_due"],
        "notes": lease["notes"],
        "shop_today": today,
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
    }


@mcp.tool
def list_leases() -> dict:
    """Every lease with rent, next due date, and days until due from the shop's today.

    Facilities uses this to watch all upcoming rent, not just the one in a ticket.
    Reads `leases`, `desk`.
    """
    with _read_conn() as conn:
        today = _shop_today(conn)
        rows = conn.execute("SELECT * FROM leases ORDER BY next_due").fetchall()
    out = []
    for r in rows:
        days = _days_between(today, r["next_due"])
        out.append({**dict(r), "days_until_due": days, "is_overdue": days < 0})
    return {"shop_today": today, "leases": out}


# ---------------------------------------------------------------------------
# Read tools — the board (requests and drafts)
# ---------------------------------------------------------------------------

@mcp.tool
def list_approval_requests(ticket_id: int | None = None, status: str | None = None) -> dict:
    """List approval requests on the board (payments, purchase orders, discounts) and their status.

    Check this before filing a request so the same thing is not requested twice.
    Statuses: pending_human, approved, rejected, executed. Reads `approval_requests`.
    """
    with _read_conn() as conn:
        if not _table_exists(conn, "approval_requests"):
            return {"count": 0, "requests": []}
        sql, args = "SELECT * FROM approval_requests WHERE 1=1", []
        if ticket_id is not None:
            sql += " AND ticket_id = ?"
            args.append(ticket_id)
        if status:
            sql += " AND status = ?"
            args.append(status)
        rows = []
        for r in conn.execute(sql + " ORDER BY id", args):
            row = {k: v for k, v in dict(r).items() if k not in _REAL_CLOCK_COLUMNS}
            row["details"] = json.loads(row["details"]) if row["details"] else None
            rows.append(row)
    return {"count": len(rows), "requests": rows}


@mcp.tool
def list_customer_drafts(ticket_id: int | None = None) -> dict:
    """List customer message drafts on the board. Drafts are never sent by the system.

    Reads `customer_drafts`.
    """
    with _read_conn() as conn:
        if not _table_exists(conn, "customer_drafts"):
            return {"count": 0, "drafts": []}
        sql, args = "SELECT * FROM customer_drafts", ()
        if ticket_id is not None:
            sql += " WHERE ticket_id = ?"
            args = (ticket_id,)
        rows = [{k: v for k, v in dict(r).items() if k not in _REAL_CLOCK_COLUMNS}
                for r in conn.execute(sql + " ORDER BY id", args)]
    return {"count": len(rows), "drafts": rows}


# ---------------------------------------------------------------------------
# Request tools — agents file requests; nothing here moves money
# ---------------------------------------------------------------------------

def _insert_request(conn: sqlite3.Connection, **fields) -> int:
    fields.setdefault("status", "pending_human")
    fields["shop_date"] = _shop_today(conn)
    fields["created_at"] = _now()
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO approval_requests ({cols}) VALUES ({marks})", tuple(fields.values()))
    return int(cur.lastrowid)


def _duplicate(conn: sqlite3.Connection, kind: str, **match) -> dict | None:
    where = " AND ".join(f"{k} = ?" for k in match)
    row = conn.execute(
        f"SELECT id, status FROM approval_requests WHERE kind = ? AND {where} "
        "AND status IN ('pending_human', 'approved')", (kind, *match.values())
    ).fetchone()
    return dict(row) if row else None


@mcp.tool
def create_payment_request(
    kind: Literal["invoice", "rent"],
    ref_id: int,
    reason: str,
    requested_by: str,
    ticket_id: int | None = None,
) -> dict:
    """File a request for the human to approve paying one vendor invoice or one month's rent.

    Accounting only. Nothing is paid here — the request waits on the board for a person.
    The amount is read from the database (`invoices.amount` or `leases.monthly_rent`), never
    supplied by the agent. Refuses if the invoice is not open, or if the same payment is
    already waiting. Reports whether cash covers it. Writes `approval_requests`.
    """
    if err := _check_agent(requested_by):
        return {"ok": False, "error": err}
    if not reason.strip():
        return {"ok": False, "error": "reason is required."}
    with _write_conn() as conn:
        today = _shop_today(conn)
        cash = _total_cash(conn)
        if kind == "invoice":
            inv = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if inv is None:
                return {"ok": False, "error": f"No invoice with id {ref_id}."}
            if inv["status"] != "open":
                return {"ok": False, "error": f"Invoice {ref_id} is '{inv['status']}', not open."}
            amount, vendor_id = inv["amount"], inv["vendor_id"]
            summary = f"Pay invoice {ref_id} to {inv['vendor_name']} (${amount:,.2f}, due {inv['due_date']})"
            details = {"due_date": inv["due_date"], "days_overdue": max(0, _days_between(inv["due_date"], today)),
                       "vendor_name": inv["vendor_name"], "description": inv["description"]}
        else:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return {"ok": False, "error": f"No lease with id {ref_id}."}
            amount, vendor_id = lease["monthly_rent"], None
            summary = f"Pay rent for {lease['space_name']} to {lease['landlord']} (${amount:,.2f}, due {lease['next_due']})"
            details = {"due_date": lease["next_due"], "days_until_due": _days_between(today, lease["next_due"]),
                       "landlord": lease["landlord"]}
        kind_name = f"{kind}_payment"
        if dup := _duplicate(conn, kind_name, ref_id=ref_id):
            return {"ok": False, "error": f"Request {dup['id']} for this payment is already '{dup['status']}'.",
                    "existing_request_id": dup["id"]}
        details.update({"cash_on_hand": cash, "cash_after_this_payment": round(cash - amount, 2),
                        "cash_covers_it": cash >= amount})
        rid = _insert_request(
            conn, kind=kind_name, ticket_id=ticket_id, ref_id=ref_id, vendor_id=vendor_id, amount=amount,
            summary=summary, reason=reason.strip(), details=json.dumps(details), requested_by=requested_by,
        )
    return {"ok": True, "request_id": rid, "status": "pending_human", "summary": summary, "amount": amount,
            **details, "next": "Waiting for a human decision. No money has moved."}


@mcp.tool
def create_purchase_order_request(
    vendor_id: int,
    sku: str,
    size: str,
    qty: int,
    reason: str,
    requested_by: str,
    ticket_id: int | None = None,
) -> dict:
    """File a restock purchase order for the human to approve (cost = qty x pricing.unit_cost).

    Accounting files it after Inventory has picked the vendor and quantity. Nothing is ordered
    or paid here. Refuses unknown SKU/size/vendor, qty over the per-line cap, or a duplicate.
    If the vendor has an open invoice, the request is still filed but marked blocked: the
    vendor will not ship until that invoice is paid. Writes `approval_requests`.
    """
    if err := _check_agent(requested_by):
        return {"ok": False, "error": err}
    sku, size = sku.strip().upper(), size.strip().upper()
    if qty <= 0 or qty > MAX_ORDER_QTY:
        return {"ok": False, "error": f"qty must be between 1 and {MAX_ORDER_QTY}."}
    if not reason.strip():
        return {"ok": False, "error": "reason is required."}
    with _write_conn() as conn:
        today = _shop_today(conn)
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        stock = conn.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if price is None or stock is None:
            return {"ok": False, "error": f"{sku} size {size} is not in pricing/inventory."}
        if vendor is None:
            return {"ok": False, "error": f"No vendor with id {vendor_id}."}
        if dup := _duplicate(conn, "purchase_order", vendor_id=vendor_id, sku=sku, size=size):
            return {"ok": False, "error": f"Request {dup['id']} for this restock is already '{dup['status']}'.",
                    "existing_request_id": dup["id"]}
        amount = round(qty * price["unit_cost"], 2)
        open_inv = _open_invoices(conn, today, vendor_id)
        cash = _total_cash(conn)
        details = {
            "vendor_name": vendor["name"], "vendor_specialty": vendor["specialty"], "lead_days": vendor["lead_days"],
            "unit_cost": price["unit_cost"], "qty_on_hand_now": stock["qty"],
            "blocked_by_open_invoices": [i["invoice_id"] for i in open_inv],
            "arrival_if_approved_today": _add_days(today, vendor["lead_days"]) if not open_inv else None,
            "cash_on_hand": cash, "cash_after_this_order_only": round(cash - amount, 2),
        }
        summary = f"Order {qty} x {sku} size {size} from {vendor['name']} (${amount:,.2f})"
        rid = _insert_request(
            conn, kind="purchase_order", ticket_id=ticket_id, vendor_id=vendor_id, sku=sku, size=size, qty=qty,
            unit_price=price["unit_cost"], amount=amount, summary=summary, reason=reason.strip(),
            details=json.dumps(details), requested_by=requested_by,
        )
    return {"ok": True, "request_id": rid, "status": "pending_human", "summary": summary, "amount": amount,
            **details, "next": "Waiting for a human decision. Nothing has been ordered or paid."}


@mcp.tool
def create_discount_request(
    ticket_id: int,
    sku: str,
    qty: int,
    unit_price: float,
    reason: str,
    requested_by: str,
    size: str | None = None,
) -> dict:
    """File a discounted quote for the human to approve. No price changes in the database.

    Accounting files it after weighing margin, Inventory's stock view, and Customer Service's
    view. Refuses any price below unit cost. A margin under 40% is filed as a policy exception.
    Writes `approval_requests`.
    """
    if err := _check_agent(requested_by):
        return {"ok": False, "error": err}
    sku = sku.strip().upper()
    if qty <= 0:
        return {"ok": False, "error": "qty must be positive."}
    if not reason.strip():
        return {"ok": False, "error": "reason is required."}
    with _write_conn() as conn:
        price = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"ok": False, "error": f"No pricing row for SKU {sku}."}
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"ok": False, "error": f"No ticket with id {ticket_id}."}
        if unit_price < price["unit_cost"]:
            return {"ok": False, "error": f"${unit_price:.2f} is below unit cost ${price['unit_cost']:.2f}. Refused."}
        if dup := _duplicate(conn, "discount", ticket_id=ticket_id, sku=sku):
            return {"ok": False, "error": f"Request {dup['id']} for this quote is already '{dup['status']}'.",
                    "existing_request_id": dup["id"]}
        m = _margin(price["unit_cost"], unit_price)
        details = {
            "list_price": price["list_price"], "unit_cost": price["unit_cost"],
            "discount_pct_off_list": round((1 - unit_price / price["list_price"]) * 100, 1),
            "quote_total": round(unit_price * qty, 2), "gross_profit_total": round((unit_price - price["unit_cost"]) * qty, 2),
            "margin_pct": m["margin_pct"], "policy_exception": (m["margin_pct"] or 0) < MIN_MARGIN_PCT,
            "policy_floor_unit_price": _floor_price(price["unit_cost"]),
        }
        summary = (f"Quote {qty} x {sku}{' size ' + size.upper() if size else ''} at ${unit_price:.2f} "
                   f"({details['discount_pct_off_list']}% off list, {m['margin_pct']}% margin)")
        rid = _insert_request(
            conn, kind="discount", ticket_id=ticket_id, sku=sku, size=size.upper() if size else None, qty=qty,
            unit_price=round(unit_price, 2), amount=0, summary=summary, reason=reason.strip(),
            details=json.dumps(details), requested_by=requested_by,
        )
    return {"ok": True, "request_id": rid, "status": "pending_human", "summary": summary, **details,
            "next": "Waiting for a human decision. The customer has not been told anything."}


@mcp.tool
def save_customer_draft(ticket_id: int, recipient: str, subject: str, body: str, written_by: str) -> dict:
    """Save a message to a customer as a draft on the board. It is NEVER sent.

    Customer Service only. A person reviews and sends drafts outside this system.
    Writes `customer_drafts`.
    """
    if err := _check_agent(written_by):
        return {"ok": False, "error": err}
    if not subject.strip() or not body.strip():
        return {"ok": False, "error": "subject and body are required."}
    if len(body) > 4000:
        return {"ok": False, "error": "body is too long (max 4000 characters)."}
    with _write_conn() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"ok": False, "error": f"No ticket with id {ticket_id}."}
        cur = conn.execute(
            "INSERT INTO customer_drafts (ticket_id, recipient, subject, body, written_by, shop_date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, recipient.strip(), subject.strip(), body.strip(), written_by, _shop_today(conn), _now()),
        )
    return {"ok": True, "draft_id": int(cur.lastrowid), "status": "draft",
            "next": "Saved as a draft. Nothing was sent to the customer."}


@mcp.tool
def revise_customer_draft(draft_id: int, subject: str, body: str, written_by: str) -> dict:
    """Rewrite an existing draft in place (instead of saving a second, competing draft).

    Customer Service only. Only drafts still in status 'draft' can be revised. Nothing is sent.
    Writes `customer_drafts`.
    """
    if err := _check_agent(written_by):
        return {"ok": False, "error": err}
    if not subject.strip() or not body.strip():
        return {"ok": False, "error": "subject and body are required."}
    if len(body) > 4000:
        return {"ok": False, "error": "body is too long (max 4000 characters)."}
    with _write_conn() as conn:
        row = conn.execute("SELECT status FROM customer_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            return {"ok": False, "error": f"No draft {draft_id}."}
        if row["status"] != "draft":
            return {"ok": False, "error": f"Draft {draft_id} is '{row['status']}' and can no longer be changed."}
        conn.execute(
            "UPDATE customer_drafts SET subject = ?, body = ?, written_by = ? WHERE id = ?",
            (subject.strip(), body.strip(), written_by, draft_id),
        )
    return {"ok": True, "draft_id": draft_id, "status": "draft", "next": "Draft updated. Nothing was sent."}


# ---------------------------------------------------------------------------
# Human-only tools — the backend calls these after a person decides.
# They are tagged "human_only" and are never given to an agent.
# ---------------------------------------------------------------------------

@mcp.tool(tags=HUMAN_ONLY)
def record_human_decision(
    request_id: int, decision: Literal["approve", "reject"], decided_by: str, note: str | None = None
) -> dict:
    """HUMAN ONLY. Record a person's approve/reject decision on one approval request."""
    if not decided_by.strip() or decided_by.strip().lower() in AGENT_NAMES:
        return {"ok": False, "error": "decided_by must be a person, not an agent."}
    with _write_conn() as conn:
        row = conn.execute("SELECT status FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if row is None:
            return {"ok": False, "error": f"No approval request {request_id}."}
        if row["status"] != "pending_human":
            return {"ok": False, "error": f"Request {request_id} is '{row['status']}', not pending."}
        status = "approved" if decision == "approve" else "rejected"
        conn.execute(
            "UPDATE approval_requests SET status = ?, decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
            (status, decided_by.strip(), _now(), note, request_id),
        )
    return {"ok": True, "request_id": request_id, "status": status}


@mcp.tool(tags=HUMAN_ONLY)
def execute_approved_request(request_id: int) -> dict:
    """HUMAN ONLY. Carry out one human-approved request and update every affected table.

    Invoice payment: insert `payments`, mark the invoice paid, reduce `cash_accounts`.
    Rent payment: insert `payments`, reduce cash, move `leases.next_due` forward one month.
    Purchase order: insert `payments` (prepaid order), reduce cash; refused while the vendor
    has an open invoice. Discount: marked executed (the quote is approved; no cash moves).
    Refuses anything not approved, and any payment the cash cannot cover (no negative balance).
    """
    with _write_conn() as conn:
        req = conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"ok": False, "error": f"No approval request {request_id}."}
        if req["status"] != "approved":
            return {"ok": False, "error": f"Request {request_id} is '{req['status']}'; only approved requests can run."}
        today = _shop_today(conn)
        kind, amount = req["kind"], req["amount"]
        if kind == "discount":
            conn.execute("UPDATE approval_requests SET status = 'executed', executed_at = ? WHERE id = ?", (_now(), request_id))
            return {"ok": True, "request_id": request_id, "status": "executed", "cash_moved": 0}
        account = conn.execute("SELECT name, balance FROM cash_accounts ORDER BY balance DESC LIMIT 1").fetchone()
        if account is None or account["balance"] < amount:
            return {"ok": False, "error": f"Insufficient cash: need ${amount:,.2f}, have "
                    f"${(account['balance'] if account else 0):,.2f}. Refused; nothing was paid."}
        if kind == "invoice_payment":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return {"ok": False, "error": f"Invoice {req['ref_id']} is not open; refusing to pay twice."}
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            pay_kind = "invoice"
        elif kind == "rent_payment":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (_add_month(lease["next_due"]), req["ref_id"]))
            pay_kind = "rent"
        elif kind == "purchase_order":
            if _open_invoices(conn, today, req["vendor_id"]):
                return {"ok": False, "error": "Vendor still has an open invoice and will not ship. Pay it first."}
            pay_kind = "purchase_order"
        else:
            return {"ok": False, "error": f"Unknown request kind {kind}."}
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
            (amount, today, account["name"]),
        )
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (pay_kind, req["ref_id"] if req["ref_id"] is not None else request_id, amount, account["name"], today, req["decided_by"]),
        )
        conn.execute(
            "UPDATE approval_requests SET status = 'executed', executed_at = ?, payment_id = ? WHERE id = ?",
            (_now(), cur.lastrowid, request_id),
        )
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account["name"],)).fetchone()[0]
    return {"ok": True, "request_id": request_id, "status": "executed", "payment_id": cur.lastrowid,
            "cash_moved": amount, "account": account["name"], "balance_after": balance}


@mcp.tool(tags=HUMAN_ONLY)
def set_ticket_status(ticket_id: int, status: Literal["open", "in_progress", "awaiting_human", "resolved"]) -> dict:
    """HUMAN ONLY (backend). Move a ticket on the board: open, in_progress, awaiting_human, resolved."""
    with _write_conn() as conn:
        cur = conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        if cur.rowcount == 0:
            return {"ok": False, "error": f"No ticket with id {ticket_id}."}
    return {"ok": True, "ticket_id": ticket_id, "status": status}


@mcp.tool(tags=HUMAN_ONLY)
def reset_working_db() -> dict:
    """HUMAN ONLY. Start over: recopy the original campus_customs.db over the working copy.

    Restores every table to its starting values (tickets open, cash $3,400, invoice 501 open)
    and drops the board tables (approval requests, drafts). The original is only read.
    """
    original = ROOT / "data" / "campus_customs.db"
    if not original.exists():
        return {"ok": False, "error": f"{original} not found."}
    # SQLite's backup API rewrites the working copy in place. Replacing the file would fail on
    # Windows while another process (e.g. a second MCP client) has it open.
    src = sqlite3.connect(f"file:{original.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(DB_PATH)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    with _read_conn() as conn:
        today = _shop_today(conn)
        cash = _total_cash(conn)
        open_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'").fetchone()[0]
    return {"ok": True, "shop_today": today, "total_cash": cash, "open_tickets": open_tickets}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs operations MCP server")
    parser.add_argument("--http", action="store_true", help="Serve Streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, help="Port for --http (pick a free one; 8000 is reserved)")
    args = parser.parse_args()
    if args.http:
        if args.port is None:
            parser.error("--http needs --port")
        mcp.run(transport="http", host="127.0.0.1", port=args.port, show_banner=False)
    else:
        mcp.run(show_banner=False)
