from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.ai_service import generate_full_script, _generate_dynamic_fallback_script, GenerationError
from app.models import Idea, GeneratedScript

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


class ScriptGenRequest(BaseModel):
    idea: Idea
    characters: list[str] = Field(default_factory=lambda: ["levi", "luca", "dad", "mom"], min_length=1, max_length=30)
    allow_fallback: bool = False


@router.post("/generate")
def create_script(req: ScriptGenRequest):
    idea = req.idea.model_dump(mode="json")
    try:
        return {"script": generate_full_script(idea, req.characters), "status": "generated", "provenance": "ai"}
    except GenerationError as exc:
        if not req.allow_fallback:
            raise HTTPException(502, str(exc))
        script = GeneratedScript.model_validate(_generate_dynamic_fallback_script(idea, req.characters)).model_dump(mode="json", exclude_none=True)
        return {"script": script, "status": "fallback", "provenance": "offline_template", "warning": str(exc)}
