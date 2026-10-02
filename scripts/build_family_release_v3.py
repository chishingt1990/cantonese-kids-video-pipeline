"""Reproducible build of the family-expansion release v3.

Reads the approved batch state at
``design/2026-10-01-family-expansion/family-batch-54.json`` (relative to the
workspace root, which is the Clawpilot folder that contains the repository),
normalises each downloaded candidate PNG (alpha<=2 to 0, alpha>=250 to 255,
crop to alpha bbox, add eight transparent pixels on every side, no RGB or
geometric change), writes 53 primary runtime PNGs under ``assets/sprites/`` and
seven byte-identical ``_standing.png`` anchor aliases for the standalone
reference identities, and emits ``config/family_release_v3.json`` as the
provenance manifest.

The job ``paternal_grandpa_seated_storytelling_r01`` (state
``submission_uncertain``) is explicitly excluded. Original candidate files are
not modified. The script is idempotent: re-running produces identical bytes.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parent
BATCH_PATH = WORKSPACE / "design" / "2026-10-01-family-expansion" / "family-batch-54.json"
MANIFEST_PATH = REPO / "config" / "family_release_v3.json"
SPRITES_DIR = REPO / "assets" / "sprites"

# Config character id used as the runtime filename / id for each batch character id.
# Keeps compatibility with ``config/characters.json`` and avoids inventing new IDs
# that would silently drift from the project character catalog.
RUNTIME_ID_FOR_BATCH_ID: Dict[str, str] = {
    "paternal_grandpa": "paternal_grandpa",
    "paternal_grandma": "paternal_grandma",
    "maternal_grandpa": "maternal_grandpa",
    "maternal_grandma": "maternal_grandma",
    "auntie": "aunt_sister",
    "cousin_ryan": "cousin_ryan",
    "cousin_ben": "cousin_younger",
    # Twin kids appear only as contact participants (not as standalone jobs).
    "levi": "levi",
    "luca": "luca",
    # Already-existing adults participate in contacts.
    "mom": "mom",
    "dad": "dad",
}

# Scale class per runtime id. Drives render_service base-height selection
# and prevents misclassifying new adult-coded relatives as toddlers.
SCALE_CLASS: Dict[str, str] = {
    "mom": "adult",
    "dad": "adult",
    "paternal_grandpa": "adult",
    "paternal_grandma": "adult",
    "maternal_grandpa": "adult",
    "maternal_grandma": "adult",
    "aunt_sister": "adult",
    "cousin_ryan": "older_child",
    "cousin_younger": "toddler",
    "levi": "toddler",
    "luca": "toddler",
}

# Human-readable pose labels for new poses used in the characters router and
# the asset portal. Existing labels in app/routers/characters.py stay authoritative;
# this dict only covers the new vocabulary introduced by this release.
POSE_LABELS: Dict[str, str] = {
    "standing": "🧍 Standing Reference",
    "waving": "👋 Waving Hello",
    "seated_storytelling": "📖 Seated Storytelling",
    "offering_food_or_gift": "🎁 Offering Food / Gift",
    "crouching_to_talk": "🧎 Crouching to Talk",
    "playing_helping": "🧸 Playing & Helping",
    "showing_toy": "🎲 Showing a Toy",
    "passing_toy": "🤝 Passing a Toy",
    "sitting_playing": "🧘 Sitting & Playing",
    "listening_crouched": "🧎 Listening (Crouched)",
    "reading_book": "📚 Reading a Book",
    "offering_object": "🤲 Offering an Object",
    "open_handed_explaining": "🗣️ Open-Handed Explaining",
    "comforting_open_arms": "🤗 Comforting Open Arms",
    "walking": "🚶 Walking",
    "hug": "🤗 Shared Hug",
    "handholding": "🤝 Holding Hands",
    "carrying_child": "👶 Carrying Child",
}

ACTION_LABELS: Dict[str, str] = {
    "hug": "Hug",
    "handholding": "Hand-holding",
    "carrying_child": "Adult Carrying Child",
}


@dataclass
class NormalizationResult:
    runtime_path: str
    sha256: str
    size: Tuple[int, int]
    processing: Dict[str, object]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_png(source: Path, destination: Path) -> NormalizationResult:
    """Apply the sprite-release alpha normalization and padding convention.

    Mirrors the artwork_release_v1 production processing:
    alpha<=2 -> 0, alpha>=250 -> 255, no RGB changes, crop to alpha bbox,
    then add eight fully transparent pixels on every side.
    """
    with Image.open(source) as image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        else:
            # Force a fresh copy so getdata/putdata operate on an unlocked image.
            image = image.copy()

        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        le_2 = sum(histogram[: 2 + 1])
        ge_250 = sum(histogram[250:])
        normalized_alpha = alpha.point(lambda a: 0 if a <= 2 else (255 if a >= 250 else a))
        image.putalpha(normalized_alpha)

        bbox = normalized_alpha.getbbox()
        if bbox is None:
            raise ValueError(f"Normalized alpha has no opaque pixels: {source}")
        cropped = image.crop(bbox)
        padded = Image.new("RGBA", (cropped.width + 16, cropped.height + 16), (0, 0, 0, 0))
        padded.paste(cropped, (8, 8))

    destination.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    padded.save(buffer, format="PNG", optimize=True)
    data = buffer.getvalue()
    destination.write_bytes(data)
    return NormalizationResult(
        runtime_path=str(destination.relative_to(REPO)).replace("\\", "/"),
        sha256=hashlib.sha256(data).hexdigest(),
        size=(padded.width, padded.height),
        processing={
            "rgb_changes": False,
            "alpha_le_2_to_zero_pixels": int(le_2),
            "alpha_ge_250_to_255_pixels": int(ge_250),
            "source_crop_ltrb": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
            "transparent_padding_each_side": 8,
            "resampling": "none",
        },
    )


def _runtime_filename_for_job(job: dict) -> Tuple[str, str, Optional[str], Optional[str], List[str]]:
    """Return (asset_id, runtime_path, character_id, pose_id, alias_runtime_paths)
    for a downloaded job. ``character_id`` and ``pose_id`` are set for solo jobs;
    for contact jobs ``character_id`` is None and the contact-specific metadata
    is handled by the caller."""
    category = job["category"]
    pose = job["pose"]
    batch_chars = list(job["character_ids"])
    if category == "solo":
        runtime_char = RUNTIME_ID_FOR_BATCH_ID[batch_chars[0]]
        pose_id = "default" if job.get("is_standalone_reference") else pose
        asset_id = f"sprite_{runtime_char}_{pose_id}"
        runtime_name = f"{runtime_char}_{pose_id}.png"
        aliases: List[str] = []
        if job.get("is_standalone_reference"):
            # Preserve a stable ``_standing.png`` anchor alongside ``_default.png``
            # so explicit "standing" pose selections still resolve to the approved
            # reference bytes.
            aliases.append(f"assets/sprites/{runtime_char}_standing.png")
        return asset_id, f"assets/sprites/{runtime_name}", runtime_char, pose_id, aliases
    if category == "contact":
        runtime_members = [RUNTIME_ID_FOR_BATCH_ID[b] for b in batch_chars]
        slug = "_".join(runtime_members)
        asset_id = f"contact_{slug}_{pose}"
        runtime_name = f"contact_{slug}_{pose}.png"
        return asset_id, f"assets/sprites/{runtime_name}", None, pose, []
    raise ValueError(f"Unknown category: {category}")


def build(write: bool = True) -> dict:
    batch = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
    jobs = batch["jobs"]

    workspace_from_batch = Path(batch["workspace_root"])
    if workspace_from_batch.resolve() != WORKSPACE.resolve():
        raise ValueError(
            f"family-batch-54.json workspace_root {workspace_from_batch} does not match "
            f"the resolved workspace {WORKSPACE}; refusing to overwrite assets."
        )

    excluded: List[dict] = []
    downloaded: List[dict] = []
    for job in jobs:
        if job["state"] == "downloaded":
            downloaded.append(job)
        else:
            excluded.append({
                "job_id": job["job_id"],
                "state": job["state"],
                "character_ids": job["character_ids"],
                "pose": job["pose"],
                "reason": "Not downloaded; sprite bytes are not present locally.",
            })

    assets: List[dict] = []
    for job in downloaded:
        source = WORKSPACE / job["candidate_output_relative_path"]
        if not source.is_file():
            raise FileNotFoundError(f"Downloaded candidate missing: {source}")
        actual_source_sha = _sha256(source)
        if actual_source_sha != job["source_sha256"]:
            raise ValueError(
                f"Source hash mismatch for {job['job_id']}: "
                f"expected {job['source_sha256']}, got {actual_source_sha}"
            )
        asset_id, runtime_path, char_id, pose_id, alias_paths = _runtime_filename_for_job(job)
        destination = REPO / runtime_path
        if write:
            result = _normalize_png(source, destination)
            for alias in alias_paths:
                alias_dest = REPO / alias
                alias_dest.write_bytes(destination.read_bytes())
        else:
            # Dry-run: still normalize into a bytes buffer so we can report hashes.
            tmp = destination.with_suffix(".tmp")
            result = _normalize_png(source, tmp)
            tmp.unlink()

        with Image.open(source) as source_image:
            source_size = list(source_image.size)
        asset = {
            "id": asset_id,
            "kind": "sprite",
            "runtime_path": result.runtime_path,
            "alias_runtime_paths": alias_paths,
            "source_filename": Path(job["candidate_output_relative_path"]).name,
            "source_sha256": actual_source_sha,
            "source_size": source_size,
            "primary_reference": {
                "repository_relative_paths": [
                    str(Path(ref["path"]).relative_to(REPO)).replace("\\", "/")
                    for ref in job["reference_files"]
                ],
                "sha256_list": [ref["sha256"] for ref in job["reference_files"]],
            },
            "prompt_sha256": job["prompt_sha256"],
            "provider": "Microsoft 365 Copilot Designer",
            "processing": result.processing,
            "size": list(result.size),
            "mode": "RGBA",
            "sha256": result.sha256,
            "pose": pose_id,
            "visual_status": "user_approved",
        }
        if job["category"] == "solo":
            asset["category"] = "solo"
            asset["character_id"] = char_id
            asset["is_standalone_reference"] = bool(job.get("is_standalone_reference"))
            asset["scale_class"] = SCALE_CLASS[char_id]
        else:
            asset["category"] = "contact"
            asset["action"] = pose_id
            members = []
            for batch_cid in job["character_ids"]:
                members.append({
                    "runtime_character_id": RUNTIME_ID_FOR_BATCH_ID[batch_cid],
                    "age_role": next(
                        role["age_role"]
                        for ref in job["reference_files"]
                        for role in ref.get("roles", [])
                        if role["character_id"] == batch_cid
                    ) if any(role["character_id"] == batch_cid
                             for ref in job["reference_files"]
                             for role in ref.get("roles", [])) else None,
                })
            asset["members"] = members
            # Composite scale is driven by the tallest member so adult-child
            # pairs are not rendered as toddler-size clusters.
            tallest = max(members, key=lambda m: {"adult": 3, "older_child": 2, "toddler": 1, "pet": 0}
                          .get(SCALE_CLASS.get(m["runtime_character_id"], "toddler"), 1))
            asset["scale_class"] = SCALE_CLASS[tallest["runtime_character_id"]]
        assets.append(asset)

    manifest = {
        "schema_version": 1,
        "release_id": "family_release_v3",
        "status": "approved_complete_release",
        "approval": (
            "User reply 'these are great. push to main' on 2026-10-02 01:03 PDT after "
            "visual approval of 53 of 54 approved family-expansion jobs; one job "
            "(paternal_grandpa_seated_storytelling_r01) remained in submission_uncertain "
            "state and is excluded from this release manifest."
        ),
        "scope": (
            "53 approved family sprites: 7 standalone standing identity references "
            "(paternal_grandpa, paternal_grandma, maternal_grandpa, maternal_grandma, "
            "aunt_sister, cousin_ryan, cousin_younger), 34 additional solo poses, and "
            "12 contact sprites (hug, handholding, carrying_child)."
        ),
        "note": (
            "Provenance manifest, not the runtime catalog. Runtime catalogs load this "
            "file via app/services/family_catalog.py. Original candidate PNGs and the "
            "191MB private review.html remain outside the repository."
        ),
        "scale_classes": {
            "adult": {"base_height_px": 760},
            "older_child": {"base_height_px": 640},
            "toddler": {"base_height_px": 520},
            "pet": {"base_height_px": 320},
        },
        "pose_labels": POSE_LABELS,
        "contact_action_labels": ACTION_LABELS,
        "excluded_jobs": excluded,
        "assets": assets,
    }
    if write:
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return manifest


if __name__ == "__main__":
    manifest = build(write=True)
    print(f"Wrote {MANIFEST_PATH.relative_to(REPO)} with {len(manifest['assets'])} assets")
    print(f"Excluded {len(manifest['excluded_jobs'])} job(s): "
          + ", ".join(e["job_id"] for e in manifest["excluded_jobs"]))
