import os


# Long-lived SSE chat turns can include multiple LLM calls plus one image edit.
# Railway's default Gunicorn timeout is too short for that production path.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "180"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", str(timeout + 30)))
