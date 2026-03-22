from abc import ABC, abstractmethod
from pathlib import Path


class BaseNpc(ABC):
    """Shared helpers for backend-owned conversational NPCs."""

    npc_id: str
    speaker_label: str
    character_lore_file: str
    smalltalk_lore_file: str
    secrets_lore_file: str

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.backend_dir = Path(__file__).resolve().parent.parent
        self.lore_dir = self.backend_dir / "lore"

    def load_lore_bundle(self) -> dict[str, str]:
        """Load the required lore markdown files and fail fast if any are missing."""
        return {
            "character": self._read_lore_file(self.character_lore_file),
            "smalltalk": self._read_lore_file(self.smalltalk_lore_file),
            "secrets": self._read_lore_file(self.secrets_lore_file),
        }

    def format_transcript(self, messages: list[dict[str, str]]) -> str:
        """Format persisted thread messages into a short prompt transcript."""
        if not messages:
            return "No prior conversation has been recorded yet."

        transcript_lines: list[str] = []
        for message in messages:
            speaker_label = message.get("speaker_label") or ("Guest" if message.get("role") == "user" else self.speaker_label)
            transcript_lines.append(f"{speaker_label}: {message.get('content', '').strip()}")
        return "\n".join(transcript_lines)

    def _read_lore_file(self, file_name: str) -> str:
        """Read one lore file from the canonical backend lore directory."""
        lore_path = (self.lore_dir / file_name).resolve()
        if not lore_path.exists():
            raise FileNotFoundError(f"Required lore file not found: {lore_path}")
        return lore_path.read_text(encoding="utf-8").strip()

    @abstractmethod
    def matches_explicit_addressing(self, user_message: str) -> bool:
        """Return whether the user is clearly addressing this NPC."""
