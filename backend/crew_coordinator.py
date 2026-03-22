import re
from pathlib import Path
from typing import Any, Iterator

from ai_runtime import build_crewai_llm_kwargs
from crew_inventory_handler import CrewInventoryHandler
from crew_room_handler import CrewRoomHandler
from db_handlers import append_conversation_message, get_npc_registry_entry, get_session_state, list_conversation_messages
from deterministic_rule_handler import DeterministicRuleHandler
from npcs import CrewNpcReceptionist


class CrewCoordinator:
    """Chat-facing coordinator that routes turns across world and NPC handlers."""

    WORLD_SPEAKER_ID = "hotel_world"
    WORLD_SPEAKER_LABEL = "Grand Pannonia Hotel"

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.inventory_handler = CrewInventoryHandler(database_path)
        self.room_handler = CrewRoomHandler(database_path)
        self.rule_handler = DeterministicRuleHandler(database_path)
        self.receptionist = CrewNpcReceptionist(database_path)

    def stream_turn(self, session_id: str, user_message: str) -> Iterator[dict[str, Any]]:
        """Stream one chat turn as SSE-friendly events."""
        session_state = get_session_state(self.database_path, session_id)
        if session_state is None:
            raise ValueError("The current session state is not initialized.")
        current_room_name = str(session_state["current_room_name"])

        turn_result = self._resolve_turn(
            session_id=session_id,
            current_room_name=current_room_name,
            user_message=user_message.strip(),
        )
        final_text = str(turn_result["content"]).strip()
        if not final_text:
            raise ValueError("The coordinator produced an empty reply.")

        for token in self._chunk_text_for_stream(final_text):
            yield {
                "type": "delta",
                "content": token,
                "speaker_id": turn_result["speaker_id"],
                "speaker_label": turn_result["speaker_label"],
                "speaker_portrait_base64": turn_result.get("speaker_portrait_base64"),
                "speaker_image_media_type": turn_result.get("speaker_image_media_type"),
            }

        yield {
            "type": "complete",
            "content": final_text,
            "speaker_id": turn_result["speaker_id"],
            "speaker_label": turn_result["speaker_label"],
            "speaker_portrait_base64": turn_result.get("speaker_portrait_base64"),
            "speaker_image_media_type": turn_result.get("speaker_image_media_type"),
            "openai_conversation_id": None,
            "latest_response_id": None,
        }

    def _resolve_turn(self, *, session_id: str, current_room_name: str, user_message: str) -> dict[str, Any]:
        """Choose the correct in-world handler for the current turn."""
        resolved_item = self.inventory_handler.resolve_item(session_id, user_message)
        explicit_receptionist_target = self.receptionist.matches_explicit_addressing(user_message)
        receptionist_available = self.rule_handler.receptionist_is_available(current_room_name)

        if explicit_receptionist_target and not receptionist_available:
            return self._store_world_turn(
                session_id=session_id,
                user_message=user_message,
                assistant_message="The receptionist is not here just now.",
            )

        if explicit_receptionist_target:
            return self._handle_receptionist_turn(
                session_id=session_id,
                current_room_name=current_room_name,
                user_message=user_message,
                resolved_item=resolved_item,
            )

        action_result = self._handle_player_action_if_needed(
            session_id=session_id,
            user_message=user_message,
            resolved_item=resolved_item,
        )
        if action_result is not None:
            return self._store_world_turn(
                session_id=session_id,
                user_message=user_message,
                assistant_message=str(action_result.get("user_message") or "").strip(),
            )

        if receptionist_available:
            return self._handle_receptionist_turn(
                session_id=session_id,
                current_room_name=current_room_name,
                user_message=user_message,
                resolved_item=resolved_item,
            )

        return self._store_world_turn(
            session_id=session_id,
            user_message=user_message,
            assistant_message=self._run_world_reply(
                session_id=session_id,
                current_room_name=current_room_name,
                user_message=user_message,
            ),
        )

    def _handle_player_action_if_needed(
        self,
        *,
        session_id: str,
        user_message: str,
        resolved_item: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Use the proven inventory and room handlers directly for action-oriented turns."""
        if resolved_item is None and not self._looks_like_room_action(user_message):
            return None
        return self.room_handler.apply_action(session_id=session_id, user_message=user_message, inventory_item=resolved_item)

    def _handle_receptionist_turn(
        self,
        *,
        session_id: str,
        current_room_name: str,
        user_message: str,
        resolved_item: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Run one receptionist conversation turn with deterministic state support."""
        gift_event = self.rule_handler.apply_receptionist_gift_if_triggered(
            session_id=session_id,
            user_message=user_message,
            inventory_item=resolved_item,
        )
        deterministic_flags = self.rule_handler.get_rule_flags(session_id, self.receptionist.npc_id)
        conversation_history = list_conversation_messages(
            database_path=self.database_path,
            session_id=session_id,
            speaker_id=self.receptionist.npc_id,
            limit=12,
        )
        receptionist_reply = self.receptionist.generate_reply(
            current_room_name=current_room_name,
            user_message=user_message,
            conversation_history=conversation_history,
            deterministic_flags=deterministic_flags,
            gift_event=gift_event,
        )
        append_conversation_message(
            database_path=self.database_path,
            session_id=session_id,
            speaker_id=self.receptionist.npc_id,
            speaker_label=self.receptionist.speaker_label,
            role="user",
            content=user_message,
        )
        append_conversation_message(
            database_path=self.database_path,
            session_id=session_id,
            speaker_id=self.receptionist.npc_id,
            speaker_label=self.receptionist.speaker_label,
            role="assistant",
            content=str(receptionist_reply["content"]),
        )
        if receptionist_reply["revealed_secret"]:
            self.rule_handler.mark_secret_revealed(session_id, self.receptionist.npc_id)
        return self._enrich_npc_turn(receptionist_reply)

    def _run_world_reply(self, *, session_id: str, current_room_name: str, user_message: str) -> str:
        """Run a short in-world reply for non-NPC, non-action conversational turns."""
        try:
            from crewai import Agent, LLM
        except ImportError as error:
            raise RuntimeError("CrewAI must be installed before the coordinator can run.") from error

        conversation_history = list_conversation_messages(
            database_path=self.database_path,
            session_id=session_id,
            speaker_id=self.WORLD_SPEAKER_ID,
            limit=12,
        )
        transcript = self._format_transcript(conversation_history)
        world_agent = Agent(
            role="Crew Coordinator",
            goal="Reply to the player concisely and stay in world.",
            backstory=(
                "You speak for Grand Pannonia Hotel inside the world interaction channel. "
                "You keep the conversation short, natural, useful, and fully in world."
            ),
            llm=LLM(**build_crewai_llm_kwargs(stream=False)),
            verbose=False,
            cache=False,
        )
        result = world_agent.kickoff(
            (
                "Respond to the current player turn. Keep the answer short and text-message-like.\n"
                f"Current room: {current_room_name}\n"
                f"Current player message: {user_message}\n"
                f"Previous conversation transcript:\n{transcript}\n"
                "Rules:\n"
                "- Most replies should be 1 to 4 short sentences.\n"
                "- Stay inside the world of the historic hotel mystery.\n"
                "- Do not describe using tools.\n"
                "- Do not write essays.\n"
            )
        )
        final_text = getattr(result, "raw", "") or str(result)
        if not final_text.strip():
            raise ValueError("The hotel reply was empty.")
        return final_text

    def _store_world_turn(self, *, session_id: str, user_message: str, assistant_message: str) -> dict[str, Any]:
        """Persist one world-channel conversation turn and return the stream payload."""
        append_conversation_message(
            database_path=self.database_path,
            session_id=session_id,
            speaker_id=self.WORLD_SPEAKER_ID,
            speaker_label=self.WORLD_SPEAKER_LABEL,
            role="user",
            content=user_message,
        )
        append_conversation_message(
            database_path=self.database_path,
            session_id=session_id,
            speaker_id=self.WORLD_SPEAKER_ID,
            speaker_label=self.WORLD_SPEAKER_LABEL,
            role="assistant",
            content=assistant_message,
        )
        return {
            "speaker_id": self.WORLD_SPEAKER_ID,
            "speaker_label": self.WORLD_SPEAKER_LABEL,
            "content": assistant_message,
        }

    def _enrich_npc_turn(self, turn_result: dict[str, Any]) -> dict[str, Any]:
        """Attach database-backed NPC metadata such as the portrait image."""
        speaker_id = str(turn_result["speaker_id"])
        npc_entry = get_npc_registry_entry(self.database_path, speaker_id)
        if npc_entry is None:
            return turn_result

        enriched_turn = dict(turn_result)
        enriched_turn["speaker_portrait_base64"] = npc_entry["portrait_image_base64"]
        enriched_turn["speaker_image_media_type"] = npc_entry["image_media_type"]
        enriched_turn["speaker_label"] = npc_entry["npc_label"]
        return enriched_turn

    def _looks_like_room_action(self, user_message: str) -> bool:
        """Detect action-oriented commands that should go through the room handler."""
        normalized_message = user_message.lower()
        action_pattern = re.compile(
            r"\b(put|place|set|leave|drop|use|move|push|pull|open|close|inspect|look|search|check|take|pick|go|enter|walk|return|hide|unlock)\b"
        )
        return action_pattern.search(normalized_message) is not None

    def _format_transcript(self, messages: list[dict[str, Any]]) -> str:
        """Format a persisted world-thread transcript for prompting."""
        if not messages:
            return "No prior conversation has been recorded yet."

        transcript_lines: list[str] = []
        for message in messages:
            speaker_label = message.get("speaker_label") or (
                "Guest" if message.get("role") == "user" else self.WORLD_SPEAKER_LABEL
            )
            transcript_lines.append(f"{speaker_label}: {str(message.get('content') or '').strip()}")
        return "\n".join(transcript_lines)

    def _chunk_text_for_stream(self, text: str, chunk_size: int = 24) -> list[str]:
        """Break a final fallback response into small chunks for the frontend stream parser."""
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
