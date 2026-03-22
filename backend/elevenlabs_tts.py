import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
RECEPTIONIST_VOICE_CACHE: dict[str, bytes] = {}


def synthesize_receptionist_speech(text: str) -> tuple[bytes, str]:
    """Generate one receptionist speech line via ElevenLabs and cache the result in memory."""
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("text must be a non-empty string")

    cached_audio = RECEPTIONIST_VOICE_CACHE.get(normalized_text)
    if cached_audio is not None:
        return cached_audio, "audio/mpeg"

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY must be configured before receptionist speech can be generated.")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID_RECEPTIONIST", "").strip()
    if not voice_id:
        raise RuntimeError(
            "ELEVENLABS_VOICE_ID_RECEPTIONIST must be configured before receptionist speech can be generated."
        )

    request_url = f"{ELEVENLABS_BASE_URL}/{voice_id}?{urlencode({'output_format': ELEVENLABS_OUTPUT_FORMAT})}"
    request_body = json.dumps({"text": normalized_text}).encode("utf-8")
    request = Request(
        request_url,
        data=request_body,
        method="POST",
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            audio_bytes = response.read()
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore") if hasattr(error, "read") else ""
        raise RuntimeError(
            f"ElevenLabs returned HTTP {error.code} while generating receptionist speech."
            + (f" Body: {error_body[:300]}" if error_body else "")
        ) from error
    except URLError as error:
        raise RuntimeError("Could not reach ElevenLabs while generating receptionist speech.") from error

    if not audio_bytes:
        raise RuntimeError("ElevenLabs returned an empty audio response.")

    RECEPTIONIST_VOICE_CACHE[normalized_text] = audio_bytes
    return audio_bytes, "audio/mpeg"


def clear_receptionist_voice_cache() -> None:
    """Clear the in-memory receptionist speech cache for tests."""
    RECEPTIONIST_VOICE_CACHE.clear()
