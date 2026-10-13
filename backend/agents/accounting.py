"""Accounting — cash, invoices, margins, liquidity; the only agent that files money requests for human approval."""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext

import mcp_tools
from agents.base import AgentSpec, TeamDeps, register, request_ids_exist
from models import AccountingReport


async def cash_matches_db(ctx: RunContext[TeamDeps], output: AccountingReport) -> AccountingReport:
    """Accounting's cash figure must be the database's, not a guess."""
    position = await mcp_tools.call(ctx.deps.team.mcp, "get_cash_position")
    actual = position.get("total_cash")
    if actual is not None and abs(output.cash_on_hand - actual) > 0.01:
        raise ModelRetry(f"cash_on_hand must be the database value from get_cash_position (${actual:,.2f}).")
    return output


SPEC = register(AgentSpec(
    name="accounting",
    title="Accounting",
    prompt_file="accounting.md",
    output_type=AccountingReport,
    validators=(request_ids_exist, cash_matches_db),
))
