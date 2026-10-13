"""How the team works one ticket.

    1. Boss plans        Boss reads the ticket (and what it links to) and returns a TicketPlan:
                         which specialists, in what order, what each hands to the next.
    2. Specialists work  Each plan step runs in order and sees every earlier report. Any
                         specialist may ask any other specialist mid-task (ask_teammate), so
                         work ping-pongs: e.g. Inventory asks Accounting whether a restock is
                         affordable; Facilities asks Accounting to file the rent request.
    3. Customer review   On customer-facing tickets Customer Service always reviews the plan and
                         the findings from the customer's side and saves any message as a draft.
    4. Boss reports      Boss weighs everything, may ask a specialist a last question, and
                         returns a FinalReport for the human. Every pending approval request
                         and draft must appear in it (checked in code).

The backend — not an agent — marks the ticket in_progress at the start and awaiting_human at the
end. No agent can approve, pay, or close anything.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from uuid import uuid4

import audit
import events
import mcp_tools
from agents import run_loop
from agents.base import TeamState
from guardrails import (
    CUSTOMER_TICKET_TYPES, TEAM_TOKEN_LIMIT, TICKET_TIMEOUT_SECONDS, BudgetExhausted, mask, name_variants,
)
from llm import MODEL_NAME
from models import (
    AuditRunSummary, CustomerServiceReport, FinalReport, HumanAction, PlanStep, StepResult, TeamResult,
    TeamUsage, TicketPlan,
)


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)


# Used only if Boss cannot produce a plan, so the ticket is still looked at by the right people.
FALLBACK_STEPS: dict[str, list[tuple[str, str, str]]] = {
    "customer_order": [
        ("inventory", "Check stock for the ordered SKU/size, substitutes, and restock options with arrival dates.",
         "InventoryReport with stock, restock options, blockers."),
        ("accounting", "Check cash, any invoice blocking the vendor, and file the payment/purchase-order requests needed.",
         "AccountingReport with cash plan and request ids."),
    ],
    "rent_notice": [
        ("facilities", "Check the lease, rent, due date, and whether it can be paid on time.", "FacilitiesReport."),
        ("accounting", "Confirm cash after all obligations and file the rent payment request.", "AccountingReport with request id."),
    ],
    "price_override": [
        ("inventory", "Check stock for the requested SKU/size/qty and give a stock-based view on the discount.", "InventoryReport."),
        ("accounting", "Test discount levels against margin policy and cash; file the discount request.", "AccountingReport."),
    ],
}


def fallback_plan(ticket: dict) -> TicketPlan:
    steps = FALLBACK_STEPS.get(ticket["type"], FALLBACK_STEPS["customer_order"])
    return TicketPlan(
        ticket_id=ticket["id"],
        understanding=f"Fallback plan for a {ticket['type']} ticket (Boss could not plan).",
        customer_facing=ticket["type"] in CUSTOMER_TICKET_TYPES,
        steps=[PlanStep(order=i + 1, agent=a, task=t, deliverable=d) for i, (a, t, d) in enumerate(steps)],
        success_criteria=["The human gets every fact and request needed to decide."],
        risks_to_watch=["Boss planning failed; check the audit trail."],
    )


async def fallback_final(team: TeamState, reason: str, steps: list[StepResult]) -> FinalReport:
    """Built from the board, not by a model: used when Boss cannot write the final report."""
    board = await mcp_tools.call(team.mcp, "list_approval_requests", ticket_id=team.ticket_id)
    drafts = await mcp_tools.call(team.mcp, "list_customer_drafts", ticket_id=team.ticket_id)
    kind_map = {"invoice_payment": "approve_payment", "rent_payment": "approve_payment",
                "purchase_order": "approve_purchase_order", "discount": "approve_discount"}
    actions = [
        HumanAction(kind=kind_map.get(r["kind"], "decide"), request_id=r["id"], what=r["summary"],
                    amount=r["amount"] or None, why=r["reason"], urgency="today")
        for r in board.get("requests", []) if r["status"] == "pending_human"
    ] + [
        HumanAction(kind="review_customer_draft", draft_id=d["id"], what=f"Draft to customer: {d['subject']}",
                    why="Written by Customer Service; never sent automatically.", urgency="today")
        for d in drafts.get("drafts", [])
    ]
    return FinalReport(
        ticket_id=team.ticket_id,
        headline=f"The team stopped before Boss could report ({reason}). Review the items below.",
        recommended_outcome="No recommendation: Boss did not finish. Use the specialist reports and the audit trail.",
        human_actions=actions,
        how_the_team_worked=[f"{s.order}. {s.agent}: {'done' if s.report else 'failed'}" for s in steps],
        money_summary="See the approval requests; nothing has been paid.",
        risks=[reason],
        data_gaps=[],
    )


def feedback_block(feedback: str | None) -> str:
    """The owner's reasons for rejecting earlier proposals on this ticket (a re-run)."""
    if not feedback:
        return ""
    return (
        "OWNER FEEDBACK — this is a re-run. The owner rejected earlier proposals on this ticket and said:\n"
        f"{feedback}\n"
        "Answer this feedback. If the owner asked for something the data rules out, say so plainly and why.\n"
        "A rejected request is closed, but an OBLIGATION does not go away: rent on a lease and an open vendor "
        "invoice must still be paid. If the feedback does not remove the obligation, Accounting files a NEW "
        "request for it (explaining what changed or why the owner's alternative is not possible, the due date, and "
        "what happens if it is not paid), so the decision goes back to the owner. Never end with a required "
        "payment simply left unpaid. Discretionary items (a discount, a new purchase order) can be dropped or "
        "replaced.\n\n"
    )


def plan_prompt(ticket_info: dict, feedback: str | None = None) -> str:
    return (
        f"PHASE: PLAN. A ticket needs the team.\n\n{feedback_block(feedback)}"
        f"Ticket and linked rows (from get_ticket):\n{_dump(ticket_info)}\n\n"
        "Plan who works it. Specialists: inventory, accounting, facilities, customer_service. "
        "1-4 steps, in order, each with a precise task and deliverable. Do not plan Customer Service's "
        "customer review: on customer-facing tickets it runs automatically after the steps. "
        "Do not plan a step for yourself."
    )


def step_prompt(ticket_info: dict, plan: TicketPlan, step: PlanStep, done: list[StepResult],
                feedback: str | None = None) -> str:
    earlier = [{"order": s.order, "agent": s.agent, "report": s.report, "error": s.error} for s in done]
    nxt = f" Your deliverable goes next to {step.hand_off_to}." if step.hand_off_to else " Your deliverable goes to Boss."
    return (
        f"PHASE: WORK. Ticket {plan.ticket_id}. You are step {step.order} of {len(plan.steps)} in Boss's plan.\n\n"
        f"YOUR TASK: {step.task}\nDELIVERABLE: {step.deliverable}.{nxt}\n\n{feedback_block(feedback)}"
        f"Boss's understanding: {plan.understanding}\n\n"
        f"Ticket and linked rows:\n{_dump(ticket_info)}\n\n"
        f"Earlier steps' reports:\n{_dump(earlier) if earlier else '(none - you are first)'}\n\n"
        "Verify numbers with your MCP tools; do not copy them blindly. Ask a teammate only if you need "
        "something you cannot get yourself."
    )


def review_prompt(ticket_info: dict, plan: TicketPlan, done: list[StepResult], feedback: str | None = None) -> str:
    reports = [{"order": s.order, "agent": s.agent, "report": s.report, "error": s.error} for s in done]
    return (
        f"PHASE: CUSTOMER REVIEW. Ticket {plan.ticket_id} is customer-facing. The specialists are done.\n\n"
        f"{feedback_block(feedback)}"
        f"Ticket and linked rows:\n{_dump(ticket_info)}\n\nBoss's plan:\n{plan.model_dump_json(indent=1)}\n\n"
        f"Specialist reports:\n{_dump(reports)}\n\n"
        "Review the team's direction from the customer's side, give your stance, and save the customer "
        "message as a draft (save_customer_draft) if the customer should hear from us. Do not promise "
        "anything that still needs human approval; say it is being confirmed."
    )


def final_prompt(ticket_info: dict, plan: TicketPlan, done: list[StepResult],
                 review: CustomerServiceReport | None, board: dict, drafts: dict, notes: list[str],
                 feedback: str | None = None) -> str:
    reports = [{"order": s.order, "agent": s.agent, "report": s.report, "error": s.error} for s in done]
    review_text = review.model_dump_json(indent=1) if review else "(no Customer Service review on this ticket)"
    return (
        f"PHASE: FINAL REPORT. Ticket {plan.ticket_id}.\n\n{feedback_block(feedback)}"
        f"Ticket and linked rows:\n{_dump(ticket_info)}\n\n"
        f"Your plan:\n{plan.model_dump_json(indent=1)}\n\nSpecialist reports:\n{_dump(reports)}\n\n"
        f"CUSTOMER SERVICE REVIEW (weigh this heavily; it goes to the human unedited):\n{review_text}\n\n"
        f"Approval requests on the board for this ticket:\n{_dump(board.get('requests', []))}\n\n"
        f"Customer drafts for this ticket:\n{_dump(drafts.get('drafts', []))}\n\n"
        f"Team notes: {_dump(notes) if notes else 'none'}\n\n"
        "Write the final report for the human. List every pending approval request and every draft in "
        "human_actions. If you do not follow Customer Service's stance, set agrees_with_customer_service "
        "false and explain in override_reason."
    )


async def _work(team: TeamState, ticket_info: dict, steps: list[StepResult], notes: list[str],
                feedback: str | None = None) -> dict:
    ticket = ticket_info["ticket"]
    state: dict = {"plan": None, "review": None, "final": None, "stop_reason": "completed"}

    # 1. Boss plans
    try:
        state["plan"] = await run_loop("boss", plan_prompt(ticket_info, feedback), team, phase="plan", called_by="team")
    except Exception as exc:
        notes.append(f"Boss could not plan ({type(exc).__name__}); fallback plan used.")
        state["plan"] = fallback_plan(ticket)
    plan: TicketPlan = state["plan"]

    # 2. Specialists work the plan, in order
    for step in sorted(plan.steps, key=lambda s: s.order):
        try:
            report = await run_loop(step.agent, step_prompt(ticket_info, plan, step, steps, feedback), team,
                                    phase="step", called_by="boss")
            steps.append(StepResult(order=step.order, agent=step.agent, task=step.task,
                                    report=report.model_dump(mode="json")))
        except BudgetExhausted as exc:
            notes.append(f"Stopped before step {step.order} ({step.agent}): {exc}.")
            state["stop_reason"] = "budget_exhausted"
            break
        except Exception as exc:
            steps.append(StepResult(order=step.order, agent=step.agent, task=step.task,
                                    error=f"{type(exc).__name__}: {str(exc)[:200]}"))
            if "UsageLimitExceeded" in type(exc).__name__:
                notes.append("Team token budget reached during the specialist steps.")
                state["stop_reason"] = "budget_exhausted"
                break

    # 3. Customer Service reviews every customer-facing ticket
    if ticket["type"] in CUSTOMER_TICKET_TYPES or plan.customer_facing:
        try:
            state["review"] = await run_loop("customer_service", review_prompt(ticket_info, plan, steps, feedback), team,
                                             phase="customer_review", called_by="team")
        except Exception as exc:
            notes.append(f"Customer Service review did not finish ({type(exc).__name__}). "
                         "The human must check the customer side directly.")

    # 4. Boss writes the final report (may spend the reserved budget)
    board = await mcp_tools.call(team.mcp, "list_approval_requests", ticket_id=team.ticket_id)
    drafts = await mcp_tools.call(team.mcp, "list_customer_drafts", ticket_id=team.ticket_id)
    try:
        state["final"] = await run_loop(
            "boss", final_prompt(ticket_info, plan, steps, state["review"], board, drafts, notes, feedback), team,
            phase="final", called_by="team", output_type=FinalReport,
        )
    except Exception as exc:
        notes.append(f"Boss could not write the final report ({type(exc).__name__}).")
        state["final"] = await fallback_final(team, f"Boss final report failed: {type(exc).__name__}", steps)
        if state["stop_reason"] == "completed":
            state["stop_reason"] = "final_report_fallback"
    return state


async def _shop_words(toolset) -> set[str]:
    """Words from the shop's own product, vendor, and space names (never masked as customer names)."""
    stock = await mcp_tools.call(toolset, "get_stock_overview")
    vendors = await mcp_tools.call(toolset, "list_vendors")
    leases = await mcp_tools.call(toolset, "list_leases")
    text = " ".join(
        [s["name"] for s in stock.get("skus", [])]
        + [v["name"] for v in vendors.get("vendors", [])]
        + [f"{l['space_name']} {l['landlord']}" for l in leases.get("leases", [])]
    )
    return {w.lower() for w in text.split()} | {"club", "team", "the", "and", "group", "society"}


def new_run_id(ticket_id: int) -> str:
    return f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-t{ticket_id}-{uuid4().hex[:6]}"


async def run_ticket(ticket_id: int, team_run_id: str | None = None, feedback: str | None = None) -> TeamResult:
    """Run the whole team on one ticket and return what the human needs to decide.

    `feedback` is the owner's reasons for rejecting earlier proposals (a re-run after Deny).
    """
    started_at, t0 = datetime.now(timezone.utc), time.perf_counter()
    team_run_id = team_run_id or new_run_id(ticket_id)
    toolset = mcp_tools.build_toolset()
    async with toolset:
        ticket_info = await mcp_tools.call(toolset, "get_ticket", ticket_id=ticket_id)
        if not ticket_info.get("found"):
            raise ValueError(f"No ticket {ticket_id}.")
        ticket = ticket_info["ticket"]
        # Customers are private: no customer's name reaches the audit trail. Mask every customer on
        # the board, not just this ticket's (Boss's list_open_tickets shows the others too).
        board_tickets = (await mcp_tools.call(toolset, "list_open_tickets")).get("tickets", [])
        customers = sorted({
            t["requester"] for t in [*board_tickets, ticket]
            if t["type"] in CUSTOMER_TICKET_TYPES and t.get("requester")
        })
        names = name_variants(customers, await _shop_words(toolset))
        team = TeamState(team_run_id=team_run_id, ticket_id=ticket_id, ticket=ticket, mcp=toolset, mask_names=names)
        await mcp_tools.call(toolset, "set_ticket_status", ticket_id=ticket_id, status="in_progress")
        events.publish("run_started", f"Team starts on ticket {ticket_id}: {ticket['subject']}."
                       + (" Re-run with the owner's feedback." if feedback else ""),
                       team_run_id=team_run_id, ticket_id=ticket_id, feedback=feedback)

        steps: list[StepResult] = []
        notes: list[str] = []
        try:
            state = await asyncio.wait_for(_work(team, ticket_info, steps, notes, feedback), TICKET_TIMEOUT_SECONDS)
        except TimeoutError:
            notes.append(f"Ticket run passed {TICKET_TIMEOUT_SECONDS}s and was stopped.")
            state = {"plan": None, "review": None, "stop_reason": "timeout",
                     "final": await fallback_final(team, "time limit reached", steps)}

        status = await mcp_tools.call(toolset, "set_ticket_status", ticket_id=ticket_id, status="awaiting_human")
        board = await mcp_tools.call(toolset, "list_approval_requests", ticket_id=ticket_id)
        drafts = await mcp_tools.call(toolset, "list_customer_drafts", ticket_id=ticket_id)

    u = team.usage
    usage = TeamUsage(
        agent_loops=team.loops_started, model_requests=u.requests, tool_calls=u.tool_calls,
        input_tokens=u.input_tokens, output_tokens=u.output_tokens, total_tokens=u.total_tokens,
        token_limit=TEAM_TOKEN_LIMIT,
    )
    finished_at = datetime.now(timezone.utc)
    final: FinalReport | None = state["final"]
    result = TeamResult(
        team_run_id=team_run_id, ticket_id=ticket_id, started_at=started_at, finished_at=finished_at,
        plan=state["plan"], steps=steps, customer_service_review=state["review"], final=final,
        approval_requests=board.get("requests", []), customer_drafts=drafts.get("drafts", []),
        ticket_status=status.get("status"), usage=usage, stop_reason=state["stop_reason"],
        errors=notes + team.errors, feedback=feedback,
    )
    audit.append(AuditRunSummary(
        team_run_id=team_run_id, ticket_id=ticket_id, started_at=started_at, finished_at=finished_at,
        duration_seconds=round(time.perf_counter() - t0, 2), model=MODEL_NAME, loops=team.loop_ids,
        usage=usage, stop_reason=state["stop_reason"],
        headline=mask(final.headline, team.mask_names) if final else None,
        approval_request_ids=[r["id"] for r in result.approval_requests],
        draft_ids=[d["id"] for d in result.customer_drafts],
        ticket_status=result.ticket_status, errors=[mask(e, team.mask_names) for e in result.errors],
    ))
    events.publish(
        "run_finished",
        f"Ticket {ticket_id} is waiting for the human: {mask(final.headline, team.mask_names) if final else 'no report'}",
        team_run_id=team_run_id, ticket_id=ticket_id, stop_reason=state["stop_reason"],
        tokens=usage.total_tokens, approval_request_ids=[r["id"] for r in result.approval_requests],
        draft_ids=[d["id"] for d in result.customer_drafts],
    )
    return result
