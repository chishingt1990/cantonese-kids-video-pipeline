# Cantonese Kids Video Studio

A local, parent-operated studio for illustrated Cantonese videos using approved
family artwork and recorded or explicitly selected synthetic narration.

## Run locally on Windows

Use Python 3.12 or 3.13, Node.js for frontend regression checks, and FFmpeg
(`ffmpeg` and `ffprobe` on PATH) for recording conversion and video export.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -c requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Keep the server bound to loopback; this is not a
multi-user or internet-hosted service. Do not expose it through a tunnel.
The existing workflow is Theme -> Script -> Staging -> Audio -> Render.
Run a single worker: project locks and the render queue are process-local.
`requirements-lock.txt` records the dependency versions used for this baseline.

Copy `.env.example` to `.env` or use Settings to configure a provider. A key being
configured is not proof that a provider supports a particular model or voice.
Parent-voice replication requires the adult speaker's sample and consent.
Export also needs a Cantonese-capable font; set `KIDS_STUDIO_CJK_FONT` if automatic
discovery cannot find one. Caption highlighting uses estimated timing, not
word-level speech alignment.

## Privacy and media ownership

- Recordings, credentials, generated media, and working data must remain private
  and out of Git. Voice sample files are ignored; supply your own locally.
- Previously published recordings can remain in Git history or downloaded copies.
  Removing current tracking does not revoke those copies.
- Text generation, stock TTS, and voice replication can send content to their
  selected external providers. Local files do not imply offline processing.
- Audio and rendered videos belong to one project. Old globally named narration
  must be regenerated rather than guessed or reassigned to another episode.
- A failed parent-voice request must not silently switch to another speaker.
- YouTube publishing is a separate explicit action. Unlisted links are not
  private; use private visibility for family material.

## Artwork and generation

The current character/background tools transform existing artwork: they select
poses and presets, recolor clothing, and apply limited overlays. They are not
general text-to-image or video-to-video generators.

Keep approved master artwork separate from generated candidates. Save the exact
preview you reviewed; changing its prompt requires a new preview. Unsupported
assets or edits should be reported rather than replaced with unrelated content.

Generated previews and custom art live in `data\artwork\`, or
`%KIDS_STUDIO_DATA_DIR%\artwork\` when configured. Maintenance scripts write to
that directory's `candidates\assets\` tree by default. `--promote` is an explicit
operation to replace derived sprites/backgrounds/stickers; inspect candidates
first. Master character artwork stays protected. Some legacy maintenance scripts
still require locally supplied source paths and are not part of the app workflow.

The planned V2 is a separate branch and workflow. Source-video adaptation and
faithful motion-preserving restyling are different capabilities; neither is
provided by the current YouTube publishing integration.

## Offline regression checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests\frontend.test.cjs
```

Regression fixtures use temporary storage and mocked providers. No API keys,
paid generation, or YouTube publication are needed.
The GitHub Actions workflow runs these checks on Windows without provider secrets.

`test_full_system.py` is the historical asset/live-provider suite. It modifies
assets and has obsolete global-media assumptions, so it is disabled by default.
If investigating those historical checks, use only a disposable checkout and
explicitly set `KIDS_STUDIO_RUN_LEGACY_TESTS=1`; do not run it against family data.
