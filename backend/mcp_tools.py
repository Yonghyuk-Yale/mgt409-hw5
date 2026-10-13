"""The team's only route to shop facts: the campus-customs-ops MCP server.

There is no second tool layer. Agents get MCP tools through one connection, each agent sees
only the tools on its allowlist, and the human-only tools are never on any list.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset

HW_ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = HW_ROOT / "mcp_server" / "server.py"

# Tools a person must trigger (through the backend), never an agent.
HUMAN_ONLY_TOOLS = frozenset({
    "record_human_decision", "execute_approved_request", "set_ticket_status", "reset_working_db",
})

_BASE = ("get_shop_today", "get_ticket", "list_approval_requests")

# Which MCP tools each agent may call. Least privilege: only Accounting files money requests,
# only Customer Service writes to customers, Boss reads and decides.
AGENT_TOOLS: dict[str, frozenset[str]] = {
    "boss": frozenset({*_BASE, "list_open_tickets", "list_customer_drafts", "get_cash_position"}),
    "inventory": frozenset({
        *_BASE, "check_stock_for_size", "get_stock_overview", "list_vendors", "estimate_restock",
        "get_price_and_margin_for_sku", "evaluate_discount",
    }),
    "accounting": frozenset({
        *_BASE, "get_cash_position", "list_payments", "get_price_and_margin_for_sku", "evaluate_discount",
        "list_vendors", "estimate_restock", "get_rent_due_for_lease",
        "create_payment_request", "create_purchase_order_request", "create_discount_request",
    }),
    "facilities": frozenset({
        *_BASE, "get_rent_due_for_lease", "list_leases", "get_cash_position", "list_payments",
    }),
    "customer_service": frozenset({
        *_BASE, "get_customer_history", "check_stock_for_size", "get_stock_overview",
        "get_price_and_margin_for_sku", "list_customer_drafts", "save_customer_draft", "revise_customer_draft",
    }),
}

for _agent, _tools in AGENT_TOOLS.items():
    assert not (_tools & HUMAN_ONLY_TOOLS), f"{_agent} must not get human-only tools"


def _python() -> str:
    """The HW 5 .venv Python if present (uvicorn --reload on Windows runs its worker under the
    base interpreter, whose sys.executable lacks fastmcp), else the running interpreter."""
    envs = [HW_ROOT / ".venv", Path(sys.prefix)]
    if os.getenv("VIRTUAL_ENV"):
        envs.insert(0, Path(os.environ["VIRTUAL_ENV"]))
    for env in envs:
        for candidate in (env / "Scripts" / "python.exe", env / "bin" / "python"):
            if candidate.exists():
                return str(candidate)
    return sys.executable


def build_toolset() -> MCPToolset:
    """One stdio connection to mcp_server/server.py, launched with this .venv's Python."""
    client = Client(StdioTransport(command=_python(), args=[str(SERVER_SCRIPT)], cwd=str(HW_ROOT)))
    return MCPToolset(client, max_retries=2)


def toolset_for(agent: str, base: MCPToolset):
    """The same MCP connection, filtered to one agent's allowlist."""
    allowed = AGENT_TOOLS[agent]
    return base.filtered(lambda _ctx, tool_def: tool_def.name in allowed and tool_def.name not in HUMAN_ONLY_TOOLS)


async def call(base: MCPToolset, name: str, **args) -> dict:
    """Backend-side MCP call (not an agent): reading the ticket, listing requests, setting status."""
    result = await base.direct_call_tool(name, args)
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}
    return result
