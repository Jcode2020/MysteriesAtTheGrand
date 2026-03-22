## Decision 260322-001
- decision_id: 260322-001
- timestamp: 2026-03-22T10:54:03+01:00
- requested_by: human
- recorded_by: agent
- decision: Add backend-only ElevenLabs receptionist text-to-speech playback that speaks newly completed receptionist chat bubbles, interrupts earlier receptionist speech with newer lines, and ducks the looping theme through the shared speech-active audio rule already used for spoken narration.
- rationale: The human chose a lightweight character-voice enhancement that strengthens immersion and demo value without changing the core receptionist chat flow, explicitly required that secrets stay backend-only, preferred a simple configuration surface limited to API key and receptionist voice ID, accepted in-memory-only handling for the first version, and confirmed that budget control would be handled on the ElevenLabs side rather than by adding a second local quota system.
- impact_scope: `backend/backend.py`, new backend ElevenLabs helper logic, frontend receptionist playback state in `frontend/src/App.tsx`, audio ducking behavior, env templates, and deployment/runtime configuration for receptionist speech
- status: active
