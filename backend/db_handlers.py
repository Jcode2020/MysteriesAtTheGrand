import base64
import binascii
import json
import mimetypes
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEGACY_SESSION_ID = "legacy-default-session"
PERSISTENT_SESSION_ID = "persistent"
DEFAULT_CURRENT_ROOM_NAME = "lobby"


def current_timestamp() -> str:
    """Return a timezone-aware ISO-8601 timestamp for new rows."""
    return datetime.now(timezone.utc).isoformat()


def get_db_connection(database_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _guess_image_media_type(image_path: Path) -> str:
    """Infer an image MIME type from a committed asset path."""
    guessed_type, _ = mimetypes.guess_type(image_path.name)
    if guessed_type is None or not guessed_type.startswith("image/"):
        return "image/png"
    return guessed_type


def _resolve_seed_asset_path(asset_path_value: str, manifest_path: Path) -> Path:
    """Resolve one manifest asset path relative to the manifest file."""
    asset_path = Path(asset_path_value)
    if not asset_path.is_absolute():
        asset_path = (manifest_path.parent / asset_path).resolve()
    else:
        asset_path = asset_path.resolve()

    if not asset_path.exists():
        raise FileNotFoundError(f"Seed asset not found: {asset_path}")
    return asset_path


def _normalize_persistent_room_seed_entry(entry: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    """Validate and normalize one persistent room seed definition."""
    room_name = entry.get("room_name")
    if not isinstance(room_name, str) or not room_name.strip():
        raise ValueError("Each persistent room seed must include a non-empty room_name.")

    image_path_value = entry.get("image_path")
    if not isinstance(image_path_value, str) or not image_path_value.strip():
        raise ValueError(f"Persistent room seed '{room_name}' must include a non-empty image_path.")

    room_description = entry.get("room_description")
    if not isinstance(room_description, str) or not room_description.strip():
        raise ValueError(f"Persistent room seed '{room_name}' must include a non-empty room_description.")

    image_path = _resolve_seed_asset_path(image_path_value, manifest_path)
    image_media_type = entry.get("image_media_type")
    if image_media_type is None:
        image_media_type = _guess_image_media_type(image_path)
    elif not isinstance(image_media_type, str) or not image_media_type.startswith("image/"):
        raise ValueError(f"Persistent room seed '{room_name}' must use a valid image_media_type.")

    room_modifications = entry.get("room_modifications")
    if room_modifications is not None and not isinstance(room_modifications, str):
        raise ValueError(f"Persistent room seed '{room_name}' must use a string room_modifications value.")

    state_timestamp = entry.get("state_timestamp", current_timestamp())
    if not isinstance(state_timestamp, str) or not state_timestamp.strip():
        raise ValueError(f"Persistent room seed '{room_name}' must use a non-empty state_timestamp string.")

    return {
        "room_name": room_name.strip(),
        "image_path": image_path,
        "image_media_type": image_media_type.strip(),
        "room_modifications": room_modifications.strip() if isinstance(room_modifications, str) else None,
        "room_description": room_description.strip(),
        "state_timestamp": state_timestamp.strip(),
    }


def _normalize_inventory_seed_entry(entry: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    """Validate and normalize one starter inventory item definition."""
    item_key = entry.get("item_key")
    item_name = entry.get("item_name")
    item_detail = entry.get("item_detail")
    image_path_value = entry.get("image_path")

    if not isinstance(item_key, str) or not item_key.strip():
        raise ValueError("Each starter_inventory item must include a non-empty item_key.")
    if not isinstance(item_name, str) or not item_name.strip():
        raise ValueError(f"Starter inventory '{item_key}' must include a non-empty item_name.")
    if not isinstance(item_detail, str) or not item_detail.strip():
        raise ValueError(f"Starter inventory '{item_key}' must include a non-empty item_detail.")
    if not isinstance(image_path_value, str) or not image_path_value.strip():
        raise ValueError(f"Starter inventory '{item_key}' must include a non-empty image_path.")

    image_path = _resolve_seed_asset_path(image_path_value, manifest_path)
    image_media_type = entry.get("image_media_type")
    if image_media_type is None:
        image_media_type = _guess_image_media_type(image_path)
    elif not isinstance(image_media_type, str) or not image_media_type.startswith("image/"):
        raise ValueError(f"Starter inventory '{item_key}' must use a valid image_media_type.")

    return {
        "item_key": item_key.strip(),
        "item_name": item_name.strip(),
        "item_detail": item_detail.strip(),
        "image_path": image_path,
        "image_media_type": image_media_type.strip(),
    }


def load_seed_manifest(manifest_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load the committed persistent room and starter inventory seed definitions."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Persistent room seed manifest not found: {manifest_path}")

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_payload, dict):
        raise ValueError("Persistent room seed manifest must be a JSON object.")

    raw_room_entries = manifest_payload.get("persistent_rooms")
    if not isinstance(raw_room_entries, list) or not raw_room_entries:
        raise ValueError("Persistent room seed manifest must contain a non-empty persistent_rooms array.")

    raw_inventory_entries = manifest_payload.get("starter_inventory")
    if not isinstance(raw_inventory_entries, list) or not raw_inventory_entries:
        raise ValueError("Persistent room seed manifest must contain a non-empty starter_inventory array.")

    return {
        "persistent_rooms": [
            _normalize_persistent_room_seed_entry(entry, manifest_path)
            for entry in raw_room_entries
            if isinstance(entry, dict)
        ],
        "starter_inventory": [
            _normalize_inventory_seed_entry(entry, manifest_path)
            for entry in raw_inventory_entries
            if isinstance(entry, dict)
        ],
    }


def initialize_database(database_path: Path, schema_path: Path) -> None:
    """Create the SQLite database and run compatibility migrations."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")

    with get_db_connection(database_path) as connection:
        connection.executescript(schema_sql)
        _migrate_room_table_for_sessions(connection)
        _migrate_room_table_for_descriptions(connection)


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


def _migrate_room_table_for_descriptions(connection: sqlite3.Connection) -> None:
    """Backfill older SQLite databases that predate room descriptions."""
    column_rows = connection.execute("PRAGMA table_info(room_table)").fetchall()
    existing_columns = {row["name"] for row in column_rows}
    if "room_description" not in existing_columns:
        connection.execute("ALTER TABLE room_table ADD COLUMN room_description TEXT")


def seed_persistent_room_states(database_path: Path, seed_entries: list[dict[str, Any]]) -> None:
    """Insert missing persistent room base states from the committed manifest."""
    persistent_seed_query = "SELECT id FROM room_table WHERE session_id = ? AND room_name = ? LIMIT 1"
    insert_seed_query = """
        INSERT INTO room_table (
            session_id,
            room_name,
            room_image,
            image_media_type,
            room_modifications,
            room_description,
            state_timestamp,
            previous_state_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    with get_db_connection(database_path) as connection:
        for seed_entry in seed_entries:
            existing_room_state = connection.execute(
                persistent_seed_query,
                (PERSISTENT_SESSION_ID, seed_entry["room_name"]),
            ).fetchone()
            if existing_room_state is not None:
                connection.execute(
                    """
                    UPDATE room_table
                    SET room_description = ?,
                        room_modifications = COALESCE(room_modifications, ?)
                    WHERE id = ?
                    """,
                    (seed_entry["room_description"], seed_entry["room_modifications"], existing_room_state["id"]),
                )
                continue

            connection.execute(
                insert_seed_query,
                (
                    PERSISTENT_SESSION_ID,
                    seed_entry["room_name"],
                    seed_entry["image_path"].read_bytes(),
                    seed_entry["image_media_type"],
                    seed_entry["room_modifications"],
                    seed_entry["room_description"],
                    seed_entry["state_timestamp"],
                    None,
                ),
            )


def ensure_session_bootstrap(
    database_path: Path,
    session_id: str,
    starter_inventory: list[dict[str, Any]],
) -> None:
    """Ensure a visitor has a session row and the starter inventory."""
    if session_id == PERSISTENT_SESSION_ID:
        return

    now = current_timestamp()
    with get_db_connection(database_path) as connection:
        existing_session = connection.execute(
            "SELECT session_id FROM session_state WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if existing_session is None:
            connection.execute(
                """
                INSERT INTO session_state (session_id, current_room_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, DEFAULT_CURRENT_ROOM_NAME, now, now),
            )

        inventory_count_row = connection.execute(
            "SELECT COUNT(*) AS inventory_count FROM inventory_table WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        inventory_count = int(inventory_count_row["inventory_count"]) if inventory_count_row else 0
        if inventory_count == 0:
            for item in starter_inventory:
                connection.execute(
                    """
                    INSERT INTO inventory_table (
                        session_id,
                        item_key,
                        item_name,
                        item_detail,
                        item_image,
                        image_media_type,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        item["item_key"],
                        item["item_name"],
                        item["item_detail"],
                        item["image_path"].read_bytes(),
                        item["image_media_type"],
                        now,
                    ),
                )


def get_session_state(database_path: Path, session_id: str) -> dict[str, Any] | None:
    """Return the current session state row as a JSON-safe payload."""
    with get_db_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT session_id, current_room_name, created_at, updated_at
            FROM session_state
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        return None
    return dict(row)


def set_current_room_name(database_path: Path, session_id: str, room_name: str) -> None:
    """Update the active room name for one visitor session."""
    now = current_timestamp()
    with get_db_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE session_state
            SET current_room_name = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (room_name, now, session_id),
        )


def list_inventory_items(database_path: Path, session_id: str) -> list[dict[str, Any]]:
    """Return the current session inventory as JSON-safe payloads."""
    with get_db_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, item_key, item_name, item_detail, item_image, image_media_type, created_at
            FROM inventory_table
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "session_id": row["session_id"],
            "item_key": row["item_key"],
            "item_name": row["item_name"],
            "item_detail": row["item_detail"],
            "item_image_base64": base64.b64encode(row["item_image"]).decode("ascii"),
            "image_media_type": row["image_media_type"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_inventory_item(database_path: Path, session_id: str, item_key: str) -> dict[str, Any] | None:
    """Return one inventory item for the session."""
    with get_db_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, session_id, item_key, item_name, item_detail, item_image, image_media_type, created_at
            FROM inventory_table
            WHERE session_id = ? AND item_key = ?
            """,
            (session_id, item_key),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "item_key": row["item_key"],
        "item_name": row["item_name"],
        "item_detail": row["item_detail"],
        "item_image": row["item_image"],
        "image_media_type": row["image_media_type"],
        "created_at": row["created_at"],
    }


def list_available_room_names(database_path: Path, session_id: str) -> list[str]:
    """Return the room names visible to this session."""
    with get_db_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT room_name
            FROM room_table
            WHERE session_id IN (?, ?)
            ORDER BY room_name ASC
            """,
            (PERSISTENT_SESSION_ID, session_id),
        ).fetchall()
    return [str(row["room_name"]) for row in rows]


def upsert_crew_conversation(
    database_path: Path,
    session_id: str,
    openai_conversation_id: str | None,
    latest_response_id: str | None,
) -> dict[str, Any]:
    """Store the current OpenAI conversation pointers for one session."""
    now = current_timestamp()
    with get_db_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO crew_convos (
                session_id,
                openai_conversation_id,
                latest_response_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                openai_conversation_id = excluded.openai_conversation_id,
                latest_response_id = excluded.latest_response_id,
                updated_at = excluded.updated_at
            """,
            (session_id, openai_conversation_id, latest_response_id, now, now),
        )
        row = connection.execute(
            """
            SELECT session_id, openai_conversation_id, latest_response_id, created_at, updated_at
            FROM crew_convos
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    return dict(row) if row is not None else {}


def get_crew_conversation(database_path: Path, session_id: str) -> dict[str, Any] | None:
    """Fetch the stored OpenAI conversation pointers for one session."""
    with get_db_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT session_id, openai_conversation_id, latest_response_id, created_at, updated_at
            FROM crew_convos
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def reset_session_progress(database_path: Path, session_id: str) -> dict[str, int]:
    """Delete visitor-scoped state across all runtime tables."""
    with get_db_connection(database_path) as connection:
        room_delete_cursor = connection.execute(
            """
            DELETE FROM room_table
            WHERE session_id = ? AND session_id != ?
            """,
            (session_id, PERSISTENT_SESSION_ID),
        )
        inventory_delete_cursor = connection.execute(
            "DELETE FROM inventory_table WHERE session_id = ?",
            (session_id,),
        )
        crew_convo_delete_cursor = connection.execute(
            "DELETE FROM crew_convos WHERE session_id = ?",
            (session_id,),
        )
        session_delete_cursor = connection.execute(
            "DELETE FROM session_state WHERE session_id = ?",
            (session_id,),
        )

    return {
        "deleted_room_states": room_delete_cursor.rowcount if room_delete_cursor.rowcount >= 0 else 0,
        "deleted_inventory_items": inventory_delete_cursor.rowcount if inventory_delete_cursor.rowcount >= 0 else 0,
        "deleted_crew_convos": crew_convo_delete_cursor.rowcount if crew_convo_delete_cursor.rowcount >= 0 else 0,
        "deleted_session_rows": session_delete_cursor.rowcount if session_delete_cursor.rowcount >= 0 else 0,
    }


def decode_image_payload(room_image_base64: str) -> bytes:
    """Decode a base64 image payload and fail fast on malformed input."""
    try:
        return base64.b64decode(room_image_base64, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("room_image_base64 must be valid base64 data") from error


def serialize_room_state(row: sqlite3.Row, include_image: bool) -> dict[str, Any]:
    """Convert a SQLite row into a JSON-safe room-state payload."""
    payload: dict[str, Any] = {
        "id": row["id"],
        "session_id": row["session_id"],
        "room_name": row["room_name"],
        "image_media_type": row["image_media_type"],
        "room_modifications": row["room_modifications"],
        "room_description": row["room_description"],
        "state_timestamp": row["state_timestamp"],
        "previous_state_id": row["previous_state_id"],
    }

    if include_image:
        payload["room_image_base64"] = base64.b64encode(row["room_image"]).decode("ascii")

    return payload


def validate_room_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
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

    room_description = payload.get("room_description")
    if room_description is not None and not isinstance(room_description, str):
        raise ValueError("room_description must be a string when provided")

    state_timestamp = payload.get("state_timestamp", current_timestamp())
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
        "room_image": decode_image_payload(room_image_base64),
        "room_modifications": room_modifications.strip() if isinstance(room_modifications, str) else None,
        "room_description": room_description.strip() if isinstance(room_description, str) else None,
        "state_timestamp": state_timestamp.strip(),
        "previous_state_id": previous_state_id,
        "image_media_type": image_media_type.strip(),
    }


def previous_state_belongs_to_session(
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


def room_query(session_id: str, room_name: str, latest_only: bool) -> tuple[str, tuple[Any, ...]]:
    """Build the query used to merge a persistent room base with session-specific states."""
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


def create_room_state(database_path: Path, session_id: str, room_state: dict[str, Any]) -> dict[str, Any]:
    """Insert one room snapshot for the session and return the created row."""
    insert_sql = """
        INSERT INTO room_table (
            session_id,
            room_name,
            room_image,
            image_media_type,
            room_modifications,
            room_description,
            state_timestamp,
            previous_state_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    with get_db_connection(database_path) as connection:
        if not previous_state_belongs_to_session(connection, session_id, room_state["previous_state_id"]):
            raise ValueError("previous_state_id must reference an existing room state in this session.")

        cursor = connection.execute(
            insert_sql,
            (
                session_id,
                room_state["room_name"],
                room_state["room_image"],
                room_state["image_media_type"],
                room_state["room_modifications"],
                room_state["room_description"],
                room_state["state_timestamp"],
                room_state["previous_state_id"],
            ),
        )
        row = connection.execute("SELECT * FROM room_table WHERE id = ?", (cursor.lastrowid,)).fetchone()

    if row is None:
        raise RuntimeError("Could not fetch the room state that was just created.")
    return serialize_room_state(row, include_image=True)


def get_latest_room_state_record(database_path: Path, session_id: str, room_name: str) -> dict[str, Any] | None:
    """Return the latest room snapshot with raw image bytes for internal services."""
    query, query_params = room_query(session_id, room_name, latest_only=True)
    with get_db_connection(database_path) as connection:
        row = connection.execute(query, query_params).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "room_name": row["room_name"],
        "room_image": row["room_image"],
        "image_media_type": row["image_media_type"],
        "room_modifications": row["room_modifications"],
        "room_description": row["room_description"],
        "state_timestamp": row["state_timestamp"],
        "previous_state_id": row["previous_state_id"],
    }


def list_room_states(database_path: Path, session_id: str, room_name: str, include_images: bool) -> list[dict[str, Any]]:
    """Return the room timeline merged with the persistent base state."""
    query, query_params = room_query(session_id, room_name, latest_only=False)
    with get_db_connection(database_path) as connection:
        rows = connection.execute(query, query_params).fetchall()
    return [serialize_room_state(row, include_images) for row in rows]


def get_latest_room_state(database_path: Path, session_id: str, room_name: str) -> dict[str, Any] | None:
    """Return the latest room snapshot merged with the persistent base state."""
    query, query_params = room_query(session_id, room_name, latest_only=True)
    with get_db_connection(database_path) as connection:
        row = connection.execute(query, query_params).fetchone()
    if row is None:
        return None
    return serialize_room_state(row, include_image=True)


def remove_inventory_item_and_create_room_state(
    database_path: Path,
    session_id: str,
    consumed_item_key: str | None,
    room_state: dict[str, Any],
    current_room_name: str | None = None,
) -> dict[str, Any]:
    """Commit an inventory removal and room-state write in one transaction."""
    insert_sql = """
        INSERT INTO room_table (
            session_id,
            room_name,
            room_image,
            image_media_type,
            room_modifications,
            room_description,
            state_timestamp,
            previous_state_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    with get_db_connection(database_path) as connection:
        if consumed_item_key is not None:
            inventory_row = connection.execute(
                """
                SELECT id
                FROM inventory_table
                WHERE session_id = ? AND item_key = ?
                """,
                (session_id, consumed_item_key),
            ).fetchone()
            if inventory_row is None:
                raise ValueError(f"Inventory item '{consumed_item_key}' is not available in this session.")

        if not previous_state_belongs_to_session(connection, session_id, room_state["previous_state_id"]):
            raise ValueError("previous_state_id must reference an existing room state in this session.")

        cursor = connection.execute(
            insert_sql,
            (
                session_id,
                room_state["room_name"],
                room_state["room_image"],
                room_state["image_media_type"],
                room_state["room_modifications"],
                room_state["room_description"],
                room_state["state_timestamp"],
                room_state["previous_state_id"],
            ),
        )

        if consumed_item_key is not None:
            connection.execute(
                "DELETE FROM inventory_table WHERE session_id = ? AND item_key = ?",
                (session_id, consumed_item_key),
            )

        if current_room_name is not None:
            connection.execute(
                """
                UPDATE session_state
                SET current_room_name = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (current_room_name, current_timestamp(), session_id),
            )

        row = connection.execute("SELECT * FROM room_table WHERE id = ?", (cursor.lastrowid,)).fetchone()

    if row is None:
        raise RuntimeError("Could not fetch the room state that was just created.")
    return serialize_room_state(row, include_image=True)
