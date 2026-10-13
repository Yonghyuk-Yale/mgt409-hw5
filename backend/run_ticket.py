"""Run the agent team on one or more tickets from the command line.

    ..\\.venv\\Scripts\\python.exe run_ticket.py 102
    ..\\.venv\\Scripts\\python.exe run_ticket.py 101 102 103 --reset

--reset recopies data/campus_customs.db over data/campus_customs_new.db first (shop rule:
reset before a full ticket-resolving run). Every agent loop is appended to output/audit_trail.json.
Nothing is paid or sent: approval requests and drafts wait on the board for a person.
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from team import run_ticket  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


def reset_db() -> None:
    """Rewrite the working copy from the original in place (works even if the API has it open)."""
    src = sqlite3.connect(f"file:{(DATA / 'campus_customs.db').as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(DATA / "campus_customs_new.db")
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    print("Working DB reset from the original.")


async def main(ticket_ids: list[int]) -> None:
    for ticket_id in ticket_ids:
        result = await run_ticket(ticket_id)
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team on tickets.")
    parser.add_argument("tickets", nargs="+", type=int)
    parser.add_argument("--reset", action="store_true", help="Recopy the original DB before running.")
    args = parser.parse_args()
    if args.reset:
        reset_db()
    asyncio.run(main(args.tickets))
