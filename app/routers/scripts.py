from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import generate_full_script

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

class ScriptGenRequest(BaseModel):
    idea: dict
    characters: list = ["levi", "luca", "dad", "mom"]

@router.post("/generate")
def create_script(req: ScriptGenRequest):
    script = generate_full_script(req.idea, req.characters)
    return {"script": script}
