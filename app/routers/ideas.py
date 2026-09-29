from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.ai_service import brainstorm_ideas, get_grounded_topic_ideas, GenerationError
from app.models import Idea

router = APIRouter(prefix="/api/ideas", tags=["ideas"])


class IdeaRequest(BaseModel):
    topic: str = Field(default="Meeting the Family", min_length=1, max_length=2000)
    age_group: str = Field(default="1-2 years (Toddlers)", max_length=100)
    theme: str = Field(default="Manners, Love & Politeness", max_length=2000)
    allow_fallback: bool = False


@router.post("/generate")
def generate_ideas(req: IdeaRequest):
    try:
        return {"ideas": brainstorm_ideas(req.topic, req.age_group, req.theme), "status": "generated", "provenance": "ai"}
    except GenerationError as exc:
        if not req.allow_fallback:
            raise HTTPException(502, str(exc))
        ideas = [Idea.model_validate(item).model_dump(mode="json") for item in get_grounded_topic_ideas(req.topic, req.age_group)]
        return {"ideas": ideas, "status": "fallback", "provenance": "offline_template", "warning": str(exc)}
