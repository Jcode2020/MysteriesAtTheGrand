import base64
import binascii
import json
import logging
import mimetypes
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, Response, g, jsonify, request, send_file

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT_DIR = BACKEND_DIR.parent
DEFAULT_DATABASE_PATH = REPO_ROOT_DIR / "db" / "hotel_db.sqlite3"
DEFAULT_SCHEMA_PATH = BACKEND_DIR / "schema.sql"
DEFAULT_PERSISTENT_ROOM_SEED_MANIFEST_PATH = BACKEND_DIR / "seed" / "persistent" / "manifest.json"
DEFAULT_OPENING_AUDIO_PATH = BACKEND_DIR / "static" / "audio" / "Secrets_of_the_Grand_Pannonia_2026-03-21T133239.mp3"
SESSION_COOKIE_NAME = "grand_pannonia_session_id"
LEGACY_SESSION_ID = "legacy-default-session"
PERSISTENT_SESSION_ID = "persistent"

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Set up a simple backend logger for startup and database events."""
    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(message)s",
    )


def _resolve_database_path(database_path: str | Path | None = None) -> Path:
    """Resolve the SQLite database path from the argument or environment."""
    if database_path is not None:
        return Path(database_path).expanduser().resolve()

    room_db_path = os.getenv("ROOM_DB_PATH")
    if room_db_path:
        return Path(room_db_path).expanduser().resolve()

    return DEFAULT_DATABASE_PATH


def _get_db_connection(database_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


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


def _initialize_database(database_path: Path, schema_path: Path) -> None:
    """Create the SQLite database and `room_table` schema if missing."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")

    with _get_db_connection(database_path) as connection:
        connection.executescript(schema_sql)
        _migrate_room_table_for_sessions(connection)

    logger.info("Initialized room state database at %s", database_path)


def _migrate_room_table_for_sessions(connection: sqlite3.Connection) -> None:
    """Backfill older SQLite databases that predate session-scoped room state."""
    column_rows = connection.execute("PRAGMA table_info(room_table)").fetchall()
    existing_columns = {row["name"] for row in column_rows}

    if "session_id" not in existing_columns:
        connection.execute("ALTER TABLE room_table ADD COLUMN session_id TEXT")
        connection.execute(
            "UPDATE room_table SET session_id = ? WHERE session_id IS NULL",
            (LEGACY_SESSION_ID,),
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_room_table_session_id_room_name_state_timestamp
            ON room_table (session_id, room_name, state_timestamp)
            """
        )

    connection.execute(
        "UPDATE room_table SET session_id = ? WHERE session_id IS NULL OR TRIM(session_id) = ''",
        (LEGACY_SESSION_ID,),
    )
    room_names = [
        row["room_name"]
        for row in connection.execute("SELECT DISTINCT room_name FROM room_table").fetchall()
    ]
    for room_name in room_names:
        persistent_row = connection.execute(
            "SELECT id FROM room_table WHERE room_name = ? AND session_id = ? LIMIT 1",
            (room_name, PERSISTENT_SESSION_ID),
        ).fetchone()
        if persistent_row is not None:
            continue

        connection.execute(
            """
            UPDATE room_table
            SET session_id = ?
            WHERE id = (
                SELECT id
                FROM room_table
                WHERE room_name = ?
                ORDER BY state_timestamp ASC, id ASC
                LIMIT 1
            )
            """,
            (PERSISTENT_SESSION_ID, room_name),
        )


def _guess_image_media_type(image_path: Path) -> str:
    """Infer the MIME type from the seeded asset path."""
    guessed_type, _ = mimetypes.guess_type(image_path.name)
    if guessed_type is None or not guessed_type.startswith("image/"):
        return "image/png"

    return guessed_type


def _normalize_persistent_seed_entry(entry: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    """Validate one manifest entry and resolve its image path."""
    room_name = entry.get("room_name")
    if not isinstance(room_name, str) or not room_name.strip():
        raise ValueError("Each persistent room seed must include a non-empty room_name.")

    image_path_value = entry.get("image_path")
    if not isinstance(image_path_value, str) or not image_path_value.strip():
        raise ValueError(f"Persistent room seed '{room_name}' must include a non-empty image_path.")

    image_path = Path(image_path_value)
    if not image_path.is_absolute():
        image_path = (manifest_path.parent / image_path).resolve()
    else:
        image_path = image_path.resolve()

    if not image_path.exists():
        raise FileNotFoundError(f"Persistent room seed image not found: {image_path}")

    image_media_type = entry.get("image_media_type")
    if image_media_type is None:
        image_media_type = _guess_image_media_type(image_path)
    elif not isinstance(image_media_type, str) or not image_media_type.startswith("image/"):
        raise ValueError(f"Persistent room seed '{room_name}' must use a valid image_media_type.")

    room_modifications = entry.get("room_modifications")
    if room_modifications is not None and not isinstance(room_modifications, str):
        raise ValueError(f"Persistent room seed '{room_name}' must use a string room_modifications value.")

    state_timestamp = entry.get("state_timestamp", _current_timestamp())
    if not isinstance(state_timestamp, str) or not state_timestamp.strip():
        raise ValueError(f"Persistent room seed '{room_name}' must use a non-empty state_timestamp string.")

    return {
        "room_name": room_name.strip(),
        "image_path": image_path,
        "image_media_type": image_media_type.strip(),
        "room_modifications": room_modifications.strip() if isinstance(room_modifications, str) else None,
        "state_timestamp": state_timestamp.strip(),
    }


def _load_persistent_room_seed_entries(manifest_path: Path) -> list[dict[str, Any]]:
    """Load and validate committed persistent room seed definitions."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Persistent room seed manifest not found: {manifest_path}")

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_payload, dict):
        raise ValueError("Persistent room seed manifest must be a JSON object.")

    raw_entries = manifest_payload.get("persistent_rooms")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("Persistent room seed manifest must contain a non-empty persistent_rooms array.")

    normalized_entries: list[dict[str, Any]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("Each persistent room seed entry must be a JSON object.")
        normalized_entries.append(_normalize_persistent_seed_entry(raw_entry, manifest_path))

    return normalized_entries


def _seed_persistent_room_states(database_path: Path, seed_entries: list[dict[str, Any]]) -> None:
    """Insert missing persistent room base states from the committed manifest."""
    persistent_seed_query = "SELECT id FROM room_table WHERE session_id = ? AND room_name = ? LIMIT 1"
    insert_seed_query = """
        INSERT INTO room_table (
            session_id,
            room_name,
            room_image,
            image_media_type,
            room_modifications,
            state_timestamp,
            previous_state_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    with _get_db_connection(database_path) as connection:
        for seed_entry in seed_entries:
            existing_room_state = connection.execute(
                persistent_seed_query,
                (PERSISTENT_SESSION_ID, seed_entry["room_name"]),
            ).fetchone()
            if existing_room_state is not None:
                continue

            connection.execute(
                insert_seed_query,
                (
                    PERSISTENT_SESSION_ID,
                    seed_entry["room_name"],
                    seed_entry["image_path"].read_bytes(),
                    seed_entry["image_media_type"],
                    seed_entry["room_modifications"],
                    seed_entry["state_timestamp"],
                    None,
                ),
            )
            logger.info(
                "Seeded persistent room '%s' from %s",
                seed_entry["room_name"],
                seed_entry["image_path"],
            )


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
    """Use secure cookies when explicitly enabled for HTTPS deployments."""
    return os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


def _resolve_session_cookie_samesite() -> str:
    """Resolve the SameSite policy for the anonymous session cookie."""
    configured_value = os.getenv("SESSION_COOKIE_SAMESITE", "Lax").strip().capitalize()
    if configured_value not in {"Lax", "Strict", "None"}:
        raise ValueError("SESSION_COOKIE_SAMESITE must be one of: Lax, Strict, None")
    return configured_value


def _current_timestamp() -> str:
    """Return a timezone-aware ISO-8601 timestamp for new room states."""
    return datetime.now(timezone.utc).isoformat()


def _decode_image_payload(room_image_base64: str) -> bytes:
    """Decode a base64 image payload and fail fast on malformed input."""
    try:
        return base64.b64decode(room_image_base64, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("room_image_base64 must be valid base64 data") from error


def _serialize_room_state(row: sqlite3.Row, include_image: bool) -> dict[str, Any]:
    """Convert a SQLite row into a JSON-safe room-state payload."""
    payload: dict[str, Any] = {
        "id": row["id"],
        "session_id": row["session_id"],
        "room_name": row["room_name"],
        "image_media_type": row["image_media_type"],
        "room_modifications": row["room_modifications"],
        "state_timestamp": row["state_timestamp"],
        "previous_state_id": row["previous_state_id"],
    }

    if include_image:
        payload["room_image_base64"] = base64.b64encode(row["room_image"]).decode("ascii")

    return payload


def _validate_room_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize incoming JSON before writing to SQLite."""
    room_name = payload.get("room_name")
    if not isinstance(room_name, str) or not room_name.strip():
        raise ValueError("room_name is required and must be a non-empty string")

    room_image_base64 = payload.get("room_image_base64")
    if not isinstance(room_image_base64, str) or not room_image_base64.strip():
        raise ValueError("room_image_base64 is required and must be a non-empty string")

    room_modifications = payload.get("room_modifications")
    if room_modifications is not None and not isinstance(room_modifications, str):
        raise ValueError("room_modifications must be a string when provided")

    state_timestamp = payload.get("state_timestamp", _current_timestamp())
    if not isinstance(state_timestamp, str) or not state_timestamp.strip():
        raise ValueError("state_timestamp must be a non-empty ISO-8601 string")

    previous_state_id = payload.get("previous_state_id")
    if previous_state_id is not None and not isinstance(previous_state_id, int):
        raise ValueError("previous_state_id must be an integer when provided")

    image_media_type = payload.get("image_media_type", "image/png")
    if not isinstance(image_media_type, str) or not image_media_type.startswith("image/"):
        raise ValueError("image_media_type must be an image/* MIME type")

    return {
        "room_name": room_name.strip(),
        "room_image": _decode_image_payload(room_image_base64),
        "room_modifications": room_modifications.strip() if isinstance(room_modifications, str) else None,
        "state_timestamp": state_timestamp.strip(),
        "previous_state_id": previous_state_id,
        "image_media_type": image_media_type.strip(),
    }


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
        return existing_session_id

    new_session_id = _generate_session_id()
    g.should_set_session_cookie = True
    g.session_id = new_session_id
    return new_session_id


def _attach_session_cookie(response: Response, session_id: str, app: Flask) -> Response:
    """Persist the anonymous session cookie for future room-state requests."""
    if getattr(g, "should_set_session_cookie", False):
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session_id,
            httponly=True,
            samesite=app.config["SESSION_COOKIE_SAMESITE"],
            secure=app.config["SESSION_COOKIE_SECURE"],
            max_age=60 * 60 * 24 * 30,
        )
    return response


def _previous_state_belongs_to_session(
    connection: sqlite3.Connection,
    session_id: str,
    previous_state_id: int | None,
) -> bool:
    """Ensure a room state can only chain to an earlier state from this session or the persistent base."""
    if previous_state_id is None:
        return True

    row = connection.execute(
        "SELECT 1 FROM room_table WHERE id = ? AND session_id IN (?, ?)",
        (previous_state_id, session_id, PERSISTENT_SESSION_ID),
    ).fetchone()
    return row is not None


def _room_query(room_name: str, latest_only: bool) -> tuple[str, tuple[Any, ...]]:
    """Build the query used to merge a persistent room base with session-specific states."""
    session_id = _ensure_session_id()

    if latest_only:
        query = """
            SELECT *
            FROM room_table
            WHERE session_id IN (?, ?) AND room_name = ?
            ORDER BY
                CASE WHEN session_id = ? THEN 0 ELSE 1 END ASC,
                state_timestamp DESC,
                id DESC
            LIMIT 1
        """
        return query, (PERSISTENT_SESSION_ID, session_id, room_name, session_id)

    query = """
        SELECT *
        FROM room_table
        WHERE session_id IN (?, ?) AND room_name = ?
        ORDER BY
            CASE WHEN session_id = ? THEN 0 ELSE 1 END ASC,
            state_timestamp ASC,
            id ASC
    """
    return query, (PERSISTENT_SESSION_ID, session_id, room_name, session_id)


def create_app(
    database_path: str | Path | None = None,
    schema_path: str | Path | None = None,
    seed_manifest_path: str | Path | None = None,
    opening_audio_path: str | Path | None = None,
) -> Flask:
    """Create the Flask app and wire it to the SQLite room-state database."""
    _configure_logging()

    app = Flask(__name__)
    resolved_database_path = _resolve_database_path(database_path)
    resolved_schema_path = _resolve_schema_path(schema_path)
    resolved_seed_manifest_path = _resolve_seed_manifest_path(seed_manifest_path)
    resolved_opening_audio_path = _resolve_opening_audio_path(opening_audio_path)
    seed_entries = _load_persistent_room_seed_entries(resolved_seed_manifest_path)
    app.config["DATABASE_PATH"] = resolved_database_path
    app.config["SCHEMA_PATH"] = resolved_schema_path
    app.config["FRONTEND_ORIGIN"] = _resolve_frontend_origin()
    app.config["OPENING_AUDIO_PATH"] = resolved_opening_audio_path
    app.config["SESSION_COOKIE_SECURE"] = _resolve_session_cookie_secure()
    app.config["SESSION_COOKIE_SAMESITE"] = _resolve_session_cookie_samesite()
    app.config["PERSISTENT_ROOM_SEED_MANIFEST_PATH"] = resolved_seed_manifest_path

    if app.config["SESSION_COOKIE_SAMESITE"] == "None" and not app.config["SESSION_COOKIE_SECURE"]:
        raise ValueError("SESSION_COOKIE_SAMESITE=None requires SESSION_COOKIE_SECURE=true")

    _initialize_database(resolved_database_path, resolved_schema_path)
    _seed_persistent_room_states(resolved_database_path, seed_entries)

    @app.after_request
    def add_cors_headers(response: Any) -> Any:
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

        if request.path.startswith("/rooms/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.route("/rooms/<string:room_name>/latest", methods=["OPTIONS"])
    @app.route("/rooms/<string:room_name>/states", methods=["OPTIONS"])
    @app.route("/rooms/states", methods=["OPTIONS"])
    def options_handler(room_name: str | None = None) -> tuple[str, int]:
        return "", 204

    @app.get("/health")
    def health() -> tuple[object, int]:
        return jsonify({"status": "ok"}), 200

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

    @app.post("/rooms/states")
    def create_room_state() -> tuple[object, int]:
        session_id = _ensure_session_id()
        if not _request_origin_is_allowed(app.config["FRONTEND_ORIGIN"]):
            logger.warning("Rejected room state write from unexpected origin: %s", request.headers.get("Origin"))
            response = jsonify({"error": "Request origin is not allowed."})
            return _attach_session_cookie(response, session_id, app), 403

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            response = jsonify({"error": "Request body must be valid JSON."})
            return _attach_session_cookie(response, session_id, app), 400

        try:
            room_state = _validate_room_state_payload(payload)
        except ValueError as error:
            logger.error("Room state validation failed: %s", error)
            response = jsonify({"error": str(error)})
            return _attach_session_cookie(response, session_id, app), 400

        insert_sql = """
            INSERT INTO room_table (
                session_id,
                room_name,
                room_image,
                image_media_type,
                room_modifications,
                state_timestamp,
                previous_state_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        select_sql = "SELECT * FROM room_table WHERE id = ?"

        try:
            with _get_db_connection(app.config["DATABASE_PATH"]) as connection:
                if not _previous_state_belongs_to_session(
                    connection,
                    session_id,
                    room_state["previous_state_id"],
                ):
                    response = jsonify(
                        {"error": "previous_state_id must reference an existing room state in this session."}
                    )
                    return _attach_session_cookie(response, session_id, app), 400

                cursor = connection.execute(
                    insert_sql,
                    (
                        session_id,
                        room_state["room_name"],
                        room_state["room_image"],
                        room_state["image_media_type"],
                        room_state["room_modifications"],
                        room_state["state_timestamp"],
                        room_state["previous_state_id"],
                    ),
                )
                new_state_id = cursor.lastrowid
                created_row = connection.execute(select_sql, (new_state_id,)).fetchone()
        except sqlite3.IntegrityError as error:
            logger.error("Room state insert failed: %s", error)
            response = jsonify({"error": "previous_state_id does not reference an existing room state."})
            return _attach_session_cookie(response, session_id, app), 400

        logger.info(
            "Stored room state %s for room '%s' in session %s",
            new_state_id,
            room_state["room_name"],
            session_id,
        )
        response = jsonify(_serialize_room_state(created_row, include_image=True))
        return _attach_session_cookie(response, session_id, app), 201

    @app.get("/rooms/<string:room_name>/states")
    def list_room_states(room_name: str) -> tuple[object, int]:
        session_id = _ensure_session_id()
        include_images = request.args.get("include_images", "false").lower() == "true"
        query, query_params = _room_query(room_name, latest_only=False)

        with _get_db_connection(app.config["DATABASE_PATH"]) as connection:
            rows = connection.execute(query, query_params).fetchall()

        response = jsonify([_serialize_room_state(row, include_images) for row in rows])
        return _attach_session_cookie(response, session_id, app), 200

    @app.get("/rooms/<string:room_name>/latest")
    def get_latest_room_state(room_name: str) -> tuple[object, int]:
        session_id = _ensure_session_id()
        query, query_params = _room_query(room_name, latest_only=True)

        with _get_db_connection(app.config["DATABASE_PATH"]) as connection:
            row = connection.execute(query, query_params).fetchone()

        if row is None:
            response = jsonify({"error": f"No room states found for room '{room_name}' in this session."})
            return _attach_session_cookie(response, session_id, app), 404

        response = jsonify(_serialize_room_state(row, include_image=True))
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
