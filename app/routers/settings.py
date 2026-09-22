from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel
from app.config import load_settings, save_settings, StudioSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    ollama_url: Optional[str] = None
    active_model: Optional[str] = None
    active_provider: Optional[str] = None

@router.get("/")
def get_settings():
    return load_settings()

@router.post("/")
def update_settings(req: SettingsUpdateRequest):
    current = load_settings()
    data = req.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None and v != "":
            setattr(current, k, v)
        elif v == "":
            setattr(current, k, "")
    save_settings(current)
    return {"status": "saved", "settings": current}
