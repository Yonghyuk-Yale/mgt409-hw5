"""Facilities — leases and rent: due dates, whether rent can be paid on time, early escalation."""

from __future__ import annotations

from agents.base import AgentSpec, register, request_ids_exist
from models import FacilitiesReport

SPEC = register(AgentSpec(
    name="facilities",
    title="Facilities",
    prompt_file="facilities.md",
    output_type=FacilitiesReport,
    validators=(request_ids_exist,),
))
