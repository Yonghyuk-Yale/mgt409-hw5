"""Audit trail — output/audit_trail.json.

Cumulative: every agent loop of every ticket run is appended, then a run summary closes the
run. Nothing is ever overwritten, so the file is a full history of how the team reached each
answer (who was asked what, which MCP tools ran with which arguments, what came back, how many
tokens it cost, and why each loop stopped).

- One entry per agent loop, written as soon as the loop ends (a crash mid-ticket still leaves
  the finished loops on disk).
- Customer names, emails, and long numbers are masked (see guardrails.mask).
- If the file is unreadable it is moved aside (audit_trail.broken-<time>.json), never deleted.
- Writing the audit must never break the team run.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from guardrails import mask, shorten
from models import AuditStep, AuditToolCall

AUDIT_FILE = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
log = logging.getLogger("campus_customs.audit")
_lock = threading.Lock()


def to_text(value: object) -> str:
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def steps_from_messages(messages: list[ModelMessage], names: tuple[str, ...]) -> tuple[list[AuditStep], int, int]:
    """Turn PydanticAI's message list into loop steps: one model response + the tool calls it made.

    Returns (steps, tool call count, rejected calls). A rejected call is a tool error or an
    output the validators sent back for repair.
    """
    outcomes: dict[str, tuple[str, bool]] = {}
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolReturnPart):
                outcomes[part.tool_call_id] = (shorten(mask(to_text(part.content), names)), True)
            elif isinstance(part, RetryPromptPart) and part.tool_call_id:
                outcomes[part.tool_call_id] = ("rejected: " + shorten(mask(to_text(part.content), names)), False)

    steps: list[AuditStep] = []
    calls_total = rejected = 0
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        calls = []
        for part in message.parts:
            if not isinstance(part, ToolCallPart):
                continue
            result, ok = outcomes.get(part.tool_call_id, ("(no result)", False))
            if part.tool_name == "final_result" and ok:
                result = "accepted"
            if not ok:
                rejected += 1
            calls.append(AuditToolCall(
                tool=part.tool_name, args=shorten(mask(to_text(part.args), names), 400), result=result, ok=ok,
            ))
        if calls:
            calls_total += len(calls)
            steps.append(AuditStep(step=len(steps) + 1, at=message.timestamp, tool_calls=calls))
    return steps, calls_total, rejected


def append(entry: BaseModel, path: Path = AUDIT_FILE) -> None:
    """Append one entry to the audit trail. Never raises."""
    try:
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            entries: list = []
            if path.exists():
                try:
                    entries = json.loads(path.read_text(encoding="utf-8") or "[]")
                    if not isinstance(entries, list):
                        raise ValueError("audit trail is not a list")
                except (ValueError, json.JSONDecodeError):
                    broken = path.with_name(f"audit_trail.broken-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json")
                    path.rename(broken)
                    log.error("audit_trail.json was unreadable; moved to %s", broken.name)
                    entries = []
            entries.append(json.loads(entry.model_dump_json()))
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
    except Exception:  # the audit must never break the team
        log.exception("Could not write the audit trail")
