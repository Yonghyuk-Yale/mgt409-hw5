"""What every agent shares: its spec, the agent loop, and how one agent asks another.

An *agent loop* is one PydanticAI run: the agent reads its task, calls MCP tools (and maybe
asks a teammate), and returns its typed report. Every loop goes through `run_loop`, which
enforces the team budget, writes the loop to the audit trail, and tracks who asked whom.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import RunUsage, UsageLimits

import audit
import events
import mcp_tools
from guardrails import (
    CAN_ASK, FINAL_RESERVE_TOKENS, MAX_AGENT_LOOPS, MAX_ASKS_PER_LOOP, MAX_DEPTH, PER_LOOP_REQUESTS,
    TEAM_REQUEST_LIMIT, TEAM_TOKEN_LIMIT, TEAM_TOOL_CALL_LIMIT, BudgetExhausted, mask, shorten,
)
from llm import MODEL_NAME, get_model
from models import AuditLoopEntry

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
SHARED_RULES = PROMPTS / "shared_rules.md"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class TeamState:
    """One ticket run, shared by every loop in it."""

    team_run_id: str
    ticket_id: int
    ticket: dict
    mcp: MCPToolset
    mask_names: tuple[str, ...] = ()
    usage: RunUsage = field(default_factory=RunUsage)  # the whole team's usage, shared by every loop
    loops_started: int = 0
    loop_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class LoopFrame:
    loop_id: str
    agent: str
    child_tokens: int = 0
    asked: set[tuple[str, str]] = field(default_factory=set)
    delegated_to: list[str] = field(default_factory=list)


@dataclass
class TeamDeps:
    """What a tool or validator sees through RunContext.deps."""

    team: TeamState
    agent: str
    chain: tuple[str, ...]  # agents in the current ask-chain, outermost first (includes this agent)
    frame: LoopFrame


Validator = Callable[[RunContext[TeamDeps], Any], Awaitable[Any]]


@dataclass(frozen=True)
class AgentSpec:
    name: str
    title: str
    prompt_file: str
    output_type: type[BaseModel]
    validators: tuple[Validator, ...] = ()


# ---------------------------------------------------------------------------
# Building agents
# ---------------------------------------------------------------------------

_SPECS: dict[str, AgentSpec] = {}


def register(spec: AgentSpec) -> AgentSpec:
    _SPECS[spec.name] = spec
    return spec


def spec_for(name: str) -> AgentSpec:
    return _SPECS[name]


def load_instructions(spec: AgentSpec) -> str:
    """Team-wide rules first, then the agent's own role prompt. Re-read on every loop."""
    return SHARED_RULES.read_text(encoding="utf-8") + "\n\n---\n\n" + (PROMPTS / spec.prompt_file).read_text(encoding="utf-8")


@cache
def get_agent(name: str, output_type: type[BaseModel] | None = None) -> Agent[TeamDeps, Any]:
    """One cached agent per (role, output type). Boss has two: TicketPlan and FinalReport."""
    spec = _SPECS[name]
    agent = Agent(
        get_model(),
        deps_type=TeamDeps,
        output_type=output_type or spec.output_type,
        name=spec.name,
        retries=2,  # malformed output or a validator rejection gets two repair attempts
    )

    @agent.instructions
    def instructions() -> str:
        return load_instructions(spec)

    if CAN_ASK.get(name):
        agent.tool(ask_teammate)

    for validator in spec.validators:
        agent.output_validator(validator)
    return agent


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

async def ask_teammate(ctx: RunContext[TeamDeps], teammate: str, question: str) -> dict:
    """Ask another specialist one focused question and get their structured report back.

    teammate: one of "inventory", "accounting", "facilities", "customer_service" (not yourself).
    question: what you need, the numbers you already have, and what you will do with the answer.
    Limits: at most 3 questions per task, no asking someone already in this chain, and the team
    token budget applies. If the answer is refused, carry on with what you have and say so.
    """
    deps = ctx.deps
    me = deps.agent
    teammate = teammate.strip().lower().replace(" ", "_")
    if teammate not in CAN_ASK.get(me, ()):
        return {"answered": False, "reason": f"{me} cannot ask '{teammate}'. Allowed: {list(CAN_ASK.get(me, ()))}."}
    if teammate in deps.chain:
        return {"answered": False, "reason": f"{teammate} is already working on this chain ({' -> '.join(deps.chain)}); "
                "asking back would loop. Use what you have."}
    if len(deps.chain) >= MAX_DEPTH:
        return {"answered": False, "reason": f"Delegation depth limit ({MAX_DEPTH}) reached. Use what you have."}
    key = (teammate, " ".join(question.lower().split()))
    if key in deps.frame.asked:
        return {"answered": False, "reason": "You already asked this teammate this question."}
    if len(deps.frame.asked) >= MAX_ASKS_PER_LOOP:
        return {"answered": False, "reason": f"Question limit ({MAX_ASKS_PER_LOOP} per task) reached."}
    deps.frame.asked.add(key)

    prompt = (
        f"Ticket {deps.team.ticket_id}. Your teammate **{me}** asks you a question while working this ticket.\n\n"
        f"Question from {me}:\n{question}\n\n"
        "Answer only what was asked, from MCP tool results, in your report format. "
        "Keep it short. If you file an approval request or a draft because of this question, list its id."
    )
    try:
        output = await run_loop(
            teammate, prompt, deps.team, phase="delegation", called_by=me, chain=deps.chain, parent=deps.frame,
        )
    except BudgetExhausted as exc:
        return {"answered": False, "reason": f"Team budget: {exc}. Use what you have and say so."}
    except Exception as exc:  # the teammate failed; the asker carries on
        return {"answered": False, "reason": f"{teammate} could not answer ({type(exc).__name__})."}
    return {"answered": True, "teammate": teammate, "report": output.model_dump(mode="json")}


# ---------------------------------------------------------------------------
# The agent loop
# ---------------------------------------------------------------------------

def _usage_dict(u: RunUsage) -> dict[str, int]:
    return {
        "requests": u.requests, "tool_calls": u.tool_calls, "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens, "total_tokens": u.total_tokens,
    }


def _diff(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {k: after[k] - before.get(k, 0) for k in after}


def _stop_reason(error: BaseException | None) -> str:
    if error is None:
        return "completed"
    if isinstance(error, BudgetExhausted):
        return "budget_exhausted"
    if isinstance(error, UsageLimitExceeded):
        return "usage_limit"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ModelHTTPError):
        return "content_filter" if "content_filter" in str(error.body) else "model_error"
    if isinstance(error, UnexpectedModelBehavior):
        return "invalid_output"
    return "error"


class _LiveFeed:
    """Publishes one loop's activity to the dashboard's event feed as it happens."""

    def __init__(self, team: TeamState, agent: str, phase: str, loop_id: str, called_by: str):
        self.base = {"team_run_id": team.team_run_id, "ticket_id": team.ticket_id, "agent": agent,
                     "phase": phase, "loop_id": loop_id}
        self.agent, self.phase, self.called_by = agent, phase, called_by
        self.names = team.mask_names
        self.team = team

    def _pub(self, kind: str, text: str, **extra) -> None:
        try:
            events.publish(kind, mask(text, self.names), **self.base, team_tokens=self.team.usage.total_tokens,
                           loops=self.team.loops_started, **extra)
        except Exception:  # the live feed must never break a run
            pass

    def started(self) -> None:
        who = "the team" if self.called_by == "team" else self.called_by
        self._pub("loop_started", f"{self.agent} starts ({self.phase}), called by {who}.", called_by=self.called_by)

    def model_response(self, response: ModelResponse) -> None:
        for part in response.parts:
            if isinstance(part, TextPart) and part.content.strip():
                self._pub("says", part.content)
            elif isinstance(part, ToolCallPart):
                if part.tool_name == "final_result":
                    continue
                args = part.args_as_dict() if hasattr(part, "args_as_dict") else {}
                if part.tool_name == "ask_teammate":
                    self._pub("asks", f"asks {args.get('teammate', '?')}: {args.get('question', '')}",
                              tool="ask_teammate", to=args.get("teammate"))
                else:
                    arg_text = ", ".join(f"{k}={v}" for k, v in args.items())
                    self._pub("tool_call", f"calls {part.tool_name}({arg_text})", tool=part.tool_name)

    def tool_results(self, request) -> None:
        for part in getattr(request, "parts", []):
            if isinstance(part, ToolReturnPart) and part.tool_name not in ("final_result",):
                content = part.content
                ok = not (isinstance(content, dict) and (content.get("ok") is False or content.get("found") is False))
                self._pub("tool_result", f"{part.tool_name} -> {audit.to_text(content)}", tool=part.tool_name, ok=ok)
            elif isinstance(part, RetryPromptPart):
                self._pub("retry", f"asked to fix: {audit.to_text(part.content)}", tool=part.tool_name)

    def finished(self, output, tokens: int) -> None:
        text = next((getattr(output, f) for f in ("headline", "summary", "understanding")
                     if getattr(output, f, None)), "done")
        stance = getattr(output, "stance", None)
        self._pub("report", f"{self.agent} reports: {text}", stance=stance, tokens=tokens)

    def failed(self, error: BaseException, tokens: int = 0) -> None:
        self._pub("loop_failed", f"{self.agent} stopped: {type(error).__name__}: {error}",
                  stop_reason=_stop_reason(error), tokens=tokens)


async def run_loop(
    agent_name: str,
    prompt: str,
    team: TeamState,
    *,
    phase: str,
    called_by: str,
    chain: tuple[str, ...] = (),
    parent: LoopFrame | None = None,
    output_type: type[BaseModel] | None = None,
):
    """Run one agent loop under the team budget and record it in the audit trail.

    `output_type` overrides the agent's default (Boss plans with TicketPlan, reports with FinalReport).
    """
    final = phase == "final"
    loop_cap = MAX_AGENT_LOOPS if final else MAX_AGENT_LOOPS - 1  # the last loop is kept for Boss's final report
    token_cap = TEAM_TOKEN_LIMIT if final else TEAM_TOKEN_LIMIT - FINAL_RESERVE_TOKENS
    if team.loops_started >= loop_cap:
        raise BudgetExhausted(f"agent loop limit ({MAX_AGENT_LOOPS} per ticket) reached")
    if team.usage.total_tokens >= token_cap:
        raise BudgetExhausted(f"token budget ({token_cap:,} for this phase) used up")

    team.loops_started += 1
    loop_id = f"{team.team_run_id}-L{team.loops_started:02d}"
    frame = LoopFrame(loop_id=loop_id, agent=agent_name)
    deps = TeamDeps(team=team, agent=agent_name, chain=(*chain, agent_name), frame=frame)
    agent = get_agent(agent_name, output_type)
    limits = UsageLimits(
        total_tokens_limit=token_cap, request_limit=TEAM_REQUEST_LIMIT, tool_calls_limit=TEAM_TOOL_CALL_LIMIT,
    )

    before = _usage_dict(team.usage)
    started_at, t0 = datetime.now(timezone.utc), time.perf_counter()
    run = None
    output = None
    error: BaseException | None = None
    live = _LiveFeed(team, agent_name, phase, loop_id, called_by)
    live.started()
    try:
        async with agent.iter(
            prompt, deps=deps, usage=team.usage, usage_limits=limits,
            toolsets=[mcp_tools.toolset_for(agent_name, team.mcp)],
        ) as run:
            requests = 0
            async for node in run:
                if Agent.is_model_request_node(node):
                    live.tool_results(node.request)
                    requests += 1
                    if requests > PER_LOOP_REQUESTS:
                        raise BudgetExhausted(f"{agent_name} needed more than {PER_LOOP_REQUESTS} model calls in one loop")
                elif Agent.is_call_tools_node(node):
                    live.model_response(node.model_response)
        output = run.result.output
        # own tokens only: teammates' loops it delegated to are counted on their own report
        live.finished(output, team.usage.total_tokens - before["total_tokens"] - frame.child_tokens)
    except BaseException as exc:  # recorded below, then re-raised
        error = exc
        live.failed(exc, max(0, team.usage.total_tokens - before["total_tokens"] - frame.child_tokens))
    finally:
        after = _usage_dict(team.usage)
        with_delegations = _diff(after, before)
        own = dict(with_delegations)
        own["total_tokens"] = max(0, own["total_tokens"] - frame.child_tokens)
        try:
            messages = run.all_messages() if run is not None else []
        except Exception:
            messages = []
        steps, calls, rejected = audit.steps_from_messages(messages, team.mask_names)
        audit.append(AuditLoopEntry(
            team_run_id=team.team_run_id,
            loop_id=loop_id,
            ticket_id=team.ticket_id,
            agent=agent_name,
            phase=phase,
            called_by=called_by,
            depth=len(deps.chain),
            task=shorten(mask(prompt, team.mask_names), 1500),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            duration_seconds=round(time.perf_counter() - t0, 2),
            model=MODEL_NAME,
            steps=steps,
            step_count=len(steps),
            tool_call_count=calls,
            rejected_calls=rejected,
            delegated_to=frame.delegated_to,
            stop_reason=_stop_reason(error),
            output=shorten(mask(output.model_dump_json(), team.mask_names), 4000) if output is not None else None,
            error=f"{type(error).__name__}: {shorten(str(error), 300)}" if error else None,
            usage_own=own,
            usage_with_delegations=with_delegations,
            team_tokens_after=team.usage.total_tokens,
        ))
        team.loop_ids.append(loop_id)
        if parent is not None:
            parent.child_tokens += with_delegations["total_tokens"]
            parent.delegated_to.append(loop_id)
        if error is not None:
            team.errors.append(f"{loop_id} {agent_name}: {type(error).__name__}: {shorten(str(error), 200)}")
    if error is not None:
        raise error
    return output


# ---------------------------------------------------------------------------
# Validators shared by several agents
# ---------------------------------------------------------------------------

async def request_ids_exist(ctx: RunContext[TeamDeps], output):
    """Reject approval-request ids the agent made up (they must exist on the board)."""
    ids = getattr(output, "approval_request_ids", None) or []
    if not ids:
        return output
    board = await mcp_tools.call(ctx.deps.team.mcp, "list_approval_requests")
    known = {r["id"] for r in board.get("requests", [])}
    unknown = [i for i in ids if i not in known]
    if unknown:
        raise ModelRetry(f"approval_request_ids {unknown} do not exist on the board. List only ids a tool returned.")
    return output
