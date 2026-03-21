# Project Setup

## Intended Use
- Copy or download this repository.
- Enter your project vision in `agents/agentProjectVision.md`.
- Copy the contents of `start_project.txt` into a coding agent to bootstrap setup and next steps.

## Dependencies
- Backend dependencies are defined only in `backend/requirements.txt`.
- Frontend dependencies are defined only in `frontend/package.json`.

## Install
- Backend: `pip install -r backend/requirements.txt`
- Frontend: `cd frontend && npm install`

## Run Dev
- Start both backend and frontend with `./startDevFrontAndBackend.sh`.
- The script reads `.env.dev`, then launches Flask and Vite on the configured hosts/ports.

## Environment Templates
- Dev: copy `.env.dev.example` to `.env.dev`.
- Production frontend build: copy `.env.prod.example` to `.env.prod`.
- Do not put secrets in `VITE_*` variables.
