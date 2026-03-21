import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend import create_app

ONE_PIXEL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAusB9Y9nX4QAAAAASUVORK5CYII="
)


class RoomStateApiTests(unittest.TestCase):
    """Exercise the SQLite-backed room state API end to end."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test_hotel_db.sqlite3"
        self.seed_manifest_path = self._write_seed_manifest(
            [
                {
                    "room_name": "lobby",
                    "image_path": "images/lobby.png",
                    "image_media_type": "image/png",
                    "room_modifications": None,
                    "state_timestamp": "1900-01-01T00:00:00+00:00",
                }
            ]
        )
        self.app = create_app(
            database_path=self.database_path,
            seed_manifest_path=self.seed_manifest_path,
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_seed_manifest(self, persistent_rooms: list[dict[str, object]]) -> Path:
        seed_root = Path(self.temp_dir.name) / "seed"
        images_dir = seed_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        for entry in persistent_rooms:
            image_path = entry["image_path"]
            if not isinstance(image_path, str):
                raise ValueError("image_path must be a string in test seed entries.")
            (seed_root / image_path).write_bytes(base64.b64decode(ONE_PIXEL_PNG_BASE64))

        manifest_path = seed_root / "manifest.json"
        manifest_path.write_text(
            json.dumps({"persistent_rooms": persistent_rooms}, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def test_lobby_seed_is_shared_persistent_base(self) -> None:
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
        self.assertEqual(first_state["room_name"], "lobby")
        self.assertEqual(second_state["room_name"], "lobby")
        self.assertEqual(first_state["room_image_base64"], second_state["room_image_base64"])

    def test_other_rooms_can_also_use_persistent_base_states(self) -> None:
        bootstrap_database_path = Path(self.temp_dir.name) / "bootstrap_hotel_db.sqlite3"
        multi_room_manifest_path = self._write_seed_manifest(
            [
                {
                    "room_name": "lobby",
                    "image_path": "images/lobby.png",
                    "image_media_type": "image/png",
                    "room_modifications": None,
                    "state_timestamp": "1900-01-01T00:00:00+00:00",
                },
                {
                    "room_name": "ballroom",
                    "image_path": "images/ballroom.png",
                    "image_media_type": "image/png",
                    "room_modifications": None,
                    "state_timestamp": "1900-01-01T00:01:00+00:00",
                },
                {
                    "room_name": "library",
                    "image_path": "images/library.png",
                    "image_media_type": "image/png",
                    "room_modifications": None,
                    "state_timestamp": "1900-01-01T00:02:00+00:00",
                },
            ]
        )
        seeded_app = create_app(
            database_path=bootstrap_database_path,
            seed_manifest_path=multi_room_manifest_path,
        )

        first_client = seeded_app.test_client()
        second_client = seeded_app.test_client()

        first_latest_response = first_client.get("/rooms/ballroom/latest")
        second_latest_response = second_client.get("/rooms/ballroom/latest")

        self.assertEqual(first_latest_response.status_code, 200)
        self.assertEqual(second_latest_response.status_code, 200)
        self.assertEqual(first_latest_response.get_json()["session_id"], "persistent")
        self.assertEqual(second_latest_response.get_json()["session_id"], "persistent")
        self.assertEqual(first_client.get("/rooms/library/latest").get_json()["session_id"], "persistent")

    def test_create_and_fetch_room_state_timeline(self) -> None:
        lobby_response = self.client.get("/rooms/lobby/latest")
        self.assertEqual(lobby_response.status_code, 200)
        lobby_state = lobby_response.get_json()

        first_response = self.client.post(
            "/rooms/states",
            json={
                "room_name": "grand_suite",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": None,
                "state_timestamp": "2026-03-21T12:00:00+00:00",
            },
        )
        self.assertEqual(first_response.status_code, 201)
        first_state = first_response.get_json()
        self.assertIsNotNone(first_state)
        self.assertEqual(first_state["room_name"], "grand_suite")
        self.assertNotEqual(first_state["session_id"], lobby_state["session_id"])

        second_response = self.client.post(
            "/rooms/states",
            json={
                "room_name": "grand_suite",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "dog appears in the middle of the room",
                "state_timestamp": "2026-03-21T12:01:00+00:00",
                "previous_state_id": first_state["id"],
            },
        )
        self.assertEqual(second_response.status_code, 201)

        timeline_response = self.client.get("/rooms/grand_suite/states?include_images=true")
        self.assertEqual(timeline_response.status_code, 200)
        timeline = timeline_response.get_json()
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[1]["room_modifications"], "dog appears in the middle of the room")
        self.assertEqual(timeline[1]["previous_state_id"], first_state["id"])
        self.assertEqual(timeline[0]["room_image_base64"], ONE_PIXEL_PNG_BASE64)

        latest_response = self.client.get("/rooms/grand_suite/latest")
        self.assertEqual(latest_response.status_code, 200)
        latest_state = latest_response.get_json()
        self.assertEqual(latest_state["id"], timeline[1]["id"])

    def test_different_sessions_do_not_share_room_history(self) -> None:
        first_client = self.app.test_client()
        second_client = self.app.test_client()

        first_client.get("/rooms/lobby/latest")
        second_client.get("/rooms/lobby/latest")

        create_response = first_client.post(
            "/rooms/states",
            json={
                "room_name": "ballroom",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "candles are lit",
                "state_timestamp": "2026-03-21T13:00:00+00:00",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        first_timeline_response = first_client.get("/rooms/ballroom/states")
        second_timeline_response = second_client.get("/rooms/ballroom/states")

        self.assertEqual(first_timeline_response.status_code, 200)
        self.assertEqual(second_timeline_response.status_code, 200)
        self.assertEqual(len(first_timeline_response.get_json()), 1)
        self.assertEqual(second_timeline_response.get_json(), [])

    def test_lobby_timeline_includes_persistent_base_and_session_changes(self) -> None:
        first_client = self.app.test_client()
        second_client = self.app.test_client()

        first_lobby_response = first_client.get("/rooms/lobby/latest")
        second_lobby_response = second_client.get("/rooms/lobby/latest")
        first_lobby_state = first_lobby_response.get_json()
        second_lobby_state = second_lobby_response.get_json()

        create_response = first_client.post(
            "/rooms/states",
            json={
                "room_name": "lobby",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "dog appears in the middle of the room",
                "state_timestamp": "2026-03-21T13:05:00+00:00",
                "previous_state_id": first_lobby_state["id"],
            },
        )
        self.assertEqual(create_response.status_code, 201)
        session_lobby_state = create_response.get_json()

        first_timeline_response = first_client.get("/rooms/lobby/states")
        second_timeline_response = second_client.get("/rooms/lobby/states")
        self.assertEqual(first_timeline_response.status_code, 200)
        self.assertEqual(second_timeline_response.status_code, 200)

        first_timeline = first_timeline_response.get_json()
        second_timeline = second_timeline_response.get_json()
        self.assertEqual(len(first_timeline), 2)
        self.assertEqual(len(second_timeline), 1)
        self.assertEqual(first_timeline[0]["session_id"], "persistent")
        self.assertEqual(second_timeline[0]["id"], second_lobby_state["id"])

        latest_first_lobby_response = first_client.get("/rooms/lobby/latest")
        latest_second_lobby_response = second_client.get("/rooms/lobby/latest")
        self.assertEqual(latest_first_lobby_response.status_code, 200)
        self.assertEqual(latest_second_lobby_response.status_code, 200)
        self.assertEqual(latest_first_lobby_response.get_json()["id"], session_lobby_state["id"])
        self.assertEqual(latest_second_lobby_response.get_json()["id"], second_lobby_state["id"])

    def test_non_lobby_timeline_includes_persistent_base_and_session_changes(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO room_table (
                    session_id,
                    room_name,
                    room_image,
                    image_media_type,
                    room_modifications,
                    state_timestamp,
                    previous_state_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "persistent",
                    "library",
                    base64.b64decode(ONE_PIXEL_PNG_BASE64),
                    "image/png",
                    None,
                    "2026-03-21T09:00:00+00:00",
                    None,
                ),
            )
            connection.commit()

        first_client = self.app.test_client()
        second_client = self.app.test_client()

        persistent_library_response = first_client.get("/rooms/library/latest")
        persistent_library_state = persistent_library_response.get_json()

        create_response = first_client.post(
            "/rooms/states",
            json={
                "room_name": "library",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "fireplace is lit",
                "state_timestamp": "2026-03-21T09:05:00+00:00",
                "previous_state_id": persistent_library_state["id"],
            },
        )
        self.assertEqual(create_response.status_code, 201)
        session_library_state = create_response.get_json()

        first_timeline_response = first_client.get("/rooms/library/states")
        second_timeline_response = second_client.get("/rooms/library/states")
        self.assertEqual(first_timeline_response.status_code, 200)
        self.assertEqual(second_timeline_response.status_code, 200)

        first_timeline = first_timeline_response.get_json()
        second_timeline = second_timeline_response.get_json()
        self.assertEqual(len(first_timeline), 2)
        self.assertEqual(len(second_timeline), 1)
        self.assertEqual(first_timeline[0]["session_id"], "persistent")
        self.assertEqual(second_timeline[0]["session_id"], "persistent")

        latest_first_library_response = first_client.get("/rooms/library/latest")
        latest_second_library_response = second_client.get("/rooms/library/latest")
        self.assertEqual(latest_first_library_response.get_json()["id"], session_library_state["id"])
        self.assertEqual(latest_second_library_response.get_json()["id"], persistent_library_state["id"])

    def test_rejects_invalid_base64_payload(self) -> None:
        self.client.get("/rooms/lobby/latest")

        response = self.client.post(
            "/rooms/states",
            json={
                "room_name": "ballroom",
                "room_image_base64": "not-base64",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("valid base64", response.get_json()["error"])

    def test_rejects_previous_state_from_another_session(self) -> None:
        first_client = self.app.test_client()
        second_client = self.app.test_client()

        first_client.get("/rooms/lobby/latest")
        second_client.get("/rooms/lobby/latest")

        first_response = first_client.post(
            "/rooms/states",
            json={
                "room_name": "suite",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "state_timestamp": "2026-03-21T12:00:00+00:00",
            },
        )
        self.assertEqual(first_response.status_code, 201)
        first_state = first_response.get_json()

        second_response = second_client.post(
            "/rooms/states",
            json={
                "room_name": "suite",
                "room_image_base64": ONE_PIXEL_PNG_BASE64,
                "room_modifications": "window opens",
                "state_timestamp": "2026-03-21T12:02:00+00:00",
                "previous_state_id": first_state["id"],
            },
        )
        self.assertEqual(second_response.status_code, 400)
        self.assertIn("this session", second_response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
