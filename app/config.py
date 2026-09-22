import os
import json
from pydantic import BaseModel

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "studio_settings.json")

class StudioSettings(BaseModel):
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    azure_api_key: str = ""
    azure_endpoint: str = ""
    ollama_url: str = "http://localhost:11434"
    active_model: str = "gemini-3.6-flash"
    active_provider: str = "gemini"  # "gemini", "openai", "anthropic", "azure", "ollama"
    project_dir: str = os.path.dirname(os.path.dirname(__file__))

def load_settings() -> StudioSettings:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return StudioSettings(**data)
        except Exception:
            pass
    
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    settings = StudioSettings(gemini_api_key=api_key)
    save_settings(settings)
    return settings

def save_settings(settings: StudioSettings):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2)
