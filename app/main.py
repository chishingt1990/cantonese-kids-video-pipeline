import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import settings, ideas, scripts, characters, audio, render, scene_director, projects, youtube

app = FastAPI(title="Kids Video Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(ideas.router)
app.include_router(scripts.router)
app.include_router(characters.router)
app.include_router(audio.router)
app.include_router(render.router)
app.include_router(scene_director.router)
app.include_router(projects.router)
app.include_router(youtube.router)

static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_path, "index.html"))

@app.get("/review")
@app.get("/gallery")
def read_review():
    return FileResponse(os.path.join(static_path, "review.html"))

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Kids Video Studio"}
