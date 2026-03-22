import re
from pathlib import Path
from typing import Any

from ai_runtime import build_crewai_llm_kwargs
from db_handlers import list_inventory_items


class CrewInventoryHandler:
    """Resolve player item references against the current session inventory."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def resolve_item(self, session_id: str, item_reference: str) -> dict[str, Any] | None:
        """Resolve a user-facing item phrase to one concrete inventory row."""
        inventory_items = list_inventory_items(self.database_path, session_id)
        if not inventory_items:
            return None

        exact_match = self._match_inventory_item(inventory_items, item_reference)
        if exact_match is not None:
            return exact_match

        agent_match_key = self._resolve_item_with_agent(inventory_items, item_reference)
        if agent_match_key is None:
            return None

        return next((item for item in inventory_items if item["item_key"] == agent_match_key), None)

    def _match_inventory_item(self, inventory_items: list[dict[str, Any]], item_reference: str) -> dict[str, Any] | None:
        """Use cheap deterministic matching before spending LLM tokens."""
        normalized_reference = self._normalize(item_reference)
        for item in inventory_items:
            searchable_tokens = {
                self._normalize(str(item["item_key"])),
                self._normalize(str(item["item_name"])),
                self._normalize(str(item["item_detail"])),
            }
            if normalized_reference in searchable_tokens:
                return item
            if normalized_reference and any(normalized_reference in token for token in searchable_tokens):
                return item
            if normalized_reference and any(token and token in normalized_reference for token in searchable_tokens):
                return item
        return None

    def _resolve_item_with_agent(self, inventory_items: list[dict[str, Any]], item_reference: str) -> str | None:
        """Fall back to a small CrewAI agent when deterministic matching is ambiguous."""
        try:
            from crewai import Agent, LLM
            from pydantic import BaseModel, Field
        except ImportError:
            return None

        class InventoryChoice(BaseModel):
            item_key: str | None = Field(
                default=None,
                description="The matching item_key when the user references an item that exists in the inventory.",
            )

        try:
            agent = Agent(
                role="Inventory Handler",
                goal="Match the player's item reference to one inventory item when a clear match exists.",
                backstory=(
                    "You manage the guest's suitcase inventory and must only return an item key when the match is "
                    "clearly supported by the available items."
                ),
                llm=LLM(**build_crewai_llm_kwargs()),
                verbose=False,
                cache=True,
            )

            options_text = "\n".join(
                f"- {item['item_key']}: {item['item_name']} ({item['item_detail']})" for item in inventory_items
            )
            result = agent.kickoff(
                (
                    "Choose the best matching inventory item key for the player's reference.\n"
                    f"Player reference: {item_reference}\n"
                    "Available items:\n"
                    f"{options_text}\n"
                    "Return null when no item clearly matches."
                ),
                response_format=InventoryChoice,
            )
        except Exception:
            return None

        parsed_choice = getattr(result, "pydantic", None)
        if parsed_choice is None:
            return None
        return parsed_choice.item_key

    def _normalize(self, value: str) -> str:
        """Normalize a short player phrase for cheap deterministic matching."""
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
