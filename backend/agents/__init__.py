"""The five Campus Customs agents. Importing this package registers all of them."""

from agents import accounting, boss, customer_service, facilities, inventory  # noqa: F401
from agents.base import get_agent, run_loop, spec_for  # noqa: F401

AGENT_NAMES = ("boss", "inventory", "accounting", "facilities", "customer_service")
