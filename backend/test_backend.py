import base64
import json
import logging
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import backend as backend_module
from backend import create_app
from db_handlers import get_crew_conversation, upsert_crew_conversation

ONE_PIXEL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAusB9Y9nX4QAAAAASUVORK5CYII="
)
OPENING_AUDIO_BYTES = b"ID3test-opening-theme"
INTRO_AUDIO_BYTES = b"ID3test-intro-audio"


class BackendApiTests(unittest.TestCase):
    """Exercise the expanded SQLite-backed backend API surface end to end."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test_hotel_db.sqlite3"
        self.opening_audio_path = Path(self.temp_dir.name) / "opening-theme.mp3"
        self.intro_audio_path = Path(self.temp_dir.name) / "intro.mp3"
        self.privacy_notice_path = Path(self.temp_dir.name) / "privacy-notice.md"
        self.opening_audio_path.write_bytes(OPENING_AUDIO_BYTES)
        self.intro_audio_path.write_bytes(INTRO_AUDIO_BYTES)
        self.privacy_notice_path.write_text("# Test Notice\n\nPrototype only.", encoding="utf-8")
        self.seed_manifest_path = self._write_seed_manifest()
        self.app = create_app(
            database_path=self.database_path,
            seed_manifest_path=self.seed_manifest_path,
            opening_audio_path=self.opening_audio_path,
            intro_audio_path=self.intro_audio_path,
            privacy_notice_path=self.privacy_notice_path,
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _reset_backend_logger(self) -> None:
        """Remove the named backend handlers so each logging test starts cleanly."""
        for handler_name in [backend_module.STREAM_HANDLER_NAME, backend_module.FILE_HANDLER_NAME]:
            handler = backend_module._get_logger_handler(handler_name)
            if handler is None:
                continue
            backend_module.logger.removeHandler(handler)
            handler.close()
        backend_module._ACTIVE_LOG_FILE_PATH = None

    def _write_seed_manifest(self) -> Path:
        seed_root = Path(self.temp_dir.name) / "seed"
        images_dir = seed_root / "images"
        inventory_dir = seed_root / "inventory"
        images_dir.mkdir(parents=True, exist_ok=True)
        inventory_dir.mkdir(parents=True, exist_ok=True)

        (images_dir / "lobby.png").write_bytes(base64.b64decode(ONE_PIXEL_PNG_BASE64))
        for item_name in ["pen", "book", "contract", "cash", "teddy", "watch", "scarf"]:
            (inventory_dir / f"{item_name}.png").write_bytes(base64.b64decode(ONE_PIXEL_PNG_BASE64))

        manifest_path = seed_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "persistent_rooms": [
                        {
                            "room_name": "lobby",
                            "image_path": "images/lobby.png",
                            "image_media_type": "image/png",
                            "room_modifications": None,
                            "room_description": "A warm hotel lobby with a staircase and reception desk.",
                            "state_timestamp": "1900-01-01T00:00:00+00:00",
                        }
                    ],
                    "starter_inventory": [
                        {
                            "item_key": "pen",
                            "item_name": "Pen",
                            "item_detail": "Reception Desk",
                            "image_path": "inventory/pen.png",
                            "image_media_type": "image/png",
                        },
                        {
                            "item_key": "book",
                            "item_name": "Book",
                            "item_detail": "Guest Library",
                            "image_path": "inventory/book.png",
                            "image_media_type": "image/png",
                        },
                        {
                            "item_key": "contract",
                            "item_name": "Contract",
                            "item_detail": "Signed Copy",
                            "image_path": "inventory/contract.png",
                            "image_media_type": "image/png",
                        },
                        {
                            "item_key": "cash",
                            "item_name": "Cash",
                            "item_detail": "Tucked Away",
                            "image_path": "inventory/cash.png",
                            "image_media_type": "image/png",
                        },
                        {
                            "item_key": "teddy",
                            "item_name": "Teddy",
                            "item_detail": "Nursery Find",
                            "image_path": "inventory/teddy.png",
                            "image_media_type": "image/png",
                        },
                        {
                            "item_key": "watch",
                            "item_name": "Watch",
                            "item_detail": "Pocket Piece",
                            "image_path": "inventory/watch.png",
                            "image_media_type": "image/png",
                        },
                        {
                            "item_key": "scarf",
                            "item_name": "Scarf",
                            "item_detail": "Velvet Clue",
                            "image_path": "inventory/scarf.png",
                            "image_media_type": "image/png",
                        },
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return manifest_path

    def _fetch_first_runtime_session_id(self) -> str:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT session_id FROM session_state ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        return str(row[0])

    def test_lobby_seed_is_shared_persistent_base_with_description(self) -> None:
        first_client = self.app.test_client()
        second_client = self.app.test_client()

        first_response = first_client.get("/rooms/lobby/latest")
        second_response = second_client.get("/rooms/lobby/latest")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        first_state = first_response.get_json()
        second_state = second_response.get_json()

        self.assertEqual(first_state["session_id"], "persistent")
        self.assertEqual(second_state["session_id"], "persistent")
        self.assertEqual(first_state["room_description"], "A warm hotel lobby with a staircase and reception desk.")

    def test_session_bootstrap_exposes_current_room_and_inventory(self) -> None:
        session_response = self.client.get("/session/state")
        inventory_response = self.client.get("/inventory")

        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(inventory_response.status_code, 200)
        self.assertEqual(session_response.get_json()["current_room_name"], "lobby")
        self.assertEqual(len(inventory_response.get_json()), 7)
        self.assertEqual(inventory_response.get_json()[-1]["item_key"], "scarf")

    def test_opening_theme_streams_the_committed_audio_file(self) -> None:
        response = self.client.get("/audio/opening-theme")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/mpeg")
        self.assertEqual(response.data, OPENING_AUDIO_BYTES)

    def test_intro_audio_streams_the_committed_audio_file(self) -> None:
        response = self.client.get("/audio/intro")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/mpeg")
        self.assertEqual(response.data, INTRO_AUDIO_BYTES)

    def test_privacy_notice_streams_markdown(self) -> None:
        response = self.client.get("/legal/privacy-notice")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/markdown")
        self.assertIn("Prototype only", response.get_data(as_text=True))

    def test_create_room_state_persists_room_description(self) -> None:
        lobby_response = self.client.get("/rooms/lobby/latest")
        persistent_lobby_state = lobby_response.get_json()

        create_response = self.client.post(
            "/rooms/states",
            json={
                "room_name": "lobby",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "a note appears beside the ledger",
                "room_description": "A warm hotel lobby with a staircase, reception desk, and a note beside the ledger.",
                "state_timestamp": "2026-03-21T12:00:00+00:00",
                "previous_state_id": persistent_lobby_state["id"],
            },
        )

        self.assertEqual(create_response.status_code, 201)
        created_state = create_response.get_json()
        self.assertEqual(
            created_state["room_description"],
            "A warm hotel lobby with a staircase, reception desk, and a note beside the ledger.",
        )

        latest_response = self.client.get("/rooms/lobby/latest")
        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(latest_response.get_json()["id"], created_state["id"])

    def test_different_sessions_do_not_share_runtime_room_history(self) -> None:
        first_client = self.app.test_client()
        second_client = self.app.test_client()

        first_client.get("/session/state")
        second_client.get("/session/state")
        create_response = first_client.post(
            "/rooms/states",
            json={
                "room_name": "suite",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "the curtains are drawn",
                "room_description": "A suite with closed curtains.",
                "state_timestamp": "2026-03-21T13:00:00+00:00",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        self.assertEqual(len(first_client.get("/rooms/suite/states").get_json()), 1)
        self.assertEqual(second_client.get("/rooms/suite/states").get_json(), [])

    def test_reset_clears_all_session_scoped_state(self) -> None:
        self.client.get("/session/state")
        session_id = self._fetch_first_runtime_session_id()
        self.client.post(
            "/rooms/states",
            json={
                "room_name": "suite",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "a lamp is lit",
                "room_description": "A suite with a lit lamp.",
                "state_timestamp": "2026-03-21T12:05:00+00:00",
            },
        )
        upsert_crew_conversation(self.database_path, session_id, "conv_test", "resp_test")

        reset_response = self.client.post("/session/reset")

        self.assertEqual(reset_response.status_code, 200)
        reset_payload = reset_response.get_json()
        self.assertEqual(reset_payload["deleted_room_states"], 1)
        self.assertEqual(reset_payload["deleted_inventory_items"], 7)
        self.assertEqual(reset_payload["deleted_crew_convos"], 1)
        self.assertEqual(reset_payload["deleted_session_rows"], 1)
        self.assertIsNone(get_crew_conversation(self.database_path, session_id))

        with sqlite3.connect(self.database_path) as connection:
            remaining_inventory = connection.execute(
                "SELECT COUNT(*) FROM inventory_table WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            remaining_room_rows = connection.execute(
                "SELECT COUNT(*) FROM room_table WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            remaining_session_rows = connection.execute(
                "SELECT COUNT(*) FROM session_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]

        self.assertEqual(remaining_inventory, 0)
        self.assertEqual(remaining_room_rows, 0)
        self.assertEqual(remaining_session_rows, 0)

    @patch("crew_coordinator.CrewCoordinator.stream_turn")
    def test_chat_stream_returns_sse_events(self, mock_stream_turn: Any) -> None:
        self.client.get("/session/state")
        mock_stream_turn.return_value = iter(
            [
                {"type": "delta", "content": "Welcome "},
                {"type": "delta", "content": "back."},
                {
                    "type": "complete",
                    "content": "Welcome back.",
                    "openai_conversation_id": "conv_123",
                    "latest_response_id": "resp_123",
                },
            ]
        )

        response = self.client.post("/chat/stream", json={"message": "hello"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/event-stream")
        response_text = response.get_data(as_text=True)
        self.assertIn("event: delta", response_text)
        self.assertIn('"content": "Welcome "', response_text)
        self.assertIn("event: complete", response_text)
        mock_stream_turn.assert_called_once()

    def test_logging_falls_back_to_terminal_when_repo_logs_directory_is_missing(self) -> None:
        self._reset_backend_logger()

        with patch.object(backend_module, "REPO_ROOT_DIR", Path(self.temp_dir.name)):
            create_app(
                database_path=self.database_path,
                seed_manifest_path=self.seed_manifest_path,
                opening_audio_path=self.opening_audio_path,
                privacy_notice_path=self.privacy_notice_path,
            )

        self.assertIsNotNone(backend_module._get_logger_handler(backend_module.STREAM_HANDLER_NAME))
        self.assertIsNone(backend_module._get_logger_handler(backend_module.FILE_HANDLER_NAME))

    def test_logging_adds_one_file_handler_when_repo_logs_directory_is_available(self) -> None:
        self._reset_backend_logger()
        logs_directory = Path(self.temp_dir.name) / "logs"
        logs_directory.mkdir(parents=True, exist_ok=True)

        with patch.object(backend_module, "REPO_ROOT_DIR", Path(self.temp_dir.name)):
            create_app(
                database_path=self.database_path,
                seed_manifest_path=self.seed_manifest_path,
                opening_audio_path=self.opening_audio_path,
                privacy_notice_path=self.privacy_notice_path,
            )
            create_app(
                database_path=self.database_path,
                seed_manifest_path=self.seed_manifest_path,
                opening_audio_path=self.opening_audio_path,
                privacy_notice_path=self.privacy_notice_path,
            )

        configured_handlers = {
            handler.get_name(): handler
            for handler in backend_module.logger.handlers
            if handler.get_name() in {backend_module.STREAM_HANDLER_NAME, backend_module.FILE_HANDLER_NAME}
        }
        self.assertEqual(set(configured_handlers), {backend_module.STREAM_HANDLER_NAME, backend_module.FILE_HANDLER_NAME})
        self.assertEqual(
            len([handler for handler in backend_module.logger.handlers if handler.get_name() == backend_module.STREAM_HANDLER_NAME]),
            1,
        )
        self.assertEqual(
            len([handler for handler in backend_module.logger.handlers if handler.get_name() == backend_module.FILE_HANDLER_NAME]),
            1,
        )

        file_handler = configured_handlers[backend_module.FILE_HANDLER_NAME]
        self.assertIsInstance(file_handler, logging.FileHandler)
        file_handler.flush()
        logfile_path = Path(file_handler.baseFilename)
        self.assertEqual(logfile_path.parent.resolve(), logs_directory.resolve())
        self.assertRegex(logfile_path.name, r"^\d{6}_\d{6}_logfile\.log$")
        self.assertTrue(logfile_path.exists())

    @patch("crew_coordinator.CrewCoordinator.stream_turn")
    def test_request_logging_omits_chat_message_bodies(self, mock_stream_turn: Any) -> None:
        self._reset_backend_logger()
        self.client.get("/session/state")
        secret_message = "do not log this secret phrase"
        mock_stream_turn.return_value = iter(
            [
                {"type": "delta", "content": "Welcome back."},
                {
                    "type": "complete",
                    "content": "Welcome back.",
                    "openai_conversation_id": "conv_456",
                    "latest_response_id": "resp_456",
                },
            ]
        )

        with self.assertLogs(backend_module.logger.name, level="INFO") as captured_logs:
            response = self.client.post("/chat/stream", json={"message": secret_message})

        self.assertEqual(response.status_code, 200)
        combined_logs = "\n".join(captured_logs.output)
        self.assertIn("POST /chat/stream -> 200", combined_logs)
        self.assertNotIn(secret_message, combined_logs)


if __name__ == "__main__":
    unittest.main()
