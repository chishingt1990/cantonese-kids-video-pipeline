from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtensibleModel(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)


class Vocabulary(ExtensibleModel):
    chinese: str = Field(max_length=500)
    english: str = Field(default="", max_length=1000)


class Character(ExtensibleModel):
    name: str = Field(min_length=1, max_length=100)
    pose: str = Field(default="default", max_length=100)
    scale: float = Field(default=1, gt=0, le=10)


class Scene(ExtensibleModel):
    scene_number: int = Field(default=1, ge=1, le=200)
    title: str = Field(default="", max_length=1000)
    cantonese: str = Field(default="", max_length=10000)
    english: str = Field(default="", max_length=10000)
    background: str = Field(default="living_room", max_length=500)
    speaker: str = Field(default="Dad", max_length=100)
    duration_sec: float = Field(default=6, gt=0, le=600)
    characters: list[Character] = Field(default_factory=list, max_length=30)
    stickers: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class RenderedVideo(ExtensibleModel):
    filename: str = Field(min_length=1, max_length=255)
    input_fingerprint: str = Field(default="", max_length=64)


class ProjectData(ExtensibleModel):
    id: str | None = None
    episode_id: str | None = None
    revision: int = Field(default=0, ge=0)
    title_cantonese: str = Field(default="", max_length=1000)
    title_english: str = Field(default="", max_length=1000)
    target_age: str = Field(default="1-2 years", max_length=100)
    theme: str = Field(default="", max_length=2000)
    moral_lesson: str = Field(default="", max_length=5000)
    created_at: str = ""
    updated_at: str = ""
    scenes: list[Scene] = Field(default_factory=list, max_length=200)
    vocab_words: list[Vocabulary] = Field(default_factory=list, max_length=100)
    rendered_video: RenderedVideo | None = None

    @model_validator(mode="after")
    def matching_identity(self):
        if self.id and self.episode_id and self.id != self.episode_id:
            raise ValueError("id and episode_id must identify the same project")
        return self


class Idea(ExtensibleModel):
    id: str = Field(min_length=1, max_length=100)
    title_cantonese: str = Field(min_length=1, max_length=1000)
    title_english: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=10000)
    target_vocab: list[Vocabulary] = Field(min_length=1, max_length=30)
    moral_lesson: str = Field(max_length=5000)
    scenes_preview: list[str] = Field(min_length=1, max_length=30)


class GeneratedScene(Scene):
    cantonese: str = Field(min_length=1, max_length=10000)
    english: str = Field(min_length=1, max_length=10000)


class GeneratedScript(ProjectData):
    title_cantonese: str = Field(min_length=1, max_length=1000)
    title_english: str = Field(min_length=1, max_length=1000)
    scenes: list[GeneratedScene] = Field(min_length=7, max_length=7)


class YoutubeMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=30)


PrivacyStatus = Literal["private", "unlisted", "public"]


def project_fingerprint(data: dict | ProjectData) -> str:
    """Compatibility alias; storage owns the media fingerprint contract."""
    from app.storage import media_input_fingerprint
    return media_input_fingerprint(data)
