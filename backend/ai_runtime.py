import os
from typing import Any


def get_openai_agent_model() -> str:
    """Return the OpenAI model name to use for CrewAI-backed agents."""
    configured_model = os.getenv("OPENAI_CREW_MODEL", "gpt-5.1").strip()
    if configured_model.startswith("openai/"):
        return configured_model
    return f"openai/{configured_model}"


def get_openai_image_model() -> str:
    """Return the OpenAI image model name used for room edits."""
    return os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5").strip()


def build_crewai_llm_kwargs(
    *,
    stream: bool = False,
    conversation_id: str | None = None,
    previous_response_id: str | None = None,
) -> dict[str, Any]:
    """Build a consistent OpenAI Responses API config for CrewAI LLMs."""
    llm_kwargs: dict[str, Any] = {
        "model": get_openai_agent_model(),
        "api": "responses",
        "store": True,
        "timeout": 120,
        "stream": stream,
    }
    if conversation_id:
        llm_kwargs["conversation"] = conversation_id
    if previous_response_id:
        llm_kwargs["previous_response_id"] = previous_response_id
    return llm_kwargs


def create_openai_client() -> Any:
    """Create an OpenAI SDK client lazily so imports fail only on chat/image usage."""
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
