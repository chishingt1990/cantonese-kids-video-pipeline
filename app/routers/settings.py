from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel, ValidationError
from app.config import load_settings, save_settings, StudioSettings, public_settings
from app.storage import project_lock

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
    return public_settings(load_settings())

@router.post("/")
def update_settings(req: SettingsUpdateRequest):
    with project_lock("studio-settings"):
        data = load_settings().model_dump()
        data.update(req.model_dump(exclude_unset=True, exclude_none=True))
        try:
            current = StudioSettings.model_validate(data)
        except ValidationError:
            raise HTTPException(422, "Invalid provider or endpoint settings")
        save_settings(current)
        return {"status": "saved", "settings": public_settings(current)}
