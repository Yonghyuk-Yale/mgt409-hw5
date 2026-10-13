"""Customer Service — the customer's voice on the team: drafts (never sends) messages, reviews every
customer-facing plan, and carries customer feedback back to the team and the human.

Its weight is built into the workflow, not just the prompt:
- it must review every customer-facing ticket before Boss reports (team.py),
- its review goes to the human unedited, next to Boss's report (TeamResult.customer_service_review),
- Boss must give a reason whenever it does not follow Customer Service's stance (boss.check_final).
"""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext

import mcp_tools
from agents.base import AgentSpec, TeamDeps, register, request_ids_exist
from models import CustomerServiceReport


async def drafts_exist(ctx: RunContext[TeamDeps], output: CustomerServiceReport) -> CustomerServiceReport:
    if not output.draft_ids:
        return output
    drafts = await mcp_tools.call(ctx.deps.team.mcp, "list_customer_drafts", ticket_id=ctx.deps.team.ticket_id)
    known = {d["id"] for d in drafts.get("drafts", [])}
    if unknown := set(output.draft_ids) - known:
        raise ModelRetry(f"draft_ids {sorted(unknown)} were not saved for this ticket. List only ids save_customer_draft returned.")
    return output


SPEC = register(AgentSpec(
    name="customer_service",
    title="Customer Service",
    prompt_file="customer_service.md",
    output_type=CustomerServiceReport,
    validators=(request_ids_exist, drafts_exist),
))
