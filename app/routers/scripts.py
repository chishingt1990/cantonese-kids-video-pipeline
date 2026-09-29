from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError
from app.services.ai_service import generate_full_script, _generate_dynamic_fallback_script, GenerationError
from app.models import Idea, GeneratedScript, GENERATION_MIN_DURATION_SEC, GENERATION_TARGET_DURATION_SEC, GENERATION_MAX_DURATION_SEC

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


class ScriptGenRequest(BaseModel):
    idea: Idea
    characters: list[str] = Field(default_factory=lambda: ["levi", "luca", "dad", "mom"], min_length=1, max_length=30)
    allow_fallback: bool = False
    target_duration_sec: int = Field(default=GENERATION_TARGET_DURATION_SEC, ge=GENERATION_MIN_DURATION_SEC, le=GENERATION_MAX_DURATION_SEC, strict=True)


def _validated_template(req):
    try:
        return GeneratedScript.model_validate(_generate_dynamic_fallback_script(
            req.idea.model_dump(mode="json"), req.characters,
            target_duration_sec=req.target_duration_sec,
        )).model_dump(mode="json", exclude_none=True)
    except GenerationError as exc:
        raise HTTPException(exc.status_code, str(exc),
                            headers={"X-Studio-Error-Code": exc.code}) from None
    except ValidationError:
        raise HTTPException(502, "The offline lesson could not meet the duration and teaching requirements. Try shorter target vocabulary or another idea.") from None


@router.post("/template")
def create_template(req: ScriptGenRequest):
    return {
        "script": _validated_template(req), "status": "template",
        "provenance": "offline_template",
        "warning": "Offline story template: no AI request was made. Review and edit the narration before using your voice.",
    }


@router.post("/generate")
def create_script(req: ScriptGenRequest):
    idea = req.idea.model_dump(mode="json")
    try:
        return {"script": generate_full_script(idea, req.characters, target_duration_sec=req.target_duration_sec), "status": "generated", "provenance": "ai"}
    except GenerationError as exc:
        if not req.allow_fallback:
            raise HTTPException(exc.status_code, str(exc), headers={"X-Studio-Error-Code": exc.code})
        script = _validated_template(req)
        return {"script": script, "status": "fallback", "provenance": "offline_template", "warning": str(exc), "error_code": exc.code}
