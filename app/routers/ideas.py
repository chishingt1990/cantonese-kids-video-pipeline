from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import brainstorm_ideas

router = APIRouter(prefix="/api/ideas", tags=["ideas"])

class IdeaRequest(BaseModel):
    topic: str = "Meeting the Family"
    age_group: str = "1-2 years (Toddlers)"
    theme: str = "Manners, Love & Politeness"

@router.post("/generate")
def generate_ideas(req: IdeaRequest):
    try:
        ideas = brainstorm_ideas(req.topic, req.age_group, req.theme)
        return {"ideas": ideas, "status": "success"}
    except Exception as e:
        print(f"Error in ideas generator: {e}")
        # Return fallback ideas immediately so parent is never blocked
        return {
            "status": "fallback",
            "ideas": [
                {
                    "id": "idea_1",
                    "title_cantonese": f"一齊玩！{req.topic}",
                    "title_english": f"Playing Together: {req.topic}",
                    "description": f"Levi 哥哥 and Luca 細佬 learn how to share toys, take gentle turns, and say '多謝' (Thank you).",
                    "target_vocab": [
                        {"chinese": "一齊玩", "jyutping": "jat1 cai4 waan2", "english": "Play together"},
                        {"chinese": "輪流", "jyutping": "leon4 lau4", "english": "Take turns"},
                        {"chinese": "多謝", "jyutping": "do1 ze6", "english": "Thank you"}
                    ],
                    "moral_lesson": "Sharing is caring! When we take turns, everyone is happy.",
                    "scenes_preview": [
                        "Playing with colorful blocks",
                        "Taking turns rolling a toy car",
                        "Sharing snacks and saying thank you",
                        "Warm brotherly hug"
                    ]
                }
            ]
        }
