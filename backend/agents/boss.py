"""Boss — reads the ticket, plans who works it and in what order, makes the final call for the human.

Boss runs twice per ticket: first to plan (TicketPlan), last to report (FinalReport).
Boss never files money requests or writes to customers; it reads, decides, and owns safety.
"""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext

import mcp_tools
from agents.base import AgentSpec, TeamDeps, register
from models import FinalReport, TicketPlan


async def check_plan(ctx: RunContext[TeamDeps], output):
    if not isinstance(output, TicketPlan):
        return output
    orders = [s.order for s in output.steps]
    if sorted(orders) != list(range(1, len(orders) + 1)):
        raise ModelRetry("Step orders must be 1, 2, 3 ... with no gaps or repeats.")
    if output.ticket_id != ctx.deps.team.ticket_id:
        raise ModelRetry(f"This plan is for ticket {ctx.deps.team.ticket_id}.")
    return output


async def unrequested_obligations(team) -> list[str]:
    """Rent or a vendor invoice linked to this ticket that is still owed but not waiting for the owner.

    Obligations never end at a denial: if one is unpaid and no request is pending, it must go back
    to the owner as a new request (the owner can deny it again).
    """
    ticket = team.ticket
    board = await mcp_tools.call(team.mcp, "list_approval_requests")
    live = [r for r in board.get("requests", []) if r["status"] in ("pending_human", "approved")]
    missing: list[str] = []
    if ticket.get("lease_id") is not None:
        lease = await mcp_tools.call(team.mcp, "get_rent_due_for_lease", lease_id=ticket["lease_id"])
        due_soon = lease.get("found") and lease["days_until_due"] <= 7
        if due_soon and not any(r["kind"] == "rent_payment" and r["ref_id"] == ticket["lease_id"] for r in live):
            missing.append(f"rent for lease {ticket['lease_id']} (${lease['monthly_rent']:,.2f}, due {lease['next_due']})")
    if ticket.get("invoice_id") is not None:
        info = await mcp_tools.call(team.mcp, "get_ticket", ticket_id=team.ticket_id)
        inv = (info.get("linked") or {}).get("invoice") or {}
        still_open = "days_overdue" in inv or inv.get("status") == "open"
        if still_open and not any(r["kind"] == "invoice_payment" and r["ref_id"] == ticket["invoice_id"] for r in live):
            missing.append(f"invoice {ticket['invoice_id']} (${inv.get('amount', 0):,.2f})")
    return missing


async def check_final(ctx: RunContext[TeamDeps], output):
    """Nothing about money or customers may be hidden from the human, and ids must be real."""
    if not isinstance(output, FinalReport):
        return output
    team = ctx.deps.team
    if output.ticket_id != team.ticket_id:
        raise ModelRetry(f"This report is for ticket {team.ticket_id}.")
    if missing := await unrequested_obligations(team):
        raise ModelRetry(
            f"Required payment(s) still owed with no request waiting for the owner: {'; '.join(missing)}. "
            "A denial does not cancel an obligation. Ask Accounting (ask_teammate) to file a new payment request "
            "that answers the owner's feedback and states the due date and the cost of not paying, then list it "
            "in human_actions."
        )
    board = await mcp_tools.call(team.mcp, "list_approval_requests", ticket_id=team.ticket_id)
    waiting = {r["id"] for r in board.get("requests", []) if r["status"] == "pending_human"}
    known = {r["id"] for r in board.get("requests", [])}
    listed = {a.request_id for a in output.human_actions if a.request_id is not None}
    if unknown := listed - known:
        raise ModelRetry(f"request_id {sorted(unknown)} is not on the board for this ticket. Use only real ids.")
    if missing := waiting - listed:
        raise ModelRetry(
            f"Approval request(s) {sorted(missing)} are waiting for the human but are not in human_actions. "
            "Every pending request must be shown to the human."
        )
    drafts = await mcp_tools.call(team.mcp, "list_customer_drafts", ticket_id=team.ticket_id)
    draft_ids = {d["id"] for d in drafts.get("drafts", [])}
    listed_drafts = {a.draft_id for a in output.human_actions if a.draft_id is not None}
    if unknown := listed_drafts - draft_ids:
        raise ModelRetry(f"draft_id {sorted(unknown)} does not exist for this ticket.")
    if missing := draft_ids - listed_drafts:
        raise ModelRetry(f"Customer draft(s) {sorted(missing)} must be listed for human review.")
    if output.agrees_with_customer_service is False and not (output.override_reason or "").strip():
        raise ModelRetry("You did not follow Customer Service's stance: give override_reason for the human.")
    return output


SPEC = register(AgentSpec(
    name="boss",
    title="Boss",
    prompt_file="boss.md",
    output_type=TicketPlan,
    validators=(check_plan, check_final),
))
