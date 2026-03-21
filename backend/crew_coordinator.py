import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterator, Type

from ai_runtime import build_crewai_llm_kwargs, create_openai_client
from crew_inventory_handler import CrewInventoryHandler
from crew_room_handler import CrewRoomHandler
from db_handlers import get_crew_conversation, get_inventory_item, upsert_crew_conversation

logger = logging.getLogger(__name__)
DEBUG_LOG_PATH = Path(
    os.getenv("AGENT_DEBUG_LOG_PATH", "/Users/johannesantoni/VS Code/MysteriesAtTheGrand/.cursor/debug-9b5e82.log")
)
DEBUG_SESSION_ID = "9b5e82"


def _emit_debug_line(serialized_payload: str) -> None:
    line = f"AGENT_DEBUG {serialized_payload}"
    logging.getLogger("backend").info(line)
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except OSError:
        pass


def _debug_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    payload = {
        "sessionId": DEBUG_SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    serialized_payload = json.dumps(payload, separators=(",", ":"))
    _emit_debug_line(serialized_payload)
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as debug_file:
            debug_file.write(serialized_payload + "\n")
    except OSError as error:
        logger.info(
            "DEBUG_NDJSON_FALLBACK %s",
            json.dumps(
                {
                    **payload,
                    "fallbackErrorType": type(error).__name__,
                    "fallbackErrorMessage": str(error),
                    "fallbackPath": str(DEBUG_LOG_PATH),
                },
                separators=(",", ":"),
            ),
        )


class CrewCoordinator:
    """Chat-facing coordinator that delegates to inventory and room handlers."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.inventory_handler = CrewInventoryHandler(database_path)
        self.room_handler = CrewRoomHandler(database_path)

    def stream_turn(self, session_id: str, user_message: str) -> Iterator[dict[str, Any]]:
        """Stream one chat turn as SSE-friendly events."""
        conversation_state = get_crew_conversation(self.database_path, session_id) or {}
        previous_response_id = conversation_state.get("latest_response_id")
        conversation_id = None
        run_id = f"{session_id}-{int(time.time() * 1000)}"
        stream_started_at = time.perf_counter()

        # region agent log
        _debug_log(
            run_id=run_id,
            hypothesis_id="H3",
            location="crew_coordinator.py:stream_turn:start",
            message="chat stream turn started",
            data={
                "message_length": len(user_message),
                "has_previous_response_id": previous_response_id is not None,
            },
        )
        # endregion

        try:
            action_result = self._handle_player_action_if_needed(
                session_id=session_id,
                user_message=user_message,
                run_id=run_id,
            )
            if action_result is not None:
                final_text = str(action_result.get("user_message") or "").strip()
            else:
                final_text = self._run_concierge_reply(user_message=user_message)
            latest_response_id = None
            streamed_text_parts: list[str] = []

        except Exception as error:
            raise

        # region agent log
        _debug_log(
            run_id=run_id,
            hypothesis_id="H3",
            location="crew_coordinator.py:stream_turn:before_first_yield",
            message="chat stream ready to emit first event",
            data={
                "elapsed_ms_before_stream": round((time.perf_counter() - stream_started_at) * 1000, 2),
                "used_room_action": action_result is not None,
                "final_text_length": len(final_text),
            },
        )
        # endregion

        for token in self._chunk_text_for_stream(final_text):
            streamed_text_parts.append(token)
            yield {"type": "delta", "content": token}

        upsert_crew_conversation(
            database_path=self.database_path,
            session_id=session_id,
            openai_conversation_id=conversation_id,
            latest_response_id=latest_response_id,
        )

        yield {
            "type": "complete",
            "content": final_text,
            "openai_conversation_id": conversation_id,
            "latest_response_id": latest_response_id,
        }

    def _handle_player_action_if_needed(
        self,
        *,
        session_id: str,
        user_message: str,
        run_id: str,
    ) -> dict[str, Any] | None:
        """Use the proven inventory and room handlers directly for action-oriented turns."""
        action_started_at = time.perf_counter()
        looks_like_room_action = self._looks_like_room_action(user_message)
        resolved_item = self.inventory_handler.resolve_item(session_id, user_message)
        # region agent log
        _debug_log(
            run_id=run_id,
            hypothesis_id="H4",
            location="crew_coordinator.py:_handle_player_action_if_needed:resolved",
            message="inventory resolution and room-action classification completed",
            data={
                "elapsed_ms": round((time.perf_counter() - action_started_at) * 1000, 2),
                "looks_like_room_action": looks_like_room_action,
                "resolved_item_key": resolved_item["item_key"] if resolved_item else None,
            },
        )
        # endregion
        if resolved_item is None and not looks_like_room_action:
            return None
        return self.room_handler.apply_action(
            session_id=session_id,
            user_message=user_message,
            inventory_item=resolved_item,
            run_id=run_id,
        )

    def _run_concierge_reply(self, *, user_message: str) -> str:
        """Run a plain stateless concierge reply without native CrewAI tools."""
        try:
            from crewai import Agent, LLM
        except ImportError as error:
            raise RuntimeError("CrewAI must be installed before the coordinator can run.") from error

        concierge_agent = Agent(
            role="Crew Coordinator",
            goal="Reply to the player concisely and stay in world.",
            backstory=(
                "You are the private concierge wire for the Grand Pannonia Hotel. "
                "You keep the conversation short, natural, and useful."
            ),
            llm=LLM(**build_crewai_llm_kwargs(stream=False)),
            verbose=False,
            cache=False,
        )
        result = concierge_agent.kickoff(
            (
                "Respond to the current player turn. Keep the answer short and text-message-like.\n"
                f"Current player message: {user_message}\n"
                "Rules:\n"
                "- Most replies should be 1 to 4 short sentences.\n"
                "- Stay inside the world of the historic hotel mystery.\n"
                "- Do not describe using tools.\n"
                "- Do not write essays.\n"
            )
        )
        final_text = getattr(result, "raw", "") or str(result)
        if not final_text.strip():
            raise ValueError("The concierge reply was empty.")
        return final_text

    def _looks_like_room_action(self, user_message: str) -> bool:
        """Detect action-oriented commands that should go through the room handler."""
        normalized_message = user_message.lower()
        action_pattern = re.compile(
            r"\b(put|place|set|leave|drop|use|move|push|pull|open|close|inspect|look|search|check|take|pick|go|enter|walk|return|hide|unlock)\b"
        )
        return action_pattern.search(normalized_message) is not None

    def _build_crew(
        self,
        *,
        session_id: str,
        user_message: str,
        conversation_id: str | None,
        previous_response_id: str | None,
    ) -> tuple[Any, Any, Any]:
        """Build the one-turn coordinator crew with custom tools."""
        try:
            from crewai import Agent, Crew, LLM, Process, Task
            from crewai.tools import BaseTool
            from pydantic import BaseModel, Field
        except ImportError as error:
            raise RuntimeError("CrewAI must be installed before the coordinator can run.") from error

        inventory_handler = self.inventory_handler
        room_handler = self.room_handler
        database_path = self.database_path

        class InventoryLookupInput(BaseModel):
            item_reference: str = Field(..., description="The player's item reference, for example 'scarf'.")

        class InventoryLookupTool(BaseTool):
            name: str = "inventory_lookup"
            description: str = (
                "Check whether the player's suitcase inventory contains a referenced item. "
                "Use this before trying to place or use a carried object in a room."
            )
            args_schema: Type[BaseModel] = InventoryLookupInput

            def _run(self, item_reference: str) -> str:
                resolved_item = inventory_handler.resolve_item(session_id, item_reference)
                if resolved_item is None:
                    return json.dumps({"found": False, "item_reference": item_reference})
                return json.dumps(
                    {
                        "found": True,
                        "item_key": resolved_item["item_key"],
                        "item_name": resolved_item["item_name"],
                        "item_detail": resolved_item["item_detail"],
                    }
                )

        class RoomActionInput(BaseModel):
            user_message: str = Field(..., description="The full player message describing the requested room action.")
            item_key: str | None = Field(
                default=None,
                description="The resolved inventory item key when the player action uses an inventory item.",
            )

        class RoomActionTool(BaseTool):
            name: str = "room_action"
            description: str = (
                "Apply room navigation or modification logic, including safe room-state writes and inventory consumption."
            )
            args_schema: Type[BaseModel] = RoomActionInput

            def _run(self, user_message: str, item_key: str | None = None) -> str:
                inventory_item = None
                if item_key:
                    inventory_item = get_inventory_item(database_path, session_id, item_key)
                action_result = room_handler.apply_action(session_id=session_id, user_message=user_message, inventory_item=inventory_item)
                return json.dumps(action_result)

        coordinator_agent = Agent(
            role="Crew Coordinator",
            goal="Reply to the player concisely and coordinate inventory and room actions through the handler tools.",
            backstory=(
                "You are the private concierge wire for the Grand Pannonia Hotel. You keep the conversation short, "
                "natural, and useful, and you call specialist handlers whenever the player wants to use inventory or "
                "change the room."
            ),
            llm=LLM(
                **build_crewai_llm_kwargs(
                    stream=True,
                    conversation_id=conversation_id,
                    previous_response_id=previous_response_id,
                )
            ),
            verbose=False,
            cache=True,
            tools=[InventoryLookupTool(), RoomActionTool()],
        )

        coordinator_task = Task(
            description=(
                "Respond to the current player turn. Keep the answer short and text-message-like.\n"
                f"Current player message: {user_message}\n"
                "Rules:\n"
                "- Most replies should be 1 to 4 short sentences.\n"
                "- If the player wants to use an inventory item, call inventory_lookup first.\n"
                "- If the player wants to change the room or move rooms, call room_action.\n"
                "- Do not write essays.\n"
                "- Stay inside the world of the historic hotel mystery."
            ),
            expected_output="A concise in-world assistant reply, with tool calls when needed.",
            agent=coordinator_agent,
        )

        crew = Crew(
            agents=[coordinator_agent],
            tasks=[coordinator_task],
            process=Process.sequential,
            verbose=False,
            stream=True,
            cache=True,
        )

        return coordinator_agent, coordinator_task, crew

    def _create_conversation_id(self) -> str:
        """Create one OpenAI conversation object for this browser session."""
        client = create_openai_client()
        conversation = client.conversations.create()
        return conversation.id

    def _chunk_text_for_stream(self, text: str, chunk_size: int = 24) -> list[str]:
        """Break a final fallback response into small chunks for the frontend stream parser."""
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
