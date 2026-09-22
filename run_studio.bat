@echo off
echo Starting Kids Video Studio...
start "" "http://localhost:8000"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
