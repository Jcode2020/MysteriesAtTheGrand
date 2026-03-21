import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from ai_runtime import build_crewai_llm_kwargs, create_openai_client, get_openai_image_model
from db_handlers import (
    current_timestamp,
    get_latest_room_state_record,
    get_session_state,
    list_available_room_names,
    remove_inventory_item_and_create_room_state,
)

DEBUG_LOG_PATH = Path("/Users/johannesantoni/VS Code/MysteriesAtTheGrand/.cursor/debug-9b5e82.log")
DEBUG_SESSION_ID = "9b5e82"


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
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as debug_file:
        debug_file.write(json.dumps(payload, separators=(",", ":")) + "\n")


class CrewRoomHandler:
    """Navigate rooms and apply room-state changes safely."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def apply_action(
        self,
        session_id: str,
        user_message: str,
        inventory_item: dict[str, Any] | None = None,
        run_id: str = "no-run-id",
    ) -> dict[str, Any]:
        """Plan and apply a room action, optionally consuming an inventory item."""
        session_state = get_session_state(self.database_path, session_id)
        if session_state is None:
            raise ValueError("The current session state is not initialized.")

        current_room_name = str(session_state["current_room_name"])
        latest_room_state = get_latest_room_state_record(self.database_path, session_id, current_room_name)
        if latest_room_state is None:
            raise ValueError(f"No room state exists for the active room '{current_room_name}'.")

        action_plan = self._plan_action(
            user_message=user_message,
            current_room_name=current_room_name,
            latest_room_state=latest_room_state,
            inventory_item=inventory_item,
            available_room_names=list_available_room_names(self.database_path, session_id),
        )

        # region agent log
        _debug_log(
            run_id=run_id,
            hypothesis_id="H2",
            location="crew_room_handler.py:apply_action:plan",
            message="room action plan created",
            data={
                "current_room_name": current_room_name,
                "inventory_item_key": inventory_item["item_key"] if inventory_item else None,
                "action_possible": action_plan["action_possible"],
                "consume_item": action_plan["consume_item"],
                "needs_image_edit": action_plan["needs_image_edit"],
                "target_room_name": action_plan["target_room_name"],
                "has_image_edit_prompt": bool(action_plan["image_edit_prompt"]),
            },
        )
        # endregion

        if not action_plan["action_possible"]:
            return {
                "status": "rejected",
                "action_possible": False,
                "user_message": action_plan["response_text"],
                "room_state": None,
            }

        new_image_bytes = latest_room_state["room_image"]
        new_image_media_type = latest_room_state["image_media_type"]
        if action_plan["needs_image_edit"]:
            new_image_bytes = self._edit_room_image(
                existing_image_bytes=latest_room_state["room_image"],
                existing_media_type=latest_room_state["image_media_type"],
                edit_prompt=action_plan["image_edit_prompt"],
                run_id=run_id,
            )
            new_image_media_type = "image/png"

        created_room_state = remove_inventory_item_and_create_room_state(
            database_path=self.database_path,
            session_id=session_id,
            consumed_item_key=inventory_item["item_key"] if action_plan["consume_item"] and inventory_item else None,
            room_state={
                "room_name": action_plan["target_room_name"] or current_room_name,
                "room_image": new_image_bytes,
                "image_media_type": new_image_media_type,
                "room_modifications": action_plan["room_modifications"],
                "room_description": action_plan["updated_room_description"],
                "state_timestamp": current_timestamp(),
                "previous_state_id": latest_room_state["id"],
            },
            current_room_name=action_plan["target_room_name"] or current_room_name,
        )

        return {
            "status": "applied",
            "action_possible": True,
            "user_message": action_plan["response_text"],
            "room_state": created_room_state,
        }

    def _plan_action(
        self,
        *,
        user_message: str,
        current_room_name: str,
        latest_room_state: dict[str, Any],
        inventory_item: dict[str, Any] | None,
        available_room_names: list[str],
    ) -> dict[str, Any]:
        """Use a CrewAI agent to classify the requested room interaction."""
        try:
            from crewai import Agent, LLM
            from pydantic import BaseModel, Field
        except ImportError as error:
            raise RuntimeError("CrewAI must be installed before room actions can be evaluated.") from error

        class RoomActionPlan(BaseModel):
            action_possible: bool = Field(description="Whether the requested action can be completed now.")
            consume_item: bool = Field(description="Whether the provided inventory item should be consumed.")
            needs_image_edit: bool = Field(description="Whether the room image needs to change visually.")
            target_room_name: str | None = Field(default=None, description="The room that should become active.")
            room_modifications: str | None = Field(default=None, description="A short description of what changed.")
            updated_room_description: str = Field(
                description="A detailed room description reflecting the latest known truth after this action."
            )
            response_text: str = Field(
                description="A short player-facing response written like a concise text message."
            )
            image_edit_prompt: str | None = Field(
                default=None,
                description="The exact edit prompt for the image model when a visual change is needed.",
            )

        agent = Agent(
            role="Room Handler",
            goal="Decide whether a room action is possible and describe the resulting room state precisely.",
            backstory=(
                "You manage room navigation and environmental changes for a historic hotel mystery game. "
                "You must prefer the room description as the main source of truth, only using image edits when "
                "the room should visibly change."
            ),
            llm=LLM(**build_crewai_llm_kwargs()),
            verbose=False,
            cache=True,
        )

        inventory_text = "No inventory item is being used."
        if inventory_item is not None:
            inventory_text = (
                f"Inventory item available for this action: {inventory_item['item_name']} "
                f"({inventory_item['item_key']}) with detail '{inventory_item['item_detail']}'."
            )

        room_description = latest_room_state["room_description"] or "No room description is stored yet."
        result = agent.kickoff(
            (
                "You are evaluating one player action in the Grand Pannonia Hotel.\n"
                f"Current room: {current_room_name}\n"
                f"Available known rooms: {', '.join(available_room_names)}\n"
                f"Player message: {user_message}\n"
                f"{inventory_text}\n"
                f"Current room description:\n{room_description}\n"
                "Rules:\n"
                "- Prefer the stored room description as the primary truth source.\n"
                "- If the requested action only clarifies the room truth, keep the same image and update the room description.\n"
                "- If the request visibly changes the room, set needs_image_edit=true and produce a precise edit prompt.\n"
                "- Only consume the provided inventory item if the action is possible and the item is actually used.\n"
                "- Keep response_text brief, natural, and no more than four short sentences.\n"
                "- If the room does not support the action, explain that briefly and keep updated_room_description aligned with the current truth.\n"
            ),
            response_format=RoomActionPlan,
        )

        parsed_plan = getattr(result, "pydantic", None)
        if parsed_plan is None:
            raise RuntimeError("The room handler did not return a structured action plan.")

        target_room_name = parsed_plan.target_room_name or current_room_name
        if target_room_name not in available_room_names:
            parsed_plan.action_possible = False
            parsed_plan.consume_item = False
            parsed_plan.needs_image_edit = False
            parsed_plan.target_room_name = current_room_name
            parsed_plan.room_modifications = None
            parsed_plan.image_edit_prompt = None
            parsed_plan.response_text = "That room is not available yet."
            parsed_plan.updated_room_description = room_description

        return parsed_plan.model_dump()

    def _edit_room_image(
        self,
        *,
        existing_image_bytes: bytes,
        existing_media_type: str,
        edit_prompt: str | None,
        run_id: str,
    ) -> bytes:
        """Edit an existing room image while preserving the original composition and style."""
        if not edit_prompt:
            raise ValueError("An image edit prompt is required when the room image should change.")

        image_suffix = ".png"
        if existing_media_type == "image/jpeg":
            image_suffix = ".jpg"
        elif existing_media_type == "image/webp":
            image_suffix = ".webp"

        client = create_openai_client()
        with tempfile.NamedTemporaryFile(suffix=image_suffix) as source_image:
            source_image.write(existing_image_bytes)
            source_image.flush()

            with open(source_image.name, "rb") as image_file:
                edit_started_at = time.perf_counter()
                image_model = get_openai_image_model()
                # region agent log
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="H1",
                    location="crew_room_handler.py:_edit_room_image:before_openai",
                    message="starting room image edit request",
                    data={
                        "image_model": image_model,
                        "existing_media_type": existing_media_type,
                        "source_image_bytes": len(existing_image_bytes),
                        "prompt_length": len(edit_prompt),
                    },
                )
                # endregion
                try:
                    image_response = client.images.edit(
                        model=image_model,
                        image=image_file,
                        prompt=edit_prompt,
                        input_fidelity="high",
                    )
                except Exception as error:
                    # region agent log
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H1",
                        location="crew_room_handler.py:_edit_room_image:openai_error",
                        message="room image edit request failed",
                        data={
                            "elapsed_ms": round((time.perf_counter() - edit_started_at) * 1000, 2),
                            "error_type": type(error).__name__,
                            "error_message": str(error),
                        },
                    )
                    # endregion
                    raise

        # region agent log
        _debug_log(
            run_id=run_id,
            hypothesis_id="H1",
            location="crew_room_handler.py:_edit_room_image:after_openai",
            message="room image edit request completed",
            data={
                "elapsed_ms": round((time.perf_counter() - edit_started_at) * 1000, 2),
                "has_image_data": bool(image_response.data and image_response.data[0].b64_json),
            },
        )
        # endregion

        if not image_response.data or not image_response.data[0].b64_json:
            raise RuntimeError("The image edit request did not return edited image data.")
        return base64.b64decode(image_response.data[0].b64_json)
