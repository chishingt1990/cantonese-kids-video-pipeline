from typing import Any, Literal
import math
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

GENERATION_MIN_DURATION_SEC = 120
GENERATION_TARGET_DURATION_SEC = 180
GENERATION_MAX_DURATION_SEC = 240
GENERATION_PREFERRED_MIN_SEC = 150
GENERATION_PREFERRED_MAX_SEC = 210
GENERATED_SCENE_TYPES = (
    "HOOK", "QUESTION", "SOUND-PLAY", "ACTION", "COUNT", "PRETEND", "DISCOVER", "GAG",
    "CHORUS", "CHALLENGE", "COMFORT", "TRY-AGAIN", "CELEBRATE", "REVIEW", "GOODBYE",
)
SceneType = Literal[
    "HOOK", "QUESTION", "SOUND-PLAY", "ACTION", "COUNT", "PRETEND", "DISCOVER", "GAG",
    "CHORUS", "CHALLENGE", "COMFORT", "TRY-AGAIN", "CELEBRATE", "REVIEW", "GOODBYE",
]


def chinese_spoken_text(value: str) -> str:
    punctuation = "，。！？；：、…—「」『』（）《》〈〉“”‘’·〇"
    if any(not (char.isspace() or char in punctuation or "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff" or "\U00020000" <= char <= "\U0002fa1f") for char in value):
        raise PydanticCustomError("spoken_chinese_only", "Spoken Cantonese must use Chinese characters and punctuation only, without English names or Latin letters")
    if value.strip() and not re.search(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f〇]", value):
        raise PydanticCustomError("spoken_chinese_only", "Spoken Cantonese must contain Chinese words, not only punctuation")
    return value


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


VoiceStyle = Literal["calm", "warm_playful", "excited"]


class VoiceOptions(ExtensibleModel):
    voice_id: str | None = Field(default=None, max_length=100)
    use_cloned: bool | None = None
    style: VoiceStyle | None = None


class NarrationWord(ExtensibleModel):
    text: str = Field(max_length=10000)
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered_word(self):
        if self.end_sec <= self.start_sec:
            raise ValueError("Narration word end must follow its start")
        return self


class NarrationScene(ExtensibleModel):
    scene_number: int = Field(ge=1, le=200)
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    words: list[NarrationWord] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def ordered_scene(self):
        if self.end_sec <= self.start_sec:
            raise ValueError("Narration scene end must follow its start")
        return self


class NarrationAttachment(ExtensibleModel):
    take_id: str = Field(min_length=1, max_length=100)
    audio_url: str | None = Field(default=None, max_length=500)
    duration_sec: float | None = Field(default=None, gt=0)
    script_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    voice_id: str | None = Field(default=None, max_length=100)
    style: VoiceStyle | None = None
    alignment_method: Literal["asr", "estimated", "none"] | None = None
    scenes: list[NarrationScene] = Field(default_factory=list, max_length=200)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    source_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("take_id")
    @classmethod
    def valid_take_id(cls, value):
        from app.storage import validate_id
        return validate_id(value)


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
    narration: NarrationAttachment | None = None
    previous_narration: NarrationAttachment | None = None
    narration_current: bool = Field(default=False, exclude=True)
    voice_options: VoiceOptions | None = None

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
    cantonese: str = Field(min_length=1, max_length=512)
    english: str = Field(min_length=1, max_length=10000)
    speaker: Literal["Dad"] = "Dad"
    duration_sec: float = Field(gt=0, le=30)
    scene_type: SceneType | None = None
    act: int | None = Field(default=None, ge=1, le=5)
    chorus: str | None = Field(default=None, max_length=500)
    interaction_prompt: str | None = Field(default=None, max_length=1000)

    @field_validator("cantonese", "english")
    @classmethod
    def nonblank_dialogue(cls, value):
        if not value.strip():
            raise ValueError("Generated dialogue must contain teaching content")
        return value.strip()

    @field_validator("cantonese", "chorus", "interaction_prompt")
    @classmethod
    def spoken_language_split(cls, value):
        return chinese_spoken_text(value) if value is not None else value

    @model_validator(mode="after")
    def conservative_speech_pacing(self):
        units = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f〇]", self.cantonese))
        # Loose script-only bounds, allowing short hooks and up to four seconds for interaction.
        if units > self.duration_sec * 8 + 8 or self.duration_sec > units + 4:
            raise PydanticCustomError("lesson_pacing", "Narration length is implausible for its planned scene duration")
        return self


class GeneratedScript(ProjectData):
    title_cantonese: str = Field(min_length=1, max_length=1000)
    title_english: str = Field(min_length=1, max_length=1000)
    scenes: list[GeneratedScene] = Field(min_length=18, max_length=22)
    target_duration_sec: int = Field(default=GENERATION_TARGET_DURATION_SEC, ge=GENERATION_MIN_DURATION_SEC, le=GENERATION_MAX_DURATION_SEC)
    planned_duration_sec: float = 0
    chorus: str | None = Field(default=None, max_length=500)

    @field_validator("chorus")
    @classmethod
    def chinese_chorus(cls, value):
        return chinese_spoken_text(value) if value is not None else value

    @model_validator(mode="after")
    def lesson_duration_and_sequence(self):
        if [scene.scene_number for scene in self.scenes] != list(range(1, len(self.scenes) + 1)):
            raise PydanticCustomError("lesson_sequence", "Generated scene numbers must be sequential starting at one")
        for previous, current in zip(self.scenes, self.scenes[1:]):
            if previous.scene_type and previous.scene_type == current.scene_type:
                raise PydanticCustomError("lesson_scene_types", "Adjacent generated scenes must use different scene types")
        total = math.fsum(scene.duration_sec for scene in self.scenes)
        if not GENERATION_MIN_DURATION_SEC <= total <= GENERATION_MAX_DURATION_SEC:
            raise PydanticCustomError(
                "lesson_duration",
                "Generated lessons require 120–240 seconds of planned teaching content",
            )
        units = sum(len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f〇]", scene.cantonese)) for scene in self.scenes)
        if not total * 1.5 <= units <= total * 8:
            raise PydanticCustomError("lesson_pacing", "Total narration length is implausible for the planned lesson duration")
        self.planned_duration_sec = round(total, 3)
        return self


def generated_story_response_schema() -> dict:
    """Small authoring-only provider schema; runtime validation remains authoritative."""
    text = {"type": "string"}
    return {
        "type": "object",
        "required": ["title_cantonese", "title_english", "moral_lesson", "vocab_words", "scenes"],
        "properties": {
            "title_cantonese": dict(text), "title_english": dict(text),
            "moral_lesson": dict(text), "chorus": dict(text),
            "vocab_words": {
                "type": "array", "items": {
                    "type": "object", "required": ["chinese", "english"],
                    "properties": {"chinese": dict(text), "english": dict(text)},
                },
            },
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["scene_number", "title", "background", "speaker", "cantonese", "english", "duration_sec", "characters"],
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "title": dict(text), "background": dict(text),
                        "speaker": {"type": "string"},
                        "cantonese": dict(text), "english": dict(text), "vocab_highlight": dict(text),
                        "duration_sec": {"type": "number"},
                        "scene_type": {"type": "string"},
                        "act": {"type": "integer"},
                        "chorus": dict(text), "interaction_prompt": dict(text),
                        "characters": {
                            "type": "array", "items": {
                                "type": "object", "required": ["name", "pose"],
                                "properties": {"name": dict(text), "pose": dict(text), "position": dict(text)},
                            },
                        },
                    },
                },
            },
        },
    }


class YoutubeMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=30)


PrivacyStatus = Literal["private", "unlisted", "public"]


def project_fingerprint(data: dict | ProjectData) -> str:
    """Compatibility alias; storage owns the media fingerprint contract."""
    from app.storage import media_input_fingerprint
    return media_input_fingerprint(data)
