"""Offline artwork maintenance: stage by default, opt in to derived-art promotion.

Candidates live in <data>/artwork/candidates/assets, where <data> is
KIDS_STUDIO_DATA_DIR or project/data.
They are not runtime assets. --promote writes derived assets to project/assets;
master character artwork is never promotable through these maintenance scripts.
"""

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = PROJECT_ROOT / "assets"
_promote = False

# Direct execution and package imports must share the same explicit CLI decision.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if __name__ == "maintenance_guard":
    sys.modules.setdefault("scripts.maintenance_guard", sys.modules[__name__])
elif __name__ == "scripts.maintenance_guard":
    sys.modules.setdefault("maintenance_guard", sys.modules[__name__])


def configure_cli(argv=None):
    global _promote
    _promote = False
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Explicitly replace approved derived sprites/stickers/backgrounds. "
        "Without this flag, only candidates are written; character masters stay read-only.",
    )
    args = parser.parse_args(argv)
    _promote = args.promote
    return args


def _absolute(path):
    path = Path(path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    # Normalize '..' without following symlinks until containment is checked.
    return Path(os.path.abspath(path))


def candidate_root():
    data = _absolute(os.environ.get("KIDS_STUDIO_DATA_DIR") or PROJECT_ROOT / "data")
    root = data / "artwork" / "candidates" / "assets"
    resolved = root.resolve()
    if resolved.is_relative_to(ASSETS_ROOT.resolve()) or resolved.is_relative_to(
        (PROJECT_ROOT / "app").resolve()
    ):
        raise ValueError("Candidate storage must be outside approved assets and the app")
    if resolved != root:
        raise ValueError("Candidate storage must not traverse symlinks or junctions")
    return root


def output_path(path, *, promote=None):
    """Validate a destination and create only its permitted output directory.

    Apply at every save/copy boundary, including helpers called independently.
    Relative destinations are project-relative, not current-directory-relative.
    Already-staged destinations stay staged even when promotion is enabled.
    """
    target = _absolute(path)
    staged_root = candidate_root()
    if target.is_relative_to(staged_root):
        destination = target
    else:
        if not target.is_relative_to(ASSETS_ROOT):
            raise ValueError(f"Maintenance destination is not an asset path: {target}")
        relative = target.relative_to(ASSETS_ROOT)
        if len(relative.parts) < 2:
            raise ValueError("An asset category and filename are required")
        should_promote = _promote if promote is None else promote
        if should_promote:
            if relative.parts[0] not in {"sprites", "stickers", "backgrounds"}:
                raise ValueError("Master artwork is read-only; only derived assets may be promoted")
            destination = target
        else:
            destination = staged_root / relative
    if destination.resolve() != destination:
        raise ValueError("Maintenance destinations must not traverse symlinks or junctions")
    if destination.exists() and (
        not destination.is_file() or destination.stat().st_nlink > 1
    ):
        raise ValueError("Maintenance destination must be a regular, unshared file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination
