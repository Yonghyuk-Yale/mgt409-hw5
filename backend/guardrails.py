"""Hard limits for the agent team. These are enforced in code, not just asked for in prompts.

Token budget (per ticket, whole team together)
- TEAM_TOKEN_LIMIT tokens and MAX_AGENT_LOOPS agent loops at most.
- FINAL_RESERVE_TOKENS are held back so Boss can always write the final report, even when
  the specialists used up the rest. Only Boss's final loop may spend the reserve.
- One agent loop may make at most PER_LOOP_REQUESTS model calls.

Delegation (any specialist may ask any other specialist)
- MAX_DEPTH: team -> step agent (1) -> teammate (2) -> teammate (3). Depth 3 cannot ask further.
- No asking yourself or anyone already in the current chain (no A -> B -> A loops).
- MAX_ASKS_PER_LOOP questions per loop; the same question to the same teammate is asked once.
"""

from __future__ import annotations

import re

TEAM_TOKEN_LIMIT = 150_000
FINAL_RESERVE_TOKENS = 25_000
MAX_AGENT_LOOPS = 12
PER_LOOP_REQUESTS = 8
TEAM_REQUEST_LIMIT = 60
TEAM_TOOL_CALL_LIMIT = 80
MAX_DEPTH = 3
MAX_ASKS_PER_LOOP = 3
TICKET_TIMEOUT_SECONDS = 420

# Who may ask whom. Every specialist can reach every other specialist (full connectivity);
# specialists reach Boss through their report's `for_boss` field, which Boss always reads.
CAN_ASK: dict[str, tuple[str, ...]] = {
    "boss": ("inventory", "accounting", "facilities", "customer_service"),
    "inventory": ("accounting", "facilities", "customer_service"),
    "accounting": ("inventory", "facilities", "customer_service"),
    "facilities": ("accounting", "inventory", "customer_service"),
    "customer_service": ("inventory", "accounting", "facilities"),
}

# Ticket types where a customer will hear from us; Customer Service must review these.
CUSTOMER_TICKET_TYPES = frozenset({"customer_order", "price_override"})


class BudgetExhausted(RuntimeError):
    """The team hit a hard limit; Boss wraps up with what is known so far."""


# ---------------------------------------------------------------------------
# Privacy: what is written to the audit trail
# ---------------------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# US-style phone numbers only (555-123-4567, (555) 123-4567, +1 555.123.4567); ISO dates do not match.
_PHONE = re.compile(r"(?<![\d-])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\d-])")
_LONG_NUMBER = re.compile(r"\b(?:\d[ -]?){12,19}\b")


def mask(text: str, names: tuple[str, ...] = ()) -> str:
    """Hide personal details before text reaches disk: emails, phone/card numbers, customer names.

    Customers are referred to by ticket number in the audit trail; the ticket itself is the
    lookup key for anyone with access to the board.
    """
    text = _EMAIL.sub("[email]", text)
    text = _LONG_NUMBER.sub("[number]", text)
    text = _PHONE.sub("[phone]", text)
    for name in sorted(names, key=len, reverse=True):  # full names before their parts
        if name and len(name) > 1:
            text = re.sub(rf"\b{re.escape(name)}\b", "[customer]", text, flags=re.IGNORECASE)
    return text


def name_variants(full_names: list[str], shop_words: set[str]) -> tuple[str, ...]:
    """Full customer names plus each part ("Hi Tauhid" must be masked too).

    Parts that are ordinary shop words (from product, vendor, and landlord names, e.g. "Yale")
    or shorter than 3 letters are left alone, so the audit stays readable.
    """
    out = set()
    for full in full_names:
        out.add(full)
        for part in re.findall(r"[A-Za-z][A-Za-z'-]+", full):
            if len(part) >= 3 and part.lower() not in shop_words:
                out.add(part)
    return tuple(sorted(out))


def shorten(text: str, limit: int = 600) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
