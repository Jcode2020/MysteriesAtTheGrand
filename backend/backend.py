import logging
import os
import sys
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from flask import Flask, Response, g, jsonify, request, send_file

from db_handlers import (
    ensure_session_bootstrap,
    get_latest_room_state as fetch_latest_room_state,
    get_session_state,
    initialize_database,
    list_inventory_items,
    list_room_states as fetch_room_states,
    load_seed_manifest,
    reset_session_progress as clear_session_progress,
    seed_persistent_room_states,
    validate_room_state_payload,
    create_room_state as insert_room_state,
)

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT_DIR = BACKEND_DIR.parent
DEFAULT_DATABASE_PATH = REPO_ROOT_DIR / "db" / "hotel_db.sqlite3"
DEFAULT_SCHEMA_PATH = BACKEND_DIR / "schema.sql"
DEFAULT_PERSISTENT_ROOM_SEED_MANIFEST_PATH = BACKEND_DIR / "seed" / "persistent" / "manifest.json"
DEFAULT_OPENING_AUDIO_PATH = BACKEND_DIR / "static" / "audio" / "Secrets_of_the_Grand_Pannonia_2026-03-21T133239.mp3"
DEFAULT_INTRO_AUDIO_PATH = BACKEND_DIR / "static" / "audio" / "intro.mp3"
DEFAULT_PRIVACY_NOTICE_PATH = BACKEND_DIR / "legal" / "privacy-notice.md"
SESSION_COOKIE_NAME = "grand_pannonia_session_id"
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(message)s"
STREAM_HANDLER_NAME = "grand_pannonia_backend_stream"
FILE_HANDLER_NAME = "grand_pannonia_backend_file"

_ACTIVE_LOG_FILE_PATH: Path | None = None

logger = logging.getLogger(__name__)


def _emit_agent_debug(payload: dict[str, Any]) -> None:
    """Write one structured debug line to the Railway-visible backend logs."""
    import json

    serialized_payload = json.dumps(payload, separators=(",", ":"))
    logger.info("AGENT_DEBUG %s", serialized_payload)
    try:
        sys.stderr.write(f"AGENT_DEBUG {serialized_payload}\n")
        sys.stderr.flush()
    except OSError:
        pass


def _get_logger_handler(handler_name: str) -> logging.Handler | None:
    """Return one configured backend logger handler by its stable name."""
    return next((handler for handler in logger.handlers if handler.get_name() == handler_name), None)


def _resolve_log_file_path() -> Path | None:
    """Return the active logfile path when the repo-root logs directory is usable."""
    global _ACTIVE_LOG_FILE_PATH

    logs_directory = (REPO_ROOT_DIR / "logs").resolve()
    if not logs_directory.is_dir():
        _ACTIVE_LOG_FILE_PATH = None
        return None
    if not os.access(logs_directory, os.W_OK):
        _ACTIVE_LOG_FILE_PATH = None
        return None

    if _ACTIVE_LOG_FILE_PATH is None or _ACTIVE_LOG_FILE_PATH.parent != logs_directory:
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        _ACTIVE_LOG_FILE_PATH = logs_directory / f"{timestamp}_logfile.log"

    return _ACTIVE_LOG_FILE_PATH


def _configure_logging() -> Path | None:
    """Configure backend logging for terminal output and optional repo-root file output."""
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = _get_logger_handler(STREAM_HANDLER_NAME)
    if stream_handler is None:
        stream_handler = logging.StreamHandler()
        stream_handler.set_name(STREAM_HANDLER_NAME)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    configured_log_file_path = _resolve_log_file_path()
    existing_file_handler = _get_logger_handler(FILE_HANDLER_NAME)
    existing_file_path = (
        Path(existing_file_handler.baseFilename).resolve()
        if isinstance(existing_file_handler, logging.FileHandler)
        else None
    )

    if configured_log_file_path is None:
        if existing_file_handler is not None:
            logger.removeHandler(existing_file_handler)
            existing_file_handler.close()
        return None

    if existing_file_path != configured_log_file_path.resolve():
        if existing_file_handler is not None:
            logger.removeHandler(existing_file_handler)
            existing_file_handler.close()

        file_handler = logging.FileHandler(configured_log_file_path, encoding="utf-8")
        file_handler.set_name(FILE_HANDLER_NAME)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return configured_log_file_path


def _configure_flask_logging(app: Flask) -> None:
    """Keep Flask's named app logger aligned without mutating shared handlers."""
    app.logger.setLevel(logger.level)
    if app.logger.name != logger.name:
        app.logger.propagate = True


def _configure_werkzeug_logging() -> None:
    """Avoid duplicate request lines once the app emits its own request logs."""
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.WARNING)


def _log_request_summary(response: Any, started_at: float | None) -> None:
    """Emit one low-risk request summary for backend debugging."""
    duration_ms = 0.0
    if started_at is not None:
        duration_ms = (perf_counter() - started_at) * 1000

    origin = request.headers.get("Origin")
    remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr or "-")
    request_summary = (
        "%s %s -> %s in %.2fms (remote=%s%s)"
        % (
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            remote_addr,
            f", origin={origin}" if origin else "",
        )
    )
    logger.info(request_summary)


def _resolve_database_path(database_path: str | Path | None = None) -> Path:
    """Resolve the SQLite database path from the argument or environment."""
    if database_path is not None:
        return Path(database_path).expanduser().resolve()

    room_db_path = os.getenv("ROOM_DB_PATH")
    if room_db_path:
        return Path(room_db_path).expanduser().resolve()

    return DEFAULT_DATABASE_PATH


def _resolve_schema_path(schema_path: str | Path | None = None) -> Path:
    """Resolve the SQLite schema path from an override, env var, or backend default."""
    if schema_path is not None:
        return Path(schema_path).expanduser().resolve()

    configured_schema_path = os.getenv("ROOM_SCHEMA_PATH")
    if configured_schema_path:
        return Path(configured_schema_path).expanduser().resolve()

    return DEFAULT_SCHEMA_PATH.resolve()


def _resolve_seed_manifest_path(seed_manifest_path: str | Path | None = None) -> Path:
    """Resolve the persistent room seed manifest path."""
    if seed_manifest_path is not None:
        return Path(seed_manifest_path).expanduser().resolve()

    configured_manifest_path = os.getenv("PERSISTENT_ROOM_SEED_MANIFEST_PATH")
    if configured_manifest_path:
        return Path(configured_manifest_path).expanduser().resolve()

    return DEFAULT_PERSISTENT_ROOM_SEED_MANIFEST_PATH.resolve()


def _resolve_opening_audio_path(opening_audio_path: str | Path | None = None) -> Path:
    """Resolve the opening-theme audio path from the argument or environment."""
    if opening_audio_path is not None:
        return Path(opening_audio_path).expanduser().resolve()

    configured_audio_path = os.getenv("OPENING_AUDIO_PATH")
    if configured_audio_path:
        return Path(configured_audio_path).expanduser().resolve()

    return DEFAULT_OPENING_AUDIO_PATH.resolve()


def _resolve_intro_audio_path(intro_audio_path: str | Path | None = None) -> Path:
    """Resolve the narrated intro audio path from the argument or environment."""
    if intro_audio_path is not None:
        return Path(intro_audio_path).expanduser().resolve()

    configured_audio_path = os.getenv("INTRO_AUDIO_PATH")
    if configured_audio_path:
        return Path(configured_audio_path).expanduser().resolve()

    return DEFAULT_INTRO_AUDIO_PATH.resolve()


def _resolve_privacy_notice_path(privacy_notice_path: str | Path | None = None) -> Path:
    """Resolve the prototype privacy notice path from the argument or backend default."""
    if privacy_notice_path is not None:
        return Path(privacy_notice_path).expanduser().resolve()
    return DEFAULT_PRIVACY_NOTICE_PATH.resolve()

def _resolve_frontend_origin() -> str:
    """Build the allowed frontend origin for local development requests."""
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
    if frontend_origin:
        return frontend_origin.rstrip("/")

    frontend_host = os.getenv("FRONTEND_HOST", "").strip()
    frontend_port = os.getenv("FRONTEND_PORT", "").strip()
    if frontend_host and frontend_port:
        return f"http://{frontend_host}:{frontend_port}"

    return ""


def _configured_frontend_origin_looks_local(configured_origin: str) -> bool:
    """Return whether the configured frontend origin is a localhost-style dev origin."""
    normalized_origin = configured_origin.lower()
    return (
        normalized_origin.startswith("http://localhost")
        or normalized_origin.startswith("http://127.0.0.1")
        or normalized_origin.startswith("http://0.0.0.0")
    )


def _origin_matches_configured_frontend(origin: str | None, configured_origin: str) -> bool:
    """Return whether the request origin matches the configured frontend origin."""
    if not origin or not configured_origin:
        return False
    return origin.rstrip("/") == configured_origin.rstrip("/")


def _resolve_response_origin(configured_origin: str) -> str:
    """Choose the response origin that is allowed to receive credentialed responses."""
    request_origin = request.headers.get("Origin")
    if _origin_matches_configured_frontend(request_origin, configured_origin):
        return configured_origin
    return ""


def _request_origin_is_allowed(configured_origin: str) -> bool:
    """Allow non-browser requests while enforcing the configured browser origin."""
    request_origin = request.headers.get("Origin")
    if request_origin is None:
        return True
    return _origin_matches_configured_frontend(request_origin, configured_origin)


def _resolve_session_cookie_secure() -> bool:
    """Use secure cookies in production by default while keeping local HTTP dev simple."""
    configured_value = os.getenv("SESSION_COOKIE_SECURE")
    if configured_value is not None and configured_value.strip():
        return configured_value.lower() == "true"

    configured_frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
    return bool(configured_frontend_origin) and not _configured_frontend_origin_looks_local(configured_frontend_origin)


def _resolve_session_cookie_samesite() -> str:
    """Resolve the SameSite policy for the anonymous session cookie."""
    configured_value = os.getenv("SESSION_COOKIE_SAMESITE", "").strip().capitalize()
    if not configured_value:
        configured_frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
        if configured_frontend_origin and not _configured_frontend_origin_looks_local(configured_frontend_origin):
            return "None"
        return "Lax"
    if configured_value not in {"Lax", "Strict", "None"}:
        raise ValueError("SESSION_COOKIE_SAMESITE must be one of: Lax, Strict, None")
    return configured_value


def _generate_session_id() -> str:
    """Create a non-guessable session identifier for anonymous playthroughs."""
    return uuid.uuid4().hex


def _ensure_session_id() -> str:
    """Return the active session ID, creating one when the visitor is new."""
    generated_session_id = getattr(g, "session_id", None)
    if isinstance(generated_session_id, str) and generated_session_id:
        return generated_session_id

    existing_session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if existing_session_id:
        g.session_id = existing_session_id
        g.should_set_session_cookie = False
        _emit_agent_debug(
            {
                "sessionId": "9b5e82",
                "runId": f"cookie-{existing_session_id}",
                "hypothesisId": "H10",
                "location": "backend.py:_ensure_session_id",
                "message": "reused existing session cookie",
                "data": {
                    "request_path": request.path,
                    "origin": request.headers.get("Origin"),
                    "has_cookie_header": request.headers.get("Cookie") is not None,
                    "session_id": existing_session_id,
                },
            }
        )
        return existing_session_id

    new_session_id = _generate_session_id()
    g.should_set_session_cookie = True
    g.session_id = new_session_id
    _emit_agent_debug(
        {
            "sessionId": "9b5e82",
            "runId": f"cookie-{new_session_id}",
            "hypothesisId": "H10",
            "location": "backend.py:_ensure_session_id",
            "message": "generated new session cookie",
            "data": {
                "request_path": request.path,
                "origin": request.headers.get("Origin"),
                "has_cookie_header": request.headers.get("Cookie") is not None,
                "session_id": new_session_id,
            },
        }
    )
    return new_session_id


def _attach_session_cookie(response: Response, session_id: str, app: Flask) -> Response:
    """Persist the anonymous session cookie for future room-state requests."""
    if getattr(g, "should_set_session_cookie", False):
        _set_session_cookie(response, session_id, app)
    return response


def _set_session_cookie(response: Response, session_id: str, app: Flask) -> Response:
    """Write the active anonymous session cookie to the response."""
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite=app.config["SESSION_COOKIE_SAMESITE"],
        secure=app.config["SESSION_COOKIE_SECURE"],
        max_age=60 * 60 * 24 * 30,
    )
    _emit_agent_debug(
        {
            "sessionId": "9b5e82",
            "runId": f"cookie-{session_id}",
            "hypothesisId": "H8",
            "location": "backend.py:_set_session_cookie",
            "message": "set session cookie on response",
            "data": {
                "request_path": request.path,
                "origin": request.headers.get("Origin"),
                "session_id": session_id,
                "cookie_secure": app.config["SESSION_COOKIE_SECURE"],
                "cookie_samesite": app.config["SESSION_COOKIE_SAMESITE"],
                "has_set_cookie_header": response.headers.get("Set-Cookie") is not None,
            },
        }
    )
    return response


def _replace_session_cookie(response: Response, app: Flask) -> Response:
    """Rotate the anonymous session cookie after a destructive session action."""
    new_session_id = _generate_session_id()
    g.session_id = new_session_id
    g.should_set_session_cookie = False
    return _set_session_cookie(response, new_session_id, app)


def _ensure_runtime_session(app: Flask) -> str:
    """Guarantee that a request has a session cookie, session state row, and starter inventory."""
    session_id = _ensure_session_id()
    ensure_session_bootstrap(
        database_path=app.config["DATABASE_PATH"],
        session_id=session_id,
        starter_inventory=app.config["STARTER_INVENTORY_SEED_ENTRIES"],
    )
    return session_id


def _sse_event(event_name: str, payload: dict[str, Any]) -> str:
    """Format one server-sent event payload line."""
    import json

    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


def create_app(
    database_path: str | Path | None = None,
    schema_path: str | Path | None = None,
    seed_manifest_path: str | Path | None = None,
    opening_audio_path: str | Path | None = None,
    intro_audio_path: str | Path | None = None,
    privacy_notice_path: str | Path | None = None,
) -> Flask:
    """Create the Flask app and wire it to the SQLite room-state database."""
    configured_log_file_path = _configure_logging()

    app = Flask(__name__)
    _configure_flask_logging(app)
    _configure_werkzeug_logging()
    resolved_database_path = _resolve_database_path(database_path)
    resolved_schema_path = _resolve_schema_path(schema_path)
    resolved_seed_manifest_path = _resolve_seed_manifest_path(seed_manifest_path)
    resolved_opening_audio_path = _resolve_opening_audio_path(opening_audio_path)
    resolved_intro_audio_path = _resolve_intro_audio_path(intro_audio_path)
    resolved_privacy_notice_path = _resolve_privacy_notice_path(privacy_notice_path)
    seed_manifest = load_seed_manifest(resolved_seed_manifest_path)
    app.config["DATABASE_PATH"] = resolved_database_path
    app.config["SCHEMA_PATH"] = resolved_schema_path
    app.config["FRONTEND_ORIGIN"] = _resolve_frontend_origin()
    app.config["OPENING_AUDIO_PATH"] = resolved_opening_audio_path
    app.config["INTRO_AUDIO_PATH"] = resolved_intro_audio_path
    app.config["PRIVACY_NOTICE_PATH"] = resolved_privacy_notice_path
    app.config["SESSION_COOKIE_SECURE"] = _resolve_session_cookie_secure()
    app.config["SESSION_COOKIE_SAMESITE"] = _resolve_session_cookie_samesite()
    app.config["PERSISTENT_ROOM_SEED_MANIFEST_PATH"] = resolved_seed_manifest_path
    app.config["PERSISTENT_ROOM_SEED_ENTRIES"] = seed_manifest["persistent_rooms"]
    app.config["STARTER_INVENTORY_SEED_ENTRIES"] = seed_manifest["starter_inventory"]

    if app.config["SESSION_COOKIE_SAMESITE"] == "None" and not app.config["SESSION_COOKIE_SECURE"]:
        raise ValueError("SESSION_COOKIE_SAMESITE=None requires SESSION_COOKIE_SECURE=true")

    _emit_agent_debug(
        {
            "sessionId": "9b5e82",
            "runId": "startup-cookie-config",
            "hypothesisId": "H8",
            "location": "backend.py:create_app",
            "message": "resolved production cookie configuration",
            "data": {
                "frontend_origin": app.config["FRONTEND_ORIGIN"],
                "session_cookie_secure": app.config["SESSION_COOKIE_SECURE"],
                "session_cookie_samesite": app.config["SESSION_COOKIE_SAMESITE"],
            },
        }
    )

    initialize_database(resolved_database_path, resolved_schema_path)
    seed_persistent_room_states(resolved_database_path, app.config["PERSISTENT_ROOM_SEED_ENTRIES"])
    logger.info("Initialized room state database at %s", resolved_database_path)
    if configured_log_file_path is not None:
        logger.info("Backend logging also writes to %s", configured_log_file_path)
    else:
        logger.info("Repo-root logs directory unavailable; backend logging will use terminal output only.")

    @app.before_request
    def mark_request_start_time() -> None:
        g.request_started_at = perf_counter()

    @app.after_request
    def add_cors_headers(response: Any) -> Any:
        _log_request_summary(response, getattr(g, "request_started_at", None))
        allowed_origin = _resolve_response_origin(app.config["FRONTEND_ORIGIN"])
        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")

        if request.headers.get("X-Forwarded-Proto", request.scheme) == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        if (
            request.path.startswith("/rooms/")
            or request.path.startswith("/session/")
            or request.path.startswith("/inventory")
            or request.path.startswith("/chat/")
        ):
            response.headers.setdefault("Cache-Control", "no-store")

        if (
            request.path.startswith("/rooms/")
            or request.path.startswith("/session/")
            or request.path.startswith("/inventory")
            or request.path.startswith("/chat/")
        ):
            _emit_agent_debug(
                {
                    "sessionId": "9b5e82",
                    "runId": f"after-{getattr(g, 'session_id', 'no-session')}-{request.path}",
                    "hypothesisId": "H9",
                    "location": "backend.py:add_cors_headers",
                    "message": "prepared response headers for session-scoped endpoint",
                    "data": {
                        "request_path": request.path,
                        "session_id": getattr(g, "session_id", None),
                        "allowed_origin": response.headers.get("Access-Control-Allow-Origin"),
                        "allow_credentials": response.headers.get("Access-Control-Allow-Credentials"),
                        "has_set_cookie_header": response.headers.get("Set-Cookie") is not None,
                    },
                }
            )
        return response

    @app.route("/session/state", methods=["OPTIONS"])
    @app.route("/inventory", methods=["OPTIONS"])
    @app.route("/chat/stream", methods=["OPTIONS"])
    @app.route("/legal/privacy-notice", methods=["OPTIONS"])
    @app.route("/rooms/<string:room_name>/latest", methods=["OPTIONS"])
    @app.route("/rooms/<string:room_name>/states", methods=["OPTIONS"])
    @app.route("/rooms/states", methods=["OPTIONS"])
    @app.route("/session/reset", methods=["OPTIONS"])
    def options_handler(room_name: str | None = None) -> tuple[str, int]:
        return "", 204

    @app.get("/health")
    def health() -> tuple[object, int]:
        return jsonify({"status": "ok"}), 200

    @app.get("/session/state")
    def get_current_session_state() -> tuple[object, int]:
        session_id = _ensure_runtime_session(app)
        session_state_payload = get_session_state(app.config["DATABASE_PATH"], session_id)
        response = jsonify(session_state_payload or {"session_id": session_id, "current_room_name": "lobby"})
        return _attach_session_cookie(response, session_id, app), 200

    @app.get("/inventory")
    def get_current_inventory() -> tuple[object, int]:
        session_id = _ensure_runtime_session(app)
        inventory_items = list_inventory_items(app.config["DATABASE_PATH"], session_id)
        response = jsonify(inventory_items)
        return _attach_session_cookie(response, session_id, app), 200

    @app.post("/chat/stream")
    def stream_chat_turn() -> Response | tuple[object, int]:
        session_id = _ensure_runtime_session(app)
        if not _request_origin_is_allowed(app.config["FRONTEND_ORIGIN"]):
            logger.warning("Rejected chat stream from unexpected origin: %s", request.headers.get("Origin"))
            response = jsonify({"error": "Request origin is not allowed."})
            return _attach_session_cookie(response, session_id, app), 403

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            response = jsonify({"error": "Request body must be valid JSON."})
            return _attach_session_cookie(response, session_id, app), 400

        user_message = payload.get("message")
        if not isinstance(user_message, str) or not user_message.strip():
            response = jsonify({"error": "message is required and must be a non-empty string."})
            return _attach_session_cookie(response, session_id, app), 400

        from crew_coordinator import CrewCoordinator

        coordinator = CrewCoordinator(app.config["DATABASE_PATH"])

        def event_stream() -> Any:
            try:
                for stream_event in coordinator.stream_turn(session_id=session_id, user_message=user_message.strip()):
                    yield _sse_event(stream_event["type"], stream_event)
            except Exception as error:  # noqa: BLE001
                logger.exception("Chat stream failed for session %s", session_id)
                yield _sse_event(
                    "error",
                    {"type": "error", "message": str(error) or "The chat request could not be completed."},
                )

        response = Response(event_stream(), mimetype="text/event-stream")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Accel-Buffering"] = "no"
        return _attach_session_cookie(response, session_id, app)

    @app.get("/audio/opening-theme")
    def get_opening_theme() -> Response | tuple[object, int]:
        """Stream the committed opening theme used on the first screen."""
        audio_path = Path(app.config["OPENING_AUDIO_PATH"])
        if not audio_path.exists():
            logger.error("Opening audio file not found: %s", audio_path)
            return jsonify({"error": "Opening audio file is not available."}), 404

        return send_file(
            audio_path,
            mimetype="audio/mpeg",
            conditional=True,
            download_name=audio_path.name,
        )

    @app.get("/audio/intro")
    def get_intro_audio() -> Response | tuple[object, int]:
        """Stream the narrated intro played before the guest enters the hotel."""
        audio_path = Path(app.config["INTRO_AUDIO_PATH"])
        if not audio_path.exists():
            logger.error("Intro audio file not found: %s", audio_path)
            return jsonify({"error": "Intro audio file is not available."}), 404

        return send_file(
            audio_path,
            mimetype="audio/mpeg",
            conditional=True,
            download_name=audio_path.name,
        )

    @app.get("/legal/privacy-notice")
    def get_privacy_notice() -> Response | tuple[object, int]:
        """Return the plain-language prototype privacy notice used on the start screen."""
        notice_path = Path(app.config["PRIVACY_NOTICE_PATH"])
        if not notice_path.exists():
            logger.error("Privacy notice file not found: %s", notice_path)
            return jsonify({"error": "Privacy notice is not available."}), 404

        return send_file(
            notice_path,
            mimetype="text/markdown",
            conditional=True,
            download_name=notice_path.name,
        )

    @app.post("/rooms/states")
    def create_room_state_endpoint() -> tuple[object, int]:
        session_id = _ensure_runtime_session(app)
        if not _request_origin_is_allowed(app.config["FRONTEND_ORIGIN"]):
            logger.warning("Rejected room state write from unexpected origin: %s", request.headers.get("Origin"))
            response = jsonify({"error": "Request origin is not allowed."})
            return _attach_session_cookie(response, session_id, app), 403

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            response = jsonify({"error": "Request body must be valid JSON."})
            return _attach_session_cookie(response, session_id, app), 400

        try:
            room_state = validate_room_state_payload(payload)
        except ValueError as error:
            logger.error("Room state validation failed: %s", error)
            response = jsonify({"error": str(error)})
            return _attach_session_cookie(response, session_id, app), 400

        try:
            created_room_state = insert_room_state(app.config["DATABASE_PATH"], session_id, room_state)
        except ValueError as error:
            logger.error("Room state insert failed: %s", error)
            response = jsonify({"error": str(error)})
            return _attach_session_cookie(response, session_id, app), 400

        logger.info(
            "Stored room state for room '%s' in session %s",
            created_room_state["room_name"],
            session_id,
        )
        response = jsonify(created_room_state)
        return _attach_session_cookie(response, session_id, app), 201

    @app.post("/session/reset")
    def reset_session_progress_endpoint() -> tuple[object, int]:
        """Delete this visitor's room history and issue a fresh anonymous session."""
        session_id = _ensure_session_id()
        if not _request_origin_is_allowed(app.config["FRONTEND_ORIGIN"]):
            logger.warning("Rejected session reset from unexpected origin: %s", request.headers.get("Origin"))
            response = jsonify({"error": "Request origin is not allowed."})
            return _attach_session_cookie(response, session_id, app), 403

        reset_summary = clear_session_progress(app.config["DATABASE_PATH"], session_id)

        logger.info("Reset session %s and deleted scoped state: %s", session_id, reset_summary)
        response = jsonify({"status": "reset", **reset_summary})
        return _replace_session_cookie(response, app), 200

    @app.get("/rooms/<string:room_name>/states")
    def list_room_states_endpoint(room_name: str) -> tuple[object, int]:
        session_id = _ensure_runtime_session(app)
        include_images = request.args.get("include_images", "false").lower() == "true"
        room_states = fetch_room_states(app.config["DATABASE_PATH"], session_id, room_name, include_images)
        response = jsonify(room_states)
        return _attach_session_cookie(response, session_id, app), 200

    @app.get("/rooms/<string:room_name>/latest")
    def get_latest_room_state_endpoint(room_name: str) -> tuple[object, int]:
        session_id = _ensure_runtime_session(app)
        room_state = fetch_latest_room_state(app.config["DATABASE_PATH"], session_id, room_name)

        if room_state is None:
            response = jsonify({"error": f"No room states found for room '{room_name}' in this session."})
            return _attach_session_cookie(response, session_id, app), 404

        debug_payload = __import__("json").dumps(
            {
                "sessionId": "9b5e82",
                "runId": f"latest-{session_id}-{room_name}",
                "hypothesisId": "H6",
                "location": "backend.py:get_latest_room_state_endpoint",
                "message": "served latest room state",
                "data": {
                    "room_name": room_state["room_name"],
                    "state_id": room_state["id"],
                    "previous_state_id": room_state["previous_state_id"],
                    "image_media_type": room_state["image_media_type"],
                    "room_image_base64_length": len(room_state["room_image_base64"]),
                    "room_image_sha256": hashlib.sha256(room_state["room_image_base64"].encode("ascii")).hexdigest()[:16],
                },
            },
            separators=(",", ":"),
        )
        logger.info("AGENT_DEBUG %s", debug_payload)
        try:
            sys.stderr.write(f"AGENT_DEBUG {debug_payload}\n")
            sys.stderr.flush()
        except OSError:
            pass
        response = jsonify(room_state)
        return _attach_session_cookie(response, session_id, app), 200

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port_value = os.getenv("PORT") or os.getenv("BACKEND_PORT", "5000")
    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError("PORT or BACKEND_PORT must be an integer") from error

    app.run(host=host, port=port)
