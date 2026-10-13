"""Campus Customs operations API — FastAPI backend for the HW 5 dashboard.

Run from this folder:
    uvicorn main:app --reload --port 8000

Every shop fact goes through the campus-customs-ops MCP server (no direct database access here).
Agents only prepare work; the routes below marked HUMAN are the only way money moves.

Routes (all JSON):
    GET  /                              service info and route list
    GET  /api/health                    is the API up, is the LLM configured
    GET  /api/tickets                   the tickets, each open or resolved
    GET  /api/tickets/{id}              one ticket with its requests, drafts, latest run
    POST /api/tickets/{id}/run          start the agent team on a ticket (runs in the background;
                                        optional {"feedback": "..."} re-runs it after a Deny)
    POST /api/tickets/{id}/resolve      HUMAN: mark a ticket resolved
    GET  /api/runs                      recent team runs
    GET  /api/runs/{run_id}             one run's status and full result
    GET  /api/runs/{run_id}/trace       who called whom and which tools, per agent loop (from the audit trail)
    GET  /api/events                    live agent events (poll with ?after=<seq>)
    GET  /api/approvals                 approval requests on the board
    POST /api/approvals/{id}/approve    HUMAN: approve and execute (cash changes here)
    POST /api/approvals/{id}/reject     HUMAN: reject
    GET  /api/drafts                    customer message drafts (never sent by the system)
    GET  /api/cash                      checking balance from cash_accounts
    GET  /api/transactions              every payment made, newest first
    POST /api/reset                     HUMAN: reset the working database to its starting values
"""

from __future__ import annotations

import json
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import audit  # noqa: E402
import events  # noqa: E402
import team  # noqa: E402
from guardrails import TEAM_TOKEN_LIMIT  # noqa: E402
from llm import MODEL_NAME, TeamUnavailable, get_model  # noqa: E402
from models import AuditHumanEntry  # noqa: E402
from ops_loop import ops  # noqa: E402

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_runs()
    ops.start()
    events.publish("api_started", "Operations API is up.")
    yield
    ops.stop()


app = FastAPI(
    title="Campus Customs Operations API",
    description="Backend for the HW 5 multi-agent operations dashboard. Shop data comes only from the MCP server.",
    version="1.0.0",
    lifespan=lifespan,
)

# The dashboard (Vite dev server on any local port) calls these routes from the browser.
DASHBOARD_ORIGINS = ["http://localhost:5455", "http://127.0.0.1:5455"]  # Vite dev server (frontend/vite.config.ts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=DASHBOARD_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Team runs (in memory; the permanent record is output/audit_trail.json)
# ---------------------------------------------------------------------------

_runs: dict[str, dict] = {}
_runs_lock = threading.Lock()
_last_reset_at: str | None = None

# Finished runs are also saved as JSON so a restart (e.g. --reload after an edit) keeps the
# Boss reports on screen. The audit trail stays the permanent record of how each run went.
RUNS_DIR = Path(__file__).resolve().parent.parent / "output" / "team_runs"
RESET_MARK = RUNS_DIR / "_last_reset.json"


def _save_run(run: dict) -> None:
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        (RUNS_DIR / f"{run['run_id']}.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _load_runs() -> None:
    global _last_reset_at
    if not RUNS_DIR.exists():
        return
    if RESET_MARK.exists():
        _last_reset_at = json.loads(RESET_MARK.read_text(encoding="utf-8")).get("at")
    for f in RUNS_DIR.glob("*.json"):
        if f.name.startswith("_"):
            continue
        try:
            run = json.loads(f.read_text(encoding="utf-8"))
            _runs[run["run_id"]] = run
        except Exception:
            continue


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _audit_human(**fields) -> None:
    """Every human decision goes into the audit trail next to the agent loops it answers."""
    audit.append(AuditHumanEntry(at=datetime.now(timezone.utc), **fields))


def _active_run() -> dict | None:
    with _runs_lock:
        return next((r for r in _runs.values() if r["status"] == "running"), None)


def _run_summary(run: dict) -> dict:
    return {k: v for k, v in run.items() if k != "result"}


def _latest_run(ticket_id: int) -> dict | None:
    with _runs_lock:
        runs = [r for r in _runs.values() if r["ticket_id"] == ticket_id
                and (_last_reset_at is None or r["started_at"] >= _last_reset_at)]
    return max(runs, key=lambda r: r["started_at"]) if runs else None


async def _mcp(name: str, **args) -> dict:
    try:
        return await ops.call(name, **args)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MCP server error in {name}: {type(exc).__name__}: {exc}")


async def _ticket_or_404(ticket_id: int) -> dict:
    info = await _mcp("get_ticket", ticket_id=ticket_id)
    if not info.get("found"):
        raise HTTPException(status_code=404, detail=f"No ticket {ticket_id}.")
    return info


async def _request_or_404(request_id: int) -> dict:
    board = await _mcp("list_approval_requests")
    req = next((r for r in board.get("requests", []) if r["id"] == request_id), None)
    if req is None:
        raise HTTPException(status_code=404, detail=f"No approval request {request_id}.")
    return req


class RunRequest(BaseModel):
    feedback: str | None = Field(default=None, description="The owner's reasons after a Deny; added to the team's prompts.")


class Decision(BaseModel):
    decided_by: str = Field(default="Owner", description="The person deciding (not an agent name).")
    note: str | None = None


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> dict:
    return {
        "service": "Campus Customs Operations API",
        "docs": "/docs",
        "routes": [line.strip() for line in (__doc__ or "").split("Routes (all JSON):")[1].strip().splitlines()],
    }


@app.get("/api/health")
async def health() -> dict:
    try:
        get_model()
        llm_ok, llm_error = True, None
    except TeamUnavailable as exc:
        llm_ok, llm_error = False, str(exc)
    return {"ok": True, "model": MODEL_NAME, "llm_configured": llm_ok, "llm_error": llm_error,
            "team_running": _active_run() is not None}


# ---------------------------------------------------------------------------
# 1) Tickets
# ---------------------------------------------------------------------------

@app.get("/api/tickets")
async def list_tickets() -> dict:
    """Every ticket with open/resolved, plus what is waiting on it."""
    data = await _mcp("list_tickets")
    board = await _mcp("list_approval_requests")
    drafts = await _mcp("list_customer_drafts")
    tickets = []
    for t in data.get("tickets", []):
        reqs = [r for r in board.get("requests", []) if r["ticket_id"] == t["id"]]
        latest = _latest_run(t["id"])
        with _runs_lock:
            runs = [r for r in _runs.values() if r["ticket_id"] == t["id"]
                    and (_last_reset_at is None or r["started_at"] >= _last_reset_at)]
        tickets.append({
            **t,
            "state": "resolved" if t["is_resolved"] else "open",
            # what this ticket cost: cash actually paid for it, and tokens over every team run on it
            "cash_spent": round(sum(r["amount"] for r in reqs if r["status"] == "executed"), 2),
            "tokens_used": sum(r.get("tokens") or 0 for r in runs),
            "runs": len(runs),
            "pending_approvals": sum(r["status"] == "pending_human" for r in reqs),
            "drafts": sum(d["ticket_id"] == t["id"] for d in drafts.get("drafts", [])),
            "latest_run": _run_summary(latest) if latest else None,
        })
    return {"count": len(tickets), "tickets": tickets}


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int) -> dict:
    info = await _ticket_or_404(ticket_id)
    board = await _mcp("list_approval_requests", ticket_id=ticket_id)
    drafts = await _mcp("list_customer_drafts", ticket_id=ticket_id)
    latest = _latest_run(ticket_id)
    status = info["ticket"]["status"]
    return {
        **info,
        "state": "resolved" if status == "resolved" else "open",
        "approval_requests": board.get("requests", []),
        "customer_drafts": drafts.get("drafts", []),
        "latest_run": latest,
    }


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int) -> dict:
    """HUMAN: close a ticket once the owner is satisfied."""
    await _ticket_or_404(ticket_id)
    result = await _mcp("set_ticket_status", ticket_id=ticket_id, status="resolved")
    events.publish("ticket_resolved", f"Owner marked ticket {ticket_id} resolved.", ticket_id=ticket_id)
    _audit_human(action="resolve", ticket_id=ticket_id, summary=f"Ticket {ticket_id} marked resolved.")
    return result


# ---------------------------------------------------------------------------
# 2) Run the agent team
# ---------------------------------------------------------------------------

@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_team(ticket_id: int, body: RunRequest | None = None) -> dict:
    """Start the team on one ticket. Returns at once; follow /api/events and /api/runs/{run_id}.

    A re-run after a Deny passes the owner's feedback. Notes on this ticket's rejected requests are
    added automatically, so the team always sees why its earlier proposals were turned down.
    """
    try:
        get_model()
    except TeamUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    info = await _ticket_or_404(ticket_id)
    if info["ticket"]["status"] == "resolved":
        raise HTTPException(status_code=409, detail=f"Ticket {ticket_id} is already resolved.")
    if active := _active_run():
        raise HTTPException(status_code=409, detail=f"The team is already working on ticket {active['ticket_id']} "
                                                    f"(run {active['run_id']}). One ticket at a time.")
    board = await _mcp("list_approval_requests", ticket_id=ticket_id)
    rejected = [f"- Rejected request {r['id']} ({r['summary']}): {r.get('decision_note') or 'no reason given'}"
                for r in board.get("requests", []) if r["status"] == "rejected"]
    parts = [p for p in [(body.feedback or "").strip() if body else "", "\n".join(rejected)] if p]
    feedback = "\n".join(parts) or None
    run_id = team.new_run_id(ticket_id)
    record = {"run_id": run_id, "ticket_id": ticket_id, "status": "running", "started_at": _now(), "feedback": feedback,
              "finished_at": None, "stop_reason": None, "headline": None, "tokens": None,
              "token_limit": TEAM_TOKEN_LIMIT, "error": None, "result": None}
    with _runs_lock:
        _runs[run_id] = record

    def done(future) -> None:
        with _runs_lock:
            try:
                result = future.result()
                record.update(status="completed", stop_reason=result.stop_reason,
                              headline=result.final.headline if result.final else None,
                              tokens=result.usage.total_tokens, result=result.model_dump(mode="json"))
            except Exception as exc:
                record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                events.publish("run_failed", f"Run on ticket {ticket_id} failed: {type(exc).__name__}: {exc}",
                               team_run_id=run_id, ticket_id=ticket_id)
            record["finished_at"] = _now()
            _save_run(record)

    ops.submit(team.run_ticket(ticket_id, run_id, feedback)).add_done_callback(done)
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "running",
            "follow": {"events": f"/api/events?ticket_id={ticket_id}", "run": f"/api/runs/{run_id}"}}


@app.get("/api/runs")
async def list_runs() -> dict:
    with _runs_lock:
        runs = sorted((_run_summary(r) for r in _runs.values()), key=lambda r: r["started_at"], reverse=True)
    return {"count": len(runs), "runs": runs}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    with _runs_lock:
        run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No run {run_id} (runs are kept in memory until restart).")
    return run


@app.get("/api/runs/{run_id}/trace")
async def get_run_trace(run_id: str) -> dict:
    """Each agent loop of one run from the audit trail: agent, phase, who called it, tools used, tokens."""
    try:
        entries = json.loads(audit.AUDIT_FILE.read_text(encoding="utf-8")) if audit.AUDIT_FILE.exists() else []
    except Exception:
        entries = []
    loops = [
        {
            "loop_id": e["loop_id"], "agent": e["agent"], "phase": e["phase"], "called_by": e["called_by"],
            "depth": e["depth"], "tools": [c["tool"] for s in e["steps"] for c in s["tool_calls"]
                                          if c["tool"] != "final_result"],
            "stop_reason": e["stop_reason"], "tokens": e["usage_own"].get("total_tokens"),
            "started_at": e["started_at"],
        }
        for e in entries if e.get("entry_type") == "agent_loop" and e.get("team_run_id") == run_id
    ]
    if not loops:
        raise HTTPException(status_code=404, detail=f"No audit entries for run {run_id}.")
    loops.sort(key=lambda x: x["started_at"])
    return {"run_id": run_id, "loops": loops}


# ---------------------------------------------------------------------------
# 3) Live agent events
# ---------------------------------------------------------------------------

@app.get("/api/events")
async def get_events(
    after: int = Query(0, ge=0, description="Only events with seq greater than this (the last seq you saw)."),
    limit: int = Query(100, ge=1, le=500),
    ticket_id: int | None = None,
) -> dict:
    """What each agent is saying and which tools it is using, newest last. Poll every 1-2 s."""
    return events.recent(after=after, limit=limit, ticket_id=ticket_id)


# ---------------------------------------------------------------------------
# 4) Human approval — the only place money moves
# ---------------------------------------------------------------------------

@app.get("/api/approvals")
async def list_approvals(status: str | None = None, ticket_id: int | None = None) -> dict:
    args = {k: v for k, v in {"status": status, "ticket_id": ticket_id}.items() if v is not None}
    return await _mcp("list_approval_requests", **args)


@app.post("/api/approvals/{request_id}/approve")
async def approve(request_id: int, decision: Decision | None = None) -> dict:
    """HUMAN: approve one request and carry it out (payment / purchase order / discount).

    Records the decision, then executes it through the MCP server, which updates payments,
    invoices, cash_accounts, and leases. Refused (409) if cash is short, the vendor still has an
    unpaid invoice, or it was already done. An approved-but-not-executed request can be retried.
    """
    decision = decision or Decision()
    if decision.decided_by.strip().lower() in AGENT_NAMES:
        raise HTTPException(status_code=403, detail="Approvals come from a person, not an agent.")
    req = await _request_or_404(request_id)
    if req["status"] in ("executed", "rejected"):
        raise HTTPException(status_code=409, detail=f"Request {request_id} is already {req['status']}.")
    if req["status"] == "pending_human":
        recorded = await _mcp("record_human_decision", request_id=request_id, decision="approve",
                              decided_by=decision.decided_by, note=decision.note)
        if not recorded.get("ok"):
            raise HTTPException(status_code=409, detail=recorded.get("error"))
        events.publish("approved", f"{decision.decided_by} approved request {request_id}: {req['summary']}",
                       ticket_id=req["ticket_id"], request_id=request_id)
    executed = await _mcp("execute_approved_request", request_id=request_id)
    if not executed.get("ok"):
        _audit_human(action="execution_refused", ticket_id=req["ticket_id"], request_id=request_id,
                     decided_by=decision.decided_by, summary=req["summary"], amount=req["amount"], note=executed.get("error"))
        events.publish("execution_refused", f"Request {request_id} approved but not carried out: {executed.get('error')}",
                       ticket_id=req["ticket_id"], request_id=request_id)
        raise HTTPException(status_code=409, detail={"approved": True, "executed": False, "error": executed.get("error")})
    events.publish("executed", f"Request {request_id} carried out: {req['summary']}"
                   + (f" — ${executed['cash_moved']:,.2f} paid from {executed['account']}, balance "
                      f"${executed['balance_after']:,.2f}." if executed.get("cash_moved") else " (no cash moved)."),
                   ticket_id=req["ticket_id"], request_id=request_id)
    cash = await _mcp("get_cash_position")
    _audit_human(action="approve", ticket_id=req["ticket_id"], request_id=request_id, decided_by=decision.decided_by,
                 summary=req["summary"], amount=req["amount"], cash_moved=executed.get("cash_moved", 0),
                 balance_after=_cash_view(cash)["balance"], note=decision.note)
    return {"approved": True, "executed": True, "result": executed, "cash": _cash_view(cash)}


@app.post("/api/approvals/{request_id}/reject")
async def reject(request_id: int, decision: Decision | None = None) -> dict:
    """HUMAN: reject one request. Nothing is paid or ordered."""
    decision = decision or Decision()
    if decision.decided_by.strip().lower() in AGENT_NAMES:
        raise HTTPException(status_code=403, detail="Decisions come from a person, not an agent.")
    req = await _request_or_404(request_id)
    result = await _mcp("record_human_decision", request_id=request_id, decision="reject",
                        decided_by=decision.decided_by, note=decision.note)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("error"))
    _audit_human(action="reject", ticket_id=req["ticket_id"], request_id=request_id, decided_by=decision.decided_by,
                 summary=req["summary"], amount=req["amount"], note=decision.note)
    events.publish("rejected", f"{decision.decided_by} rejected request {request_id}: {req['summary']}",
                   ticket_id=req["ticket_id"], request_id=request_id)
    return result


@app.get("/api/drafts")
async def list_drafts(ticket_id: int | None = None) -> dict:
    args = {"ticket_id": ticket_id} if ticket_id is not None else {}
    return await _mcp("list_customer_drafts", **args)


# ---------------------------------------------------------------------------
# 5) Cash
# ---------------------------------------------------------------------------

def _cash_view(position: dict) -> dict:
    checking = next((a for a in position.get("accounts", []) if a["name"] == "checking"), None)
    return {
        "account": "checking",
        "balance": checking["balance"] if checking else None,
        "as_of": checking["date"] if checking else None,
        "shop_today": position.get("shop_today"),
        "total_cash": position.get("total_cash"),
        "obligations_total": position.get("obligations_total"),
        "cash_after_all_obligations": position.get("cash_after_all_obligations"),
    }


@app.get("/api/cash")
async def get_cash() -> dict:
    """The checking balance from cash_accounts, plus what the shop owes against it."""
    return _cash_view(await _mcp("get_cash_position"))


@app.get("/api/transactions")
async def list_transactions() -> dict:
    """Every payment actually made (newest first), with the approval request that caused it."""
    payments = await _mcp("list_payments")
    board = await _mcp("list_approval_requests")
    by_payment = {r["payment_id"]: r for r in board.get("requests", []) if r.get("payment_id")}
    items = []
    for pay in reversed(payments.get("payments", [])):
        req = by_payment.get(pay["id"])
        items.append({**pay, "request_id": req["id"] if req else None, "ticket_id": req["ticket_id"] if req else None,
                      "description": req["summary"] if req else f"{pay['kind']} {pay['ref_id']}"})
    cash = await _mcp("get_cash_position")
    return {"count": len(items), "total_paid": round(sum(i["amount"] for i in items), 2),
            "balance": _cash_view(cash)["balance"], "transactions": items}


# ---------------------------------------------------------------------------
# 6) Start over
# ---------------------------------------------------------------------------

@app.post("/api/reset")
async def reset() -> dict:
    """HUMAN: recopy data/campus_customs.db over data/campus_customs_new.db (all starting values)."""
    global _last_reset_at
    if active := _active_run():
        raise HTTPException(status_code=409, detail=f"The team is working on ticket {active['ticket_id']}; "
                                                    "wait for it to finish before resetting.")
    result = await _mcp("reset_working_db")
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    _last_reset_at = _now()
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        RESET_MARK.write_text(json.dumps({"at": _last_reset_at}), encoding="utf-8")
    except Exception:
        pass
    _audit_human(action="reset", summary=f"Working database reset to starting values (cash ${result['total_cash']:,.2f}).",
                 balance_after=result["total_cash"])
    events.publish("reset", f"Database reset: tickets open, cash ${result['total_cash']:,.2f}, "
                            f"shop today {result['shop_today']}.")
    return result
