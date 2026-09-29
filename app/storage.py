import json
import hashlib
import ntpath
import os
import re
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("KIDS_STUDIO_DATA_DIR", str(ROOT))).resolve()
PROJECTS_DIR = DATA_DIR / "projects"
_locks = {}
_locks_guard = threading.Lock()
_active_operations = {}


class StorageError(ValueError):
    pass


def validate_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", value):
        raise StorageError("Invalid project or asset identifier")
    if value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        raise StorageError("Reserved identifier")
    return value


def _project_key(project_id: str) -> str:
    return os.path.normcase(validate_id(project_id))


def _validate_project_spelling(project_id: str) -> str:
    project_id = validate_id(project_id)
    key = _project_key(project_id)
    if PROJECTS_DIR.is_dir():
        for entry in PROJECTS_DIR.iterdir():
            if os.path.normcase(entry.name) == key and entry.name != project_id:
                raise StorageError("Use the project's saved identifier with its original letter case")
    return project_id


def contained_path(base: Path, *parts) -> Path:
    base = Path(base).resolve()
    segments = []
    for part in parts:
        value = str(part)
        if not value or ntpath.isabs(value) or ntpath.splitdrive(value)[0]:
            raise StorageError("Absolute or empty paths are not allowed")
        for segment in re.split(r"[\\/]", value):
            if not segment or segment in {".", ".."} or any(c in segment for c in ':<>|?*\0'):
                raise StorageError("Invalid path component")
            if segment.endswith((" ", ".")) or any(ord(c) < 32 for c in segment):
                raise StorageError("Invalid path component")
            if segment.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
                raise StorageError("Reserved path component")
            segments.append(segment)
    result = base.joinpath(*segments).resolve()
    if not result.is_relative_to(base):
        raise StorageError("Path escapes its storage directory")
    return result


def project_path(project_id: str, *parts) -> Path:
    project_id = _validate_project_spelling(project_id)
    root = contained_path(PROJECTS_DIR, project_id)
    if root != PROJECTS_DIR.resolve() / project_id:
        raise StorageError("Project directories cannot alias another project")
    return contained_path(root, *parts)


def media_input_fingerprint(project_data) -> str:
    """Canonical identity + normalized scenes + subtitle/caption options only."""
    from app.models import ProjectData
    if isinstance(project_data, ProjectData):
        project_data = project_data.model_dump(mode="json", exclude_none=True)
    if project_data.get("id") and project_data.get("episode_id") and project_data["id"] != project_data["episode_id"]:
        raise StorageError("id and episode_id must identify the same project")
    project_id = _validate_project_spelling(project_data.get("id") or project_data.get("episode_id") or "")
    project = ProjectData.model_validate({"id": project_id, "scenes": project_data.get("scenes", [])})
    metadata = {
        "revision", "created_at", "updated_at", "rendered_video", "migration_warnings",
        "last_saved", "rendered_at", "input_fingerprint",
    }

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key not in metadata and not key.startswith("_")}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    options = {}
    for key in ("subtitle_options", "caption_options"):
        value = project_data.get(key)
        options[key] = {} if value is None else value
        if not isinstance(options[key], dict):
            raise StorageError(f"{key} must be an object")
    payload = {
        "project_id": project_id,
        "scenes": [scene.model_dump(mode="json", exclude_none=True) for scene in project.scenes],
        **options,
    }
    canonical = json.dumps(clean(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, data):
    path = Path(path)
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{uuid.uuid4().hex}.pending")
    try:
        with staging.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


@contextmanager
def project_lock(project_id: str):
    key = _project_key(project_id)
    with _locks_guard:
        lock = _locks.setdefault(key, threading.RLock())
    with lock:
        yield


@contextmanager
def project_operation(project_id: str):
    """Hold a deletion lease, not the project lock, during slow media work."""
    key = _project_key(project_id)
    with project_lock(project_id):
        if not project_path(project_id, "project.json").is_file():
            raise StorageError("Save this project before generating media")
        _active_operations[key] = _active_operations.get(key, 0) + 1
    try:
        yield
    finally:
        with project_lock(project_id):
            remaining = _active_operations.get(key, 1) - 1
            if remaining:
                _active_operations[key] = remaining
            else:
                _active_operations.pop(key, None)


def project_is_busy(project_id: str) -> bool:
    with project_lock(project_id):
        return bool(_active_operations.get(_project_key(project_id)))
