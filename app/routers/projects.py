from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from app.services import project_service
from app.models import ProjectData

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectSaveRequest(BaseModel):
    project_data: ProjectData

class ProjectCreateRequest(BaseModel):
    title_cantonese: str = Field(max_length=1000)
    title_english: str = Field(max_length=1000)
    target_age: str = Field(default="1-2 years", max_length=100)
    theme: str = Field(default="", max_length=2000)
    moral_lesson: str = Field(default="", max_length=5000)

@router.get("/")
def get_all_projects():
    """List all saved projects."""
    return project_service.list_projects()

@router.get("/{project_id}")
def get_single_project(project_id: str):
    """Retrieve full project details by ID."""
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@router.post("/")
def create_project(req: ProjectCreateRequest):
    """Creates a new project draft."""
    import datetime
    import uuid
    now = datetime.datetime.now(datetime.timezone.utc)
    p_id = f"proj_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    new_data = {
        "id": p_id,
        "episode_id": p_id,
        "title_cantonese": req.title_cantonese,
        "title_english": req.title_english,
        "target_age": req.target_age,
        "theme": req.theme,
        "moral_lesson": req.moral_lesson,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "version": 1,
        "_autoDirected": False,
        "vocab_words": [],
        "subtitle_options": {
            "pill_style": "warm_cream",
            "font_size_cn": 52,
            "font_size_en": 26
        },
        "scenes": []
    }
    saved = project_service.save_project(p_id, new_data)
    return {"status": "created", "project": saved}

@router.put("/{project_id}")
def update_project(project_id: str, req: ProjectSaveRequest):
    """Saves or updates project state."""
    saved = project_service.save_project(project_id, req.project_data.model_dump(mode="json", exclude_none=True))
    return {"status": "saved", "project": saved}

@router.post("/{project_id}/duplicate")
def duplicate_project(project_id: str):
    """Duplicates an existing project."""
    cloned = project_service.duplicate_project(project_id)
    if not cloned:
        raise HTTPException(status_code=404, detail="Original project not found")
    return {"status": "duplicated", "project": cloned}

@router.delete("/{project_id}")
def delete_project(project_id: str):
    """Deletes a project."""
    success = project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted", "id": project_id}

@router.get("/{project_id}/thumbnail")
def get_thumbnail(project_id: str):
    """Serves the project 16:9 thumbnail preview."""
    thumb = project_service.get_thumbnail_path(project_id)
    if not thumb:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumb, media_type="image/png")
