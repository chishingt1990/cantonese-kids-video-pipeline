from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.ai_service import generate_full_script

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

class ScriptGenRequest(BaseModel):
    idea: dict
    characters: list = ["levi", "luca", "dad", "mom"]
    topic: Optional[str] = ""
    age_group: Optional[str] = ""

@router.post("/generate")
def create_script(req: ScriptGenRequest):
    script = generate_full_script(req.idea, req.characters, req.topic or "", req.age_group or "")
    return {"script": script}
