PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS room_table (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  room_name TEXT NOT NULL,
  room_image BLOB NOT NULL,
  image_media_type TEXT NOT NULL DEFAULT 'image/png',
  room_modifications TEXT,
  state_timestamp TEXT NOT NULL,
  previous_state_id INTEGER,
  FOREIGN KEY (previous_state_id) REFERENCES room_table(id)
);

CREATE INDEX IF NOT EXISTS idx_room_table_room_name_state_timestamp
ON room_table (room_name, state_timestamp);

CREATE INDEX IF NOT EXISTS idx_room_table_session_id_room_name_state_timestamp
ON room_table (session_id, room_name, state_timestamp);
