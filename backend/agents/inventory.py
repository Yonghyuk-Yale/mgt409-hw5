"""Inventory — stock by SKU and size, shortfalls, substitutes, vendors, restock timing, stock-based discount view."""

from __future__ import annotations

from agents.base import AgentSpec, register, request_ids_exist
from models import InventoryReport

SPEC = register(AgentSpec(
    name="inventory",
    title="Inventory",
    prompt_file="inventory.md",
    output_type=InventoryReport,
    validators=(request_ids_exist,),
))
