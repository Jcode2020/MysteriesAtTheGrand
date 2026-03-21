# Project Setup

## Intended Use
- Copy or download this repository.
- Enter your project vision in `agents/agentProjectVision.md`.
- Copy the contents of `start_project.txt` into a coding agent to bootstrap setup and next steps.

## Dependencies
- Backend dependencies are defined only in `backend/requirements.txt`.
- Frontend dependencies are defined only in `frontend/package.json`.
- The frontend UI now uses Tailwind CSS alongside React and Vite.
- The first room-state database schema lives in `backend/schema.sql`.
- Production backend serving uses Gunicorn.

## Install
- Backend: `pip install -r backend/requirements.txt`
- Frontend: `cd frontend && npm install`

## Run Dev
- Start both backend and frontend with `./startDevFrontAndBackend.sh`.
- The script reads `.env.dev`, then launches Flask and Vite on the configured hosts/ports.
- The backend will auto-create the local SQLite database at `db/hotel_db.sqlite3` unless `ROOM_DB_PATH` is set.
- Persistent room bootstrap data comes from `backend/seed/persistent/manifest.json` unless `PERSISTENT_ROOM_SEED_MANIFEST_PATH` is set.
- Set `VITE_BACKEND_URL` in `.env.dev` if you want an explicit frontend override for the backend API. When it is left empty during local development, the frontend now falls back to the same `BACKEND_HOST` and `BACKEND_PORT` values used by `startDevFrontAndBackend.sh`.
- The backend now uses an anonymous session cookie so each visitor gets an isolated room-state timeline, while each room can have a shared persistent base state visible across all sessions.

## Environment Templates
- Dev: copy `.env.dev.example` to `.env.dev`.
- Production frontend build: copy `.env.prod.example` to `.env.prod`.
- Do not put secrets in `VITE_*` variables.
- For production, set `FRONTEND_ORIGIN` to the exact public frontend URL so the backend only accepts browser writes from that origin.
- `SESSION_COOKIE_SECURE=true` is required for HTTPS deployments. `SESSION_COOKIE_SAMESITE` defaults to `Lax`.

## Production Notes
- Railway can provide the backend port via `PORT`; the backend also still accepts `BACKEND_PORT` for local development.
- When deploying the backend service from `backend/` as the Railway root directory, use Gunicorn in production instead of the Flask development server. Example: `gunicorn --bind 0.0.0.0:$PORT backend:app`
- When serving the frontend with `vite preview`, host allowlisting is now open in preview mode so generated Railway domains do not need to be hard-coded.

## Room State Database
- `room_table` stores one snapshot row per room state, scoped to a `session_id`.
- `room_image` stores the actual image bytes as a SQLite BLOB.
- `room_modifications` stores the text that describes how the room changed from the previous state.
- `state_timestamp` records when that state existed.
- `previous_state_id` links a derived room state back to its earlier snapshot.
- The earliest state for a room can use `session_id = persistent` to act as the shared base state that every session sees first.
- Persistent room definitions live in `backend/seed/persistent/manifest.json`, and the committed images it references are the source of truth for required base states.
- The current start-screen lobby image is seeded into `room_table` from `backend/seed/persistent/images/lobby.png` as the shared persistent first `lobby` entry.
- The start screen opening theme is served by the backend from `backend/static/audio/Secrets_of_the_Grand_Pannonia_2026-03-21T133239.mp3` at `GET /audio/opening-theme`.
- Session-specific room states can build on top of the persistent base for that room without affecting other visitors.
- `db/hotel_db.sqlite3` is runtime state only and should not be treated as the canonical source for required persistent rooms.
- `db/` is now for runtime SQLite state and utilities; committed schema and persistent seed assets are owned by `backend/`.
- To delete all runtime rows while keeping the schema, run `python db/clear_hotel_db.py --yes`.
- If you want to target a different SQLite file, use `python db/clear_hotel_db.py --database /path/to/file.sqlite3 --yes`.
- After clearing the database, restart the backend if you want the persistent room seed data to be created again.
- The in-app reset flow uses the backend session reset endpoint instead of wiping the full database, so it clears only the current anonymous playthrough and returns that visitor to the persistent base state.

## Backend Room State API
- `POST /rooms/states` creates a room snapshot inside the caller's current anonymous session. Send JSON with `room_name`, `room_image_base64`, optional `room_modifications`, optional `state_timestamp`, optional `previous_state_id`, and optional `image_media_type`.
- `GET /rooms/<room_name>/states` returns the full timeline for a room inside the caller's current anonymous session, including that room's shared persistent base state first when one exists. Add `?include_images=true` to include base64 image data in the response.
- `GET /rooms/<room_name>/latest` returns the latest snapshot for a room in the caller's current anonymous session, including the image. If the session has not changed the room yet, it falls back to that room's persistent base state when one exists.
- `POST /session/reset` deletes the caller's current anonymous room-state history, rotates the session cookie, and returns the experience to the persistent base state without clearing other visitors' runtime rows.
- Browser `POST /rooms/states` requests must come from the configured `FRONTEND_ORIGIN`; cross-origin writes are rejected.
