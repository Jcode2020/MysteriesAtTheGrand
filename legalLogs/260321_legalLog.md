## Decision 260321-001
- decision_id: 260321-001
- timestamp: 2026-03-21T13:35:13+01:00
- requested_by: human
- recorded_by: agent
- decision: Adopt `moodboards/_merge_final.html` as the single canonical moodboard and project design-language reference, and remove the other moodboards to avoid confusion.
- rationale: The human chose one clear visual source of truth so future design and implementation decisions stay aligned around a single palette, typography system, and layout language rather than competing references.
- impact_scope: `moodboards/`, `agents/agentProjectDesign.md`, and future visual design decisions across the project
- status: active

## Decision 260321-002
- decision_id: 260321-002
- timestamp: 2026-03-21T14:10:00+01:00
- requested_by: human
- recorded_by: agent
- decision: Implement the first persistent room-state store as a SQLite-backed `room_table` snapshot history in `db/`, with actual room images stored as BLOBs, per-state modification text tracked over time, anonymous `session_id` isolation for visitor-specific changes, shared persistent base rows for rooms, and committed manifest-driven bootstrap assets so fresh deployments do not depend on the ignored SQLite runtime file.
- rationale: The human chose a repo-local prototype architecture that keeps setup simple for development while preserving the core gameplay requirement that each room can evolve through timestamped visual states and textual modifications, clarified that multiple visitors must be able to use the app simultaneously without sharing their private state, clarified that initial room states should remain globally shared, and then identified that required base room rows must come from committed source files rather than a non-versioned database file.
- impact_scope: `backend/backend.py`, `db/seed/persistent/`, frontend session-aware room loading, `.env.dev.example`, `README.md`, and future room-image persistence and retrieval behavior
- status: active
- last_updated: 2026-03-21T16:33:00+01:00
