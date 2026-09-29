import json
import os
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator
from app.storage import DATA_DIR, ROOT, atomic_write_json, project_lock

CONFIG_FILE = DATA_DIR / "config" / "studio_settings.json"
SECRET_FIELDS = ("gemini_api_key", "openai_api_key", "anthropic_api_key", "azure_api_key")


class SettingsCorruptError(ValueError):
    pass


class StudioSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    azure_api_key: str = ""
    azure_endpoint: str = ""
    ollama_url: str = "http://localhost:11434"
    active_model: str = "gemini-3.6-flash"
    active_provider: Literal["gemini", "openai", "anthropic", "azure", "ollama"] = "gemini"
    project_dir: str = str(DATA_DIR)

    @field_validator("ollama_url")
    @classmethod
    def local_ollama(cls, value):
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.username or url.password or url.query or url.fragment:
            raise ValueError("Ollama must use a loopback HTTP endpoint")
        return value.rstrip("/")

    @field_validator("azure_endpoint")
    @classmethod
    def azure_endpoint_only(cls, value):
        if value:
            url = urlsplit(value)
            if url.scheme != "https" or not (url.hostname or "").endswith(".openai.azure.com") or url.username or url.password or url.query or url.fragment:
                raise ValueError("Use an HTTPS Azure OpenAI resource endpoint")
        return value.rstrip("/")


def load_settings() -> StudioSettings:
    with project_lock("studio-settings"):
        if os.environ.get("KIDS_STUDIO_TESTING") != "1":
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        if CONFIG_FILE.exists():
            try:
                settings = StudioSettings.model_validate_json(CONFIG_FILE.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:
                raise SettingsCorruptError("Settings are unreadable; original file preserved. Restore a valid backup.") from exc
            # Explicit empty persisted values remain cleared rather than resurrected from the environment.
            return settings
        values = {key: os.environ.get(key.upper(), "") for key in SECRET_FIELDS}
        values["gemini_api_key"] = values["gemini_api_key"] or os.environ.get("GOOGLE_API_KEY", "")
        values["azure_api_key"] = os.environ.get("AZURE_OPENAI_API_KEY", "") or values["azure_api_key"]
        values["azure_endpoint"] = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        if os.environ.get("OLLAMA_URL"):
            values["ollama_url"] = os.environ["OLLAMA_URL"]
        return StudioSettings(**values)


def save_settings(settings: StudioSettings):
    with project_lock("studio-settings"):
        atomic_write_json(CONFIG_FILE, settings.model_dump())
        try:
            CONFIG_FILE.chmod(0o600)
        except OSError:
            pass


def public_settings(settings: StudioSettings):
    data = settings.model_dump(exclude=set(SECRET_FIELDS) | {"project_dir"})
    data.update({f"{key}_configured": bool(getattr(settings, key)) for key in SECRET_FIELDS})
    return data
