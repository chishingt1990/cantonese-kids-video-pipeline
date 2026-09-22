# Cantonese Kids Video Pipeline & Studio

A full-stack, pedagogical Cantonese educational video generation studio designed for overseas Cantonese-speaking toddlers and families.

## Environment & Tech Stack
- **Python Runtime:** Python 3.13 via virtual environment located at `.venv/`
  - To invoke Python in PowerShell: `& '.\.venv\Scripts\python.exe'`
  - Server runner: `& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
- **Frontend:** Vanilla HTML5, CSS3, ES6 JavaScript (No React/Node build steps needed, static assets served via FastAPI at `app/static/`).
- **Web App URL:** `http://127.0.0.1:8000`
- **Asset Review Gallery:** `http://127.0.0.1:8000/review`

## Repository Structure
- `app/main.py`: FastAPI server setup and router registration.
- `app/routers/`:
  - `projects.py`: Project persistence & CRUD API (`/api/projects/`).
  - `youtube.py`: OAuth authentication, metadata generation, and video upload API (`/api/youtube/`).
  - `characters.py`, `script.py`, `voice.py`, `stage.py`, `video.py`, `settings.py`.
- `app/services/`:
  - `project_service.py`: JSON project serialization under `projects/{id}/project.json`.
  - `youtube_service.py`: YouTube Data API v3 integration and AI preschool metadata generation.
  - `scene_director_service.py`: 4-tier semantic narrative parser and action-prop staging.
  - `render_service.py`: Ken Burns camera motion, squash-and-stretch sticker pop-ins, ukulele bounce, eye blinks, and cross-dissolves.
  - `sticker_service.py`: 12+ milestone visual props (dim sum, toothbrush, crayons, blocks, etc.).
- `projects/`: File-backed storage for projects (e.g. `ep01_meeting_family`).
- `assets/`:
  - `assets/sprites/`: Canonical watercolor character action poses (Levi, Luca, Mom, Dad, Dog).
  - `assets/stickers/`: Props, badges, and learning stickers.
  - `assets/backgrounds/`: Living room, park, dining room watercolor scenes.
  - `assets/audio/`: Ukulele backing tracks and sound effects.

## Conventions & Rules
1. **Preschool Safety & Tone:** Content is tailored for 1-4 year old toddlers learning Cantonese. Keep vocabulary authentic (Spoken Cantonese / 廣東話), gentle, and encouraging.
2. **File-Backed Persistence:** Projects are saved directly into `projects/<project_id>/project.json`.
3. **No Breaking Web UI Changes:** Keep existing API routes intact; when modifying UI, preserve the 5-step workflow (Theme -> Script -> Staging -> Audio -> Render/Publish).
