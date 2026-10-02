"""Reproducible build of the family-interactions release v4.

Reads two approved batch states:
* ``design/2026-10-02-twins-interactions/twins-batch-26.json`` — 26 twin-focused
  interaction composites approved by the user on 2026-10-02 08:30 PDT ('these
  are great'); included 2- and 3-person contacts starring Levi and Luca.
* ``design/2026-10-02-family-groups/group-batch-6.json`` — 6 four-person family
  group composites. The user replied 'keep going' at 08:59 PDT after the
  group review HTML opened; this script records that intent accurately and
  does NOT claim prior public publication.

Both batches arrived as 1254x1254 RGBA PNGs. The script normalises each
candidate using the family_release_v3 convention (alpha<=2 to 0, alpha>=250
to 255, no RGB change, no resample, crop to alpha bbox, add eight transparent
pixels on every side), writes 32 new primary runtime PNGs under
``assets/sprites/contact_<members>_<action>.png``, and emits
``config/family_interactions_v4.json`` as the provenance manifest.

Collisions with ``config/family_release_v3.json`` IDs are rejected at build
time so the v3 release stays byte-identical and immutable.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parent
TWINS_BATCH_PATH = WORKSPACE / "design" / "2026-10-02-twins-interactions" / "twins-batch-26.json"
GROUPS_BATCH_PATH = WORKSPACE / "design" / "2026-10-02-family-groups" / "group-batch-6.json"
V3_MANIFEST_PATH = REPO / "config" / "family_release_v3.json"
V4_MANIFEST_PATH = REPO / "config" / "family_interactions_v4.json"
SPRITES_DIR = REPO / "assets" / "sprites"

# Scale class per runtime character ID. Mirrors family_catalog's assumptions
# so we can compute the composite class without importing the FastAPI app.
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
    "dog": "pet",
}

# Score the four scale classes so the composite picks the "tallest" member.
# Matches the v3 build script behaviour exactly.
_SCALE_SCORE: Dict[str, int] = {"adult": 3, "older_child": 2, "toddler": 1, "pet": 0}


# Human-readable action labels for the new contact actions introduced in v4.
# Reused by the portal, the characters router display names, and the director
# system prompt. ``hug`` is already labelled by v3's ``contact_action_labels``
# (aggregation is first-wins) so we leave the family v3 wording authoritative
# for the shared actions.
NEW_ACTION_LABELS: Dict[str, str] = {
    "holding_hands": "Holding Hands",
    "holding_both_hands": "Holding Both Hands",
    "reading_book_together": "Reading a Book Together",
    "passing_toy": "Passing a Toy",
    "high_five": "High Five",
    "reading_together": "Reading Together",
    "building_blocks_together": "Building Blocks Together",
    "play": "Playing Together",
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

    Mirrors the family_release_v3 production processing exactly:
    alpha<=2 -> 0, alpha>=250 -> 255, no RGB changes, no resample, crop to
    alpha bbox, then add eight fully transparent pixels on every side.
    """
    with Image.open(source) as image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        else:
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


def _age_role_for(batch_character_id: str, job: dict) -> str:
    """Pick the member's declared age role from the batch refmetadata/roles."""
    for ref in job.get("refmetadata", []):
        for role in ref.get("roles", []):
            if role.get("character_id") == batch_character_id:
                age = role.get("age_role")
                if age:
                    return age
    # Fall back from the scale class so adult/toddler is at least consistent.
    cls = SCALE_CLASS.get(batch_character_id, "toddler")
    return "adult" if cls == "adult" else "child"


def _composite_scale_class(member_ids: List[str]) -> str:
    """Pick the "tallest" scale class across all members. Preserves the v3
    semantic that an adult + child composite sizes to the adult base, while
    twin-pair, cousin-only or Ben+twin composites stay at the correct
    child/toddler size instead of defaulting to adult.
    """
    best = ("toddler", -1)
    for mid in member_ids:
        cls = SCALE_CLASS.get(mid, "toddler")
        score = _SCALE_SCORE.get(cls, 1)
        if score > best[1]:
            best = (cls, score)
    return best[0]


def _asset_id_and_path(member_ids: List[str], action: str) -> Tuple[str, str]:
    slug = "_".join(member_ids)
    asset_id = f"contact_{slug}_{action}"
    runtime_path = f"assets/sprites/{asset_id}.png"
    return asset_id, runtime_path


def _collect_jobs(batch_path: Path) -> Tuple[dict, List[dict], List[dict]]:
    """Load a batch state and partition into downloaded vs. excluded jobs."""
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    workspace_from_batch = Path(batch["workspace_root"])
    if workspace_from_batch.resolve() != WORKSPACE.resolve():
        raise ValueError(
            f"{batch_path.name} workspace_root {workspace_from_batch} does not match "
            f"resolved workspace {WORKSPACE}; refusing to overwrite assets."
        )
    downloaded, excluded = [], []
    for job in batch["jobs"]:
        if job.get("state") == "downloaded":
            downloaded.append(job)
        else:
            excluded.append({
                "job_id": job["job_id"],
                "state": job.get("state"),
                "character_ids": job.get("character_ids", []),
                "action": job.get("action"),
                "reason": "Not downloaded; sprite bytes are not present locally.",
            })
    return batch, downloaded, excluded


def _normalize_approval(batch: dict, job: dict, batch_label: str) -> str:
    """Pick an approval statement that reflects the user's wording honestly.

    The twins batch has explicit 'these are great' visual acceptance. The groups batch has
    only 'Approve all six' at generation time and 'keep going' after the local
    review opened — we record both quotes without claiming any public push
    approval, which belongs to a later separate step.
    """
    approval = job.get("approval_evidence") or batch.get("authorization", {}).get("approval_evidence", "")
    if batch_label == "twins":
        return (
            "User reply 'these are great' on 2026-10-02 08:30 PDT, following the "
            "exact outbound preview recorded in approval_evidence (26 twin-focused "
            "interaction composites with reference filenames and sha256). This "
            "approval covers both library grouping and image generation; public "
            "publication is handled as a separate step."
        )
    return (
        "User reply 'A. Approve all six' on 2026-10-02 08:37 PDT authorised the "
        "six family-group generations; the local group review HTML opened at "
        "08:59 PDT and the user replied 'keep going' to continue local prep. "
        "This manifest records approval for local integration only — public "
        "publication is a separate step the user handles after reviewing the "
        "combined preview."
    )


def build(write: bool = True) -> dict:
    v3 = json.loads(V3_MANIFEST_PATH.read_text(encoding="utf-8"))
    v3_asset_ids = {a["id"] for a in v3["assets"]}
    v3_runtime_paths = {a["runtime_path"] for a in v3["assets"]}
    for alias_list in (a.get("alias_runtime_paths", []) for a in v3["assets"]):
        v3_runtime_paths.update(alias_list)

    jobs: List[Tuple[dict, dict, str]] = []
    twins_batch, twins_downloaded, twins_excluded = _collect_jobs(TWINS_BATCH_PATH)
    groups_batch, groups_downloaded, groups_excluded = _collect_jobs(GROUPS_BATCH_PATH)
    jobs.extend((twins_batch, j, "twins") for j in twins_downloaded)
    jobs.extend((groups_batch, j, "groups") for j in groups_downloaded)

    assets: List[dict] = []
    seen_ids: set = set()
    for batch, job, batch_label in jobs:
        source = WORKSPACE / job["candidate_output_relative_path"]
        if not source.is_file():
            raise FileNotFoundError(f"Downloaded candidate missing: {source}")
        actual_source_sha = _sha256(source)
        if actual_source_sha != job["source_sha256"]:
            raise ValueError(
                f"Source hash mismatch for {job['job_id']}: "
                f"expected {job['source_sha256']}, got {actual_source_sha}"
            )
        member_ids = list(job["character_ids"])
        action = job["action"]
        asset_id, runtime_path = _asset_id_and_path(member_ids, action)
        # Hard collision guard: v4 must never clobber a v3 asset ID or runtime
        # file. The v3 release is immutable per the user's instructions.
        if asset_id in v3_asset_ids:
            raise ValueError(
                f"Collision with v3 asset ID {asset_id!r} — refusing to overwrite."
            )
        if runtime_path in v3_runtime_paths:
            raise ValueError(
                f"Collision with v3 runtime path {runtime_path!r} — refusing to overwrite."
            )
        if asset_id in seen_ids:
            raise ValueError(f"Duplicate asset ID within v4: {asset_id!r}")
        seen_ids.add(asset_id)

        destination = REPO / runtime_path
        if write:
            result = _normalize_png(source, destination)
        else:
            tmp = destination.with_suffix(".tmp")
            result = _normalize_png(source, tmp)
            tmp.unlink()

        with Image.open(source) as source_image:
            source_size = list(source_image.size)

        members = [
            {
                "runtime_character_id": mid,
                "age_role": _age_role_for(mid, job),
            }
            for mid in member_ids
        ]
        scale_class = _composite_scale_class(member_ids)

        ref_relative_paths: List[str] = []
        ref_shas: List[str] = []
        for ref in job.get("refmetadata", []):
            # refmetadata paths are absolute workspace paths; store repo-relative.
            try:
                rel = str(Path(ref["path"]).relative_to(REPO)).replace("\\", "/")
            except ValueError:
                rel = ref.get("filename") or Path(ref["path"]).name
            ref_relative_paths.append(rel)
            ref_shas.append(ref["sha256"])

        asset = {
            "id": asset_id,
            "kind": "sprite",
            "runtime_path": result.runtime_path,
            "alias_runtime_paths": [],
            "source_filename": Path(job["candidate_output_relative_path"]).name,
            "source_sha256": actual_source_sha,
            "source_size": source_size,
            "primary_reference": {
                "repository_relative_paths": ref_relative_paths,
                "sha256_list": ref_shas,
            },
            "prompt_sha256": job["prompt_sha256"],
            "provider": "Microsoft 365 Copilot Designer",
            "processing": result.processing,
            "size": list(result.size),
            "mode": "RGBA",
            "sha256": result.sha256,
            "pose": action,
            "visual_status": "user_approved",
            "category": "contact",
            "action": action,
            "members": members,
            "member_count": len(members),
            "scale_class": scale_class,
            "library_groups": list(job.get("library_groups", [])),
            "source_batch": batch_label,
            "approval_statement": _normalize_approval(batch, job, batch_label),
        }
        assets.append(asset)

    excluded = []
    for src_label, src_excluded in (("twins", twins_excluded), ("groups", groups_excluded)):
        for item in src_excluded:
            item = dict(item)
            item["source_batch"] = src_label
            excluded.append(item)

    manifest = {
        "schema_version": 1,
        "release_id": "family_interactions_v4",
        "status": "approved_local_integration",
        "approval": (
            "Twins batch: user said 'these are great' on 2026-10-02 08:30 PDT for the 26 "
            "twin-focused interactions. Groups batch: user said 'A. Approve all six' at "
            "08:37 PDT and 'keep going' at 08:59 PDT after the local group-review HTML "
            "opened. The groups batch has not been publicly published; public "
            "publication of this v4 release is a separate step the user handles after "
            "reviewing the combined preview."
        ),
        "scope": (
            "32 approved family-interaction composite sprites: 26 twin-focused (2- and "
            "3-person) interactions and 6 four-person family-group composites. "
            "All v3 assets stay byte-identical; v4 is additive."
        ),
        "note": (
            "Provenance manifest, not the runtime catalog. "
            "app/services/family_catalog.py aggregates this file with "
            "family_release_v3.json so individual pose vocabularies and contact IDs "
            "from both releases are visible to the director, characters router, "
            "render service and asset portal."
        ),
        "scale_classes": {
            "adult": {"base_height_px": 760},
            "older_child": {"base_height_px": 640},
            "toddler": {"base_height_px": 520},
            "pet": {"base_height_px": 320},
        },
        "pose_labels": {},
        "contact_action_labels": NEW_ACTION_LABELS,
        "excluded_jobs": excluded,
        "assets": assets,
    }
    if write:
        V4_MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return manifest


if __name__ == "__main__":
    manifest = build(write=True)
    print(f"Wrote {V4_MANIFEST_PATH.relative_to(REPO)} with {len(manifest['assets'])} assets")
    if manifest["excluded_jobs"]:
        print(f"Excluded {len(manifest['excluded_jobs'])} job(s)")
    else:
        print("No excluded jobs (all approved jobs downloaded).")
