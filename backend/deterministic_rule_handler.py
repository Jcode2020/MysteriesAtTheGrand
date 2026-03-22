import re
from pathlib import Path
from typing import Any

from db_handlers import get_deterministic_rule_state, remove_inventory_item, set_deterministic_rule_state


class DeterministicRuleHandler:
    """Evaluate and persist deterministic NPC-related state transitions."""

    RECEPTIONIST_ID = "receptionist"
    RECEPTIONIST_TEDDY_GIFTED_RULE = "teddy_gifted"
    RECEPTIONIST_SECRET_REVEALED_RULE = "secret_revealed"

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def receptionist_is_available(self, current_room_name: str) -> bool:
        """Return whether the receptionist should be reachable from the current room."""
        return current_room_name.strip().lower() == "lobby"

    def get_rule_flags(self, session_id: str, npc_id: str) -> dict[str, bool]:
        """Return the currently persisted boolean flags for one NPC."""
        return {
            self.RECEPTIONIST_TEDDY_GIFTED_RULE: self._rule_is_true(
                session_id=session_id,
                npc_id=npc_id,
                rule_key=self.RECEPTIONIST_TEDDY_GIFTED_RULE,
            ),
            self.RECEPTIONIST_SECRET_REVEALED_RULE: self._rule_is_true(
                session_id=session_id,
                npc_id=npc_id,
                rule_key=self.RECEPTIONIST_SECRET_REVEALED_RULE,
            ),
        }

    def apply_receptionist_gift_if_triggered(
        self,
        *,
        session_id: str,
        user_message: str,
        inventory_item: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Consume the teddy and persist the gift rule when the player offers it."""
        already_gifted = self._rule_is_true(
            session_id=session_id,
            npc_id=self.RECEPTIONIST_ID,
            rule_key=self.RECEPTIONIST_TEDDY_GIFTED_RULE,
        )
        normalized_message = user_message.lower()
        gift_pattern = re.compile(r"\b(give|gift|present|offer|hand)\b")
        gift_intent_detected = gift_pattern.search(normalized_message) is not None
        if already_gifted:
            return {"gift_applied": False, "gift_reason": "already_gifted", "removed_item": None}

        if inventory_item is None or str(inventory_item.get("item_key")) != "teddy":
            return {"gift_applied": False, "gift_reason": "no_teddy", "removed_item": None}

        if not gift_intent_detected:
            return {"gift_applied": False, "gift_reason": "no_gift_intent", "removed_item": None}

        removed_item = remove_inventory_item(self.database_path, session_id, "teddy")
        set_deterministic_rule_state(
            database_path=self.database_path,
            session_id=session_id,
            npc_id=self.RECEPTIONIST_ID,
            rule_key=self.RECEPTIONIST_TEDDY_GIFTED_RULE,
            rule_value="true",
        )
        return {"gift_applied": True, "gift_reason": "teddy_gifted", "removed_item": removed_item}

    def mark_secret_revealed(self, session_id: str, npc_id: str) -> dict[str, Any]:
        """Persist that an NPC has already revealed their protected secret."""
        return set_deterministic_rule_state(
            database_path=self.database_path,
            session_id=session_id,
            npc_id=npc_id,
            rule_key=self.RECEPTIONIST_SECRET_REVEALED_RULE,
            rule_value="true",
        )

    def _rule_is_true(self, *, session_id: str, npc_id: str, rule_key: str) -> bool:
        """Read one NPC rule and interpret the stored string as a boolean."""
        return get_deterministic_rule_state(
            database_path=self.database_path,
            session_id=session_id,
            npc_id=npc_id,
            rule_key=rule_key,
        ) == "true"
