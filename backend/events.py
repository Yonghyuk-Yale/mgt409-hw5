"""Live event feed for the dashboard: what each agent is saying and which tools it is using.

The audit trail (audit.py) is the permanent record, written when a loop ends. This feed is the
live view: events are published the moment they happen (a loop starts, a tool is called, a tool
answers, an agent reports), so the board can poll GET /api/events and refresh as the team works.

Kept in memory (the latest MAX_EVENTS). Each event has an increasing `seq`, so a client asks
only for events after the last one it has seen. Thread-safe: agents run on the ops loop thread,
the API reads from the web server's thread.
"""

from __future__ import annotations

import itertools
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from guardrails import mask, shorten

MAX_EVENTS = 1000

_lock = threading.Lock()
_events: deque[dict] = deque(maxlen=MAX_EVENTS)
_seq = itertools.count(1)


def publish(kind: str, text: str, **fields: Any) -> dict:
    """Add one event. `text` is the one-line, human-readable description shown on the board."""
    event = {
        "seq": 0,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "text": shorten(mask(text), 500),
        **{k: v for k, v in fields.items() if v is not None},
    }
    with _lock:
        event["seq"] = next(_seq)
        _events.append(event)
    return event


def recent(after: int = 0, limit: int = 100, ticket_id: int | None = None) -> dict:
    """Events with seq > after (oldest first), at most `limit` of the newest ones."""
    with _lock:
        items = [e for e in _events if e["seq"] > after and (ticket_id is None or e.get("ticket_id") == ticket_id)]
        latest = _events[-1]["seq"] if _events else 0
    return {"latest_seq": latest, "count": len(items[-limit:]), "events": items[-limit:]}
