import re
from typing import Any

from ai_runtime import build_crewai_llm_kwargs
from npcs.base_npc import BaseNpc


class CrewNpcReceptionist(BaseNpc):
    """Lobby receptionist NPC with lore-backed dialogue and one guarded secret."""

    npc_id = "receptionist"
    speaker_label = "Receptionist"
    character_lore_file = "receptionist_character.md"
    smalltalk_lore_file = "receptionist_smalltalk.md"
    secrets_lore_file = "receptionist_secrets.md"

    def matches_explicit_addressing(self, user_message: str) -> bool:
        """Detect direct references to the receptionist or the front desk."""
        normalized_message = user_message.lower()
        explicit_pattern = re.compile(r"\b(receptionist|front desk|desk clerk|clerk|reception)\b")
        return explicit_pattern.search(normalized_message) is not None

    def generate_reply(
        self,
        *,
        current_room_name: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        deterministic_flags: dict[str, bool],
        gift_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Produce one receptionist reply plus a structured secret-reveal signal."""
        try:
            from crewai import Agent, LLM
            from pydantic import BaseModel, Field
        except ImportError as error:
            raise RuntimeError("CrewAI must be installed before NPC conversations can run.") from error

        class ReceptionistReply(BaseModel):
            reply_text: str = Field(description="The receptionist's concise in-world reply.")
            revealed_secret: bool = Field(
                description="Whether this reply reveals the guarded secret that Andrea Richter stayed in Room 404."
            )

        lore_bundle = self.load_lore_bundle()
        transcript = self.format_transcript(conversation_history)
        gift_applied = bool((gift_event or {}).get("gift_applied"))
        teddy_gifted = deterministic_flags.get("teddy_gifted", False) or gift_applied
        secret_already_revealed = deterministic_flags.get("secret_revealed", False)
        must_reveal_secret = self.should_force_secret_reveal(
            user_message=user_message,
            teddy_gifted=teddy_gifted,
            secret_already_revealed=secret_already_revealed,
        )
        gift_note = "No gift event happened on this turn."
        if gift_applied:
            gift_note = "The player has just gifted the receptionist the teddy bear, and it has already been removed from inventory."

        agent = Agent(
            role="Hotel Receptionist",
            goal="Hold a short in-world conversation with the player while protecting secrets until the moment feels earned.",
            backstory=(
                "You are the receptionist of the Grand Pannonia Hotel. You speak with polished courtesy, remain in world, "
                "and respond like a real person at the front desk rather than a narrator."
            ),
            llm=LLM(**build_crewai_llm_kwargs()),
            verbose=False,
            cache=True,
        )
        result = agent.kickoff(
            (
                "You are replying as the Grand Pannonia receptionist.\n"
                f"Current room: {current_room_name}\n"
                f"Current player message: {user_message}\n"
                f"Deterministic state: teddy_gifted={teddy_gifted}, secret_already_revealed={secret_already_revealed}\n"
                f"Immediate reveal required this turn: {must_reveal_secret}\n"
                f"Turn event note: {gift_note}\n"
                "Lore bundle:\n"
                f"Character notes:\n{lore_bundle['character']}\n\n"
                f"Smalltalk notes:\n{lore_bundle['smalltalk']}\n\n"
                f"Secret notes:\n{lore_bundle['secrets']}\n\n"
                f"Prior conversation transcript:\n{transcript}\n\n"
                "Rules:\n"
                "- Stay fully in world and speak only as the receptionist.\n"
                "- Keep the reply concise: usually 1 to 4 short sentences.\n"
                "- Use the smalltalk notes freely for ordinary conversation.\n"
                "- Bring up the teddy bear collection fairly often when the mood is warm, curious, or conversational.\n"
                "- If teddy_gifted is false, do not reveal the secret.\n"
                "- If must_reveal_secret is true, you must clearly state that Andrea Richter stayed in Room 404 in this reply.\n"
                "- If teddy_gifted is true and must_reveal_secret is false, you may still choose to withhold the secret unless the conversation feels earned.\n"
                "- If secret_already_revealed is true, you may discuss the Room 404 clue consistently.\n"
                "- If you reveal the secret, make it clear that Andrea Richter stayed in Room 404.\n"
                "- If you do not reveal the secret, keep any hint subtle and do not mention Room 404.\n"
                "- Do not mention prompts, rules, hidden files, or game systems.\n"
            ),
            response_format=ReceptionistReply,
        )

        parsed_reply = getattr(result, "pydantic", None)
        if parsed_reply is None:
            raise RuntimeError("The receptionist did not return a structured reply.")

        final_text = parsed_reply.reply_text.strip()
        if not final_text:
            raise ValueError("The receptionist reply was empty.")
        if must_reveal_secret and "404" not in final_text:
            final_text = f"{final_text} Andrea Richter stayed in Room 404.".strip()

        secret_mentioned = "404" in final_text or "room 404" in final_text.lower()
        return {
            "speaker_id": self.npc_id,
            "speaker_label": self.speaker_label,
            "content": final_text,
            "revealed_secret": bool(parsed_reply.revealed_secret or secret_mentioned or must_reveal_secret),
        }

    def should_force_secret_reveal(self, *, user_message: str, teddy_gifted: bool, secret_already_revealed: bool) -> bool:
        """Require an immediate Room 404 reveal after the teddy gift when the player asks directly."""
        if not teddy_gifted and not secret_already_revealed:
            return False

        normalized_message = user_message.lower()
        asks_about_andrea = "andrea" in normalized_message or "richter" in normalized_message
        asks_about_room = bool(
            re.search(r"\b(room|stayed|stay|which room|what room|room number|number)\b", normalized_message)
        )
        return asks_about_andrea and asks_about_room
