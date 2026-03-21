PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS room_table (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  room_name TEXT NOT NULL,
  room_image BLOB NOT NULL,
  image_media_type TEXT NOT NULL DEFAULT 'image/png',
  room_modifications TEXT,
  room_description TEXT,
  state_timestamp TEXT NOT NULL,
  previous_state_id INTEGER,
  FOREIGN KEY (previous_state_id) REFERENCES room_table(id)
);

CREATE INDEX IF NOT EXISTS idx_room_table_room_name_state_timestamp
ON room_table (room_name, state_timestamp);

CREATE INDEX IF NOT EXISTS idx_room_table_session_id_room_name_state_timestamp
ON room_table (session_id, room_name, state_timestamp);

CREATE TABLE IF NOT EXISTS session_state (
  session_id TEXT PRIMARY KEY,
  current_room_name TEXT NOT NULL DEFAULT 'lobby',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_state_current_room_name
ON session_state (current_room_name);

CREATE TABLE IF NOT EXISTS inventory_table (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  item_key TEXT NOT NULL,
  item_name TEXT NOT NULL,
  item_detail TEXT NOT NULL,
  item_image BLOB NOT NULL,
  image_media_type TEXT NOT NULL DEFAULT 'image/png',
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES session_state(session_id) ON DELETE CASCADE,
  UNIQUE(session_id, item_key)
);

CREATE INDEX IF NOT EXISTS idx_inventory_table_session_id_item_key
ON inventory_table (session_id, item_key);

CREATE TABLE IF NOT EXISTS crew_convos (
  session_id TEXT PRIMARY KEY,
  openai_conversation_id TEXT,
  latest_response_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES session_state(session_id) ON DELETE CASCADE
);
