import json
from pathlib import Path
from typing import Any, Iterator, Type

from ai_runtime import build_crewai_llm_kwargs, create_openai_client
from crew_inventory_handler import CrewInventoryHandler
from crew_room_handler import CrewRoomHandler
from db_handlers import get_crew_conversation, get_inventory_item, upsert_crew_conversation


class CrewCoordinator:
    """Chat-facing coordinator that delegates to inventory and room handlers."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.inventory_handler = CrewInventoryHandler(database_path)
        self.room_handler = CrewRoomHandler(database_path)

    def stream_turn(self, session_id: str, user_message: str) -> Iterator[dict[str, Any]]:
        """Stream one chat turn as SSE-friendly events."""
        conversation_state = get_crew_conversation(self.database_path, session_id) or {}
        conversation_id = conversation_state.get("openai_conversation_id") or self._create_conversation_id()
        previous_response_id = conversation_state.get("latest_response_id")

        coordinator_agent, coordinator_task, crew = self._build_crew(
            session_id=session_id,
            user_message=user_message,
            conversation_id=conversation_id,
            previous_response_id=previous_response_id,
        )

        streaming = crew.kickoff()
        streamed_text_parts: list[str] = []
        latest_response_id = previous_response_id

        for chunk in streaming:
            chunk_content = getattr(chunk, "content", "")
            if isinstance(chunk_content, str) and chunk_content:
                streamed_text_parts.append(chunk_content)
                yield {"type": "delta", "content": chunk_content}

            chunk_response_id = getattr(chunk, "response_id", None)
            if isinstance(chunk_response_id, str) and chunk_response_id:
                latest_response_id = chunk_response_id

        result = getattr(streaming, "result", None)
        final_text = ""
        if result is not None:
            final_text = getattr(result, "raw", "") or str(result)
        if not final_text.strip():
            final_text = "".join(streamed_text_parts).strip()

        # If CrewAI did not expose chunked text, still stream the final answer to the frontend.
        if final_text and not streamed_text_parts:
            for token in self._chunk_text_for_stream(final_text):
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

    def _build_crew(
        self,
        *,
        session_id: str,
        user_message: str,
        conversation_id: str,
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
