"""Data types for the Campus Customs agent team.

Three groups:
- agent outputs   — what each agent must hand back (PydanticAI validates them, so an agent
                    cannot return a vague paragraph instead of the fields the next agent needs)
- team result     — what one ticket run produces for the human
- audit entries   — one record per agent loop, appended to output/audit_trail.json
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
SpecialistName = Literal["inventory", "accounting", "facilities", "customer_service"]
Confidence = Literal["high", "medium", "low"]


# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------

class Fact(BaseModel):
    """One fact an agent relies on, tied to the MCP tool that returned it."""

    statement: str = Field(description="The fact, with its number/date, e.g. 'Size S on hand: 0'.")
    source_tool: str = Field(description="The MCP tool that returned it, e.g. 'check_stock_for_size'.")


class SpecialistReport(BaseModel):
    """Fields every specialist returns, whether working a plan step or answering a teammate."""

    summary: str = Field(description="Two to four sentences: what you found and what you recommend.")
    facts: list[Fact] = Field(description="Every number or date you rely on, each tied to an MCP tool.")
    recommendations: list[str] = Field(description="Concrete next actions, in priority order.")
    approval_request_ids: list[int] = Field(
        default_factory=list, description="Ids of approval requests you filed or found for this ticket."
    )
    for_boss: list[str] = Field(
        default_factory=list,
        description="Decisions or trade-offs only Boss/the human can make (conflicts, exceptions, escalations).",
    )
    data_gaps: list[str] = Field(
        default_factory=list, description="What you could not know because the database does not hold it."
    )
    confidence: Confidence


# ---------------------------------------------------------------------------
# Boss
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    order: int = Field(ge=1, description="Run order, starting at 1.")
    agent: SpecialistName
    task: str = Field(description="Exactly what this agent must find out or do.")
    deliverable: str = Field(description="What it must hand back (the fields the next agent needs).")
    hand_off_to: SpecialistName | None = Field(
        default=None, description="Who uses this deliverable next (None if it goes straight to Boss)."
    )


class TicketPlan(BaseModel):
    """Boss's plan: who works the ticket, in what order, and what each hands off."""

    ticket_id: int
    understanding: str = Field(description="What the ticket really needs, including hidden links (invoices, leases).")
    customer_facing: bool = Field(description="True if a customer will hear back from us about this ticket.")
    steps: list[PlanStep] = Field(min_length=1, max_length=4)
    success_criteria: list[str] = Field(description="How we will know the ticket is handled well.")
    risks_to_watch: list[str] = Field(description="Money, customer, data, or budget risks for this ticket.")


class HumanAction(BaseModel):
    """One thing the human must decide or do."""

    kind: Literal[
        "approve_payment", "approve_purchase_order", "approve_discount", "review_customer_draft", "decide", "fyi"
    ]
    request_id: int | None = Field(default=None, description="approval_requests.id, when this is an approval.")
    draft_id: int | None = Field(default=None, description="customer_drafts.id, when this is a draft review.")
    what: str
    amount: float | None = Field(default=None, description="Cash out in dollars (None if no cash moves).")
    why: str
    urgency: Literal["today", "this_week", "when_convenient"]


class FinalReport(BaseModel):
    """Boss's final answer to the human for one ticket."""

    ticket_id: int
    headline: str = Field(description="One sentence the owner can act on.")
    recommended_outcome: str = Field(description="What should happen, and why, in a short paragraph.")
    human_actions: list[HumanAction] = Field(
        description="Every approval request and draft on this ticket, plus any decision only a person can make."
    )
    how_the_team_worked: list[str] = Field(description="Who did what, in order, including hand-offs.")
    money_summary: str = Field(description="Cash now, what this ticket would spend, and cash left after.")
    agrees_with_customer_service: bool | None = Field(
        default=None, description="None if Customer Service did not review this ticket."
    )
    override_reason: str | None = Field(
        default=None, description="Required when you do not follow Customer Service's stance."
    )
    risks: list[str]
    data_gaps: list[str]


# ---------------------------------------------------------------------------
# Specialists
# ---------------------------------------------------------------------------

class StockLine(BaseModel):
    sku: str
    size: str
    on_hand: int
    needed: int | None = None
    shortfall: int | None = None


class RestockOption(BaseModel):
    vendor_id: int
    vendor_name: str
    sku: str
    size: str
    qty: int
    total_cost: float
    arrival_date: str | None = Field(description="None if the vendor cannot ship yet.")
    blocked_by_invoice_ids: list[int] = Field(default_factory=list)
    vendor_match_inferred: bool = Field(description="True: the DB has no SKU-vendor link; matched by specialty.")


class InventoryReport(SpecialistReport):
    stock_status: list[StockLine]
    restock_options: list[RestockOption] = Field(default_factory=list)
    substitutes: list[str] = Field(default_factory=list, description="In-stock alternatives (other sizes or items).")
    discount_view: str | None = Field(
        default=None, description="Stock-based view on a discount: does the stock level argue for or against it?"
    )


class PaymentPriority(BaseModel):
    rank: int
    item: str
    amount: float
    due: str | None
    why: str


class MarginCheck(BaseModel):
    sku: str
    quoted_unit_price: float
    margin_pct: float
    within_policy: bool


class AccountingReport(SpecialistReport):
    cash_on_hand: float
    obligations_total: float
    cash_after_obligations: float
    payment_priority: list[PaymentPriority] = Field(default_factory=list)
    margin_checks: list[MarginCheck] = Field(default_factory=list)
    liquidity_risk: Literal["none", "low", "high", "cannot_cover"]


class FacilitiesReport(SpecialistReport):
    lease_id: int | None
    monthly_rent: float | None
    next_due: str | None
    days_until_due: int | None
    is_overdue: bool | None
    can_pay_on_time: Literal["yes", "only_if_prioritized", "no", "unknown"]
    escalate_to_human: bool
    escalation_reason: str | None = None


class CustomerServiceReport(SpecialistReport):
    stance: Literal["support", "support_with_changes", "concerns", "oppose"] = Field(
        description="Your view of the team's plan, from the customer's side."
    )
    customer_impact: str = Field(description="What the customer experiences if we follow the plan.")
    what_the_customer_needs: str
    apology_needed: bool
    alternatives_for_customer: list[str] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list, description="customer_drafts ids you saved.")
    feedback_for_team: list[str] = Field(
        default_factory=list, description="What the team or the system should change, learned from this customer."
    )
    must_tell_human: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Team result
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    order: int
    agent: SpecialistName
    task: str
    report: dict | None = None
    error: str | None = None


class TeamUsage(BaseModel):
    agent_loops: int
    model_requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    token_limit: int


class TeamResult(BaseModel):
    """Everything one ticket run produced, for the human (and later the dashboard)."""

    team_run_id: str
    ticket_id: int
    started_at: datetime
    finished_at: datetime
    plan: TicketPlan | None
    steps: list[StepResult]
    customer_service_review: CustomerServiceReport | None = Field(
        description="Customer Service's review, passed to the human unedited."
    )
    final: FinalReport | None
    approval_requests: list[dict]
    customer_drafts: list[dict]
    ticket_status: str | None
    usage: TeamUsage
    stop_reason: str
    errors: list[str]
    feedback: str | None = Field(default=None, description="Owner feedback this run answered (re-run after Deny).")


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

class AuditToolCall(BaseModel):
    tool: str
    args: str
    result: str
    ok: bool


class AuditStep(BaseModel):
    step: int
    at: datetime
    tool_calls: list[AuditToolCall]


class AuditLoopEntry(BaseModel):
    """One agent loop: one agent, one task, every model step and tool call it made."""

    entry_type: Literal["agent_loop"] = "agent_loop"
    team_run_id: str
    loop_id: str
    ticket_id: int
    agent: AgentName
    phase: Literal["plan", "step", "delegation", "customer_review", "final"]
    called_by: str
    depth: int
    task: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    model: str
    steps: list[AuditStep]
    step_count: int
    tool_call_count: int
    rejected_calls: int
    delegated_to: list[str]
    stop_reason: str
    output: str | None
    error: str | None
    usage_own: dict[str, int]
    usage_with_delegations: dict[str, int]
    team_tokens_after: int


class AuditHumanEntry(BaseModel):
    """A person's action from the dashboard/API: approve, reject, refused execution, resolve, reset."""

    entry_type: Literal["human_decision"] = "human_decision"
    at: datetime
    action: Literal["approve", "reject", "execution_refused", "resolve", "reset"]
    ticket_id: int | None = None
    request_id: int | None = None
    decided_by: str | None = None
    summary: str
    amount: float | None = None
    cash_moved: float | None = None
    balance_after: float | None = None
    note: str | None = None
    source: str = "api"


class AuditRunSummary(BaseModel):
    """Closes one ticket run in the audit trail."""

    entry_type: Literal["team_run_summary"] = "team_run_summary"
    team_run_id: str
    ticket_id: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    model: str
    loops: list[str]
    usage: TeamUsage
    stop_reason: str
    headline: str | None
    approval_request_ids: list[int]
    draft_ids: list[int]
    ticket_status: str | None
    errors: list[str]
