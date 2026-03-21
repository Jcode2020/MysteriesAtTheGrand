# Project Setup

## Intended Use
- Copy or download this repository.
- Enter your project vision in `agents/agentProjectVision.md`.
- Copy the contents of `start_project.txt` into a coding agent to bootstrap setup and next steps.

## Dependencies
- Backend dependencies are defined only in `backend/requirements.txt`.
- Frontend dependencies are defined only in `frontend/package.json`.
- The frontend UI now uses Tailwind CSS alongside React and Vite.
- The committed runtime schema lives in `backend/schema.sql`.
- Production backend serving uses Gunicorn.
- The CrewAI coordinator and room/inventory handlers use OpenAI services from the backend only.

## Install
- Backend: `pip install -r backend/requirements.txt`
- Frontend: `cd frontend && npm install`

## Run Dev
- Start both backend and frontend with `./startDevFrontAndBackend.sh`.
- The script reads `.env.dev`, then launches Flask and Vite on the configured hosts/ports.
- The backend always logs debugging activity to the terminal. When the repo-root `logs/` directory exists and is writable, the backend also mirrors those logs into a timestamped logfile there; otherwise it falls back to terminal-only logging.
- The backend will auto-create the local SQLite database at `db/hotel_db.sqlite3` unless `ROOM_DB_PATH` is set.
- Persistent room bootstrap data comes from `backend/seed/persistent/manifest.json` unless `PERSISTENT_ROOM_SEED_MANIFEST_PATH` is set.
- Set `VITE_BACKEND_URL` in `.env.dev` if you want an explicit frontend override for the backend API. When it is left empty during local development, the frontend now falls back to the same `BACKEND_HOST` and `BACKEND_PORT` values used by `startDevFrontAndBackend.sh`.
- The backend uses an anonymous session cookie so each visitor gets an isolated room-state timeline, suitcase inventory, current-room pointer, and OpenAI conversation pointer.

## Environment Templates
- Dev: copy `.env.dev.example` to `.env.dev`.
- Production frontend build: copy `.env.prod.example` to `.env.prod`.
- Do not put secrets in `VITE_*` variables.
- For production, set `FRONTEND_ORIGIN` to the exact public frontend URL so the backend only accepts browser writes from that origin.
- `SESSION_COOKIE_SECURE=true` is required for HTTPS deployments. `SESSION_COOKIE_SAMESITE` defaults to `Lax`.
- Set `OPENAI_API_KEY` for the CrewAI/OpenAI backend integration.
- `OPENAI_CREW_MODEL` controls the text model used by the coordinator and handler agents.
- `OPENAI_IMAGE_MODEL` controls the image-edit model used when a room image must change visibly.

## Production Notes
- Railway can provide the backend port via `PORT`; the backend also still accepts `BACKEND_PORT` for local development.
- When deploying the backend service from `backend/` as the Railway root directory, use Gunicorn in production instead of the Flask development server. Example: `gunicorn --bind 0.0.0.0:$PORT backend:app`
- `backend/gunicorn.conf.py` raises the default request timeout for production chat/image-edit turns. If your Railway start command overrides Gunicorn config loading, pass it explicitly with `-c gunicorn.conf.py`.
- When serving the frontend with `vite preview`, host allowlisting is now open in preview mode so generated Railway domains do not need to be hard-coded.
- The chat endpoint streams `text/event-stream` responses. If you tune Gunicorn later, make sure long-lived streamed requests remain supported.

## Room State Database
- `room_table` stores one snapshot row per room state, scoped to a `session_id`.
- `room_image` stores the actual image bytes as a SQLite BLOB.
- `room_modifications` stores the text that describes how the room changed from the previous state.
- `room_description` stores the current exhaustive semantic description used to decide whether actions are possible.
- `state_timestamp` records when that state existed.
- `previous_state_id` links a derived room state back to its earlier snapshot.
- The earliest state for a room can use `session_id = persistent` to act as the shared base state that every session sees first.
- `session_state` stores the active room for each anonymous visitor session.
- `inventory_table` stores the session-scoped suitcase inventory, seeded from committed backend assets.
- `crew_convos` stores the session-scoped OpenAI conversation pointer metadata used by the CrewAI coordinator.
- Persistent room and inventory definitions live in `backend/seed/persistent/manifest.json`, and the committed assets it references are the source of truth for required base states.
- The current start-screen lobby image is seeded into `room_table` from `backend/seed/persistent/images/lobby.png` as the shared persistent first `lobby` entry.
- The current suitcase starter inventory is seeded from `backend/seed/persistent/inventory/`.
- The start screen opening theme is served by the backend from `backend/static/audio/Secrets_of_the_Grand_Pannonia_2026-03-21T133239.mp3` at `GET /audio/opening-theme`.
- Session-specific room states can build on top of the persistent base for that room without affecting other visitors.
- `db/hotel_db.sqlite3` is runtime state only and should not be treated as the canonical source for required persistent rooms.
- `db/` is now for runtime SQLite state and utilities; committed schema and persistent seed assets are owned by `backend/`.
- To delete all runtime rows while keeping the schema, run `python db/clear_hotel_db.py --yes`.
- If you want to target a different SQLite file, use `python db/clear_hotel_db.py --database /path/to/file.sqlite3 --yes`.
- After clearing the database, restart the backend if you want the persistent room seed data to be created again.
- The in-app reset flow uses the backend session reset endpoint instead of wiping the full database, so it clears only the current anonymous playthrough and returns that visitor to the persistent base state.

## Backend Room State API
- `POST /rooms/states` creates a room snapshot inside the caller's current anonymous session. Send JSON with `room_name`, `room_image_base64`, optional `room_modifications`, optional `room_description`, optional `state_timestamp`, optional `previous_state_id`, and optional `image_media_type`.
- `GET /rooms/<room_name>/states` returns the full timeline for a room inside the caller's current anonymous session, including that room's shared persistent base state first when one exists. Add `?include_images=true` to include base64 image data in the response.
- `GET /rooms/<room_name>/latest` returns the latest snapshot for a room in the caller's current anonymous session, including the image. If the session has not changed the room yet, it falls back to that room's persistent base state when one exists.
- `GET /session/state` returns the current anonymous session row, including the active room name.
- `GET /inventory` returns the current anonymous session suitcase inventory, including base64 image data for each item.
- `POST /chat/stream` accepts a JSON body with `message` and returns an SSE-style `text/event-stream` response from the CrewAI coordinator.
- `GET /legal/privacy-notice` returns the plain-language prototype privacy notice shown on the start screen.
- `POST /session/reset` deletes the caller's current anonymous room-state history, suitcase inventory, session row, and conversation pointer, rotates the session cookie, and returns the experience to a fresh anonymous state without clearing other visitors' runtime rows.
- Browser `POST /rooms/states` requests must come from the configured `FRONTEND_ORIGIN`; cross-origin writes are rejected.

## Canonical AI Prompt Assets
- Canonical runtime design guidance now lives in `backend/agentProjectDesign.md`.
- The canonical moodboard now lives in `backend/moodboards/_merge_final.html`.
- `agents/agentProjectDesign.md` remains as the workspace bridge file and points back to the canonical backend copy.

## Prototype Privacy Warning
- The start flow now requires the player to acknowledge a plain-language prototype warning before entering the experience.
- The warning states that this is a prototype, that no sensitive data should be entered, and that gameplay data flows through Railway and OpenAI services.
