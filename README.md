# cantonese-kids-video-pipeline

## Approved artwork library

Open [the asset portal](generated-asset-portal.html) from a local clone, or visit
`/asset-library` when running the studio. GitHub's file view shows HTML source;
download/clone the repository to use the interactive portal.

The portal contains **189 assets**: the original 60-asset release, 73 glyph-shaped
phonics stickers (A-Z, a-z, 0-20), and 56 additional toys, vehicles, fruit,
vegetables and dishes. The phonics update replaces the six old boxed ABC/123
PNGs under compatible IDs and adds 67 glyph PNGs. The prop expansion adds 56 PNGs.
Eight unrecovered generation requests are explicitly excluded, not represented
as completed assets. Existing backgrounds and character identity anchors are unchanged.

`config/artwork_release_v1.json`, `config/phonics_release_v2.json`, and
`config/props_release_v2.json` record the released artwork and hashes.
The prop manifest lists the eight excluded requests. The portal uses relative repository links and embedded
previews, without private local paths or Copilot conversation links. Raw generator
downloads and superseded trials are not included.

Rebuild the portal after changing the approved release manifest:

```powershell
python scripts\build_asset_portal.py
```

Read [STYLE_GUIDE.md](STYLE_GUIDE.md) before creating or replacing artwork.
Approved props are loaded from the release manifest into the sticker catalog;
they must not be regenerated from placeholder drawing recipes. Missing approved
prop PNGs produce an explicit error.

## Artwork integration tests

Install the dependencies in `requirements.txt` in your environment, plus the
HTTP test-client dependency used by the existing tests (`httpx`). Then run:

```powershell
python -m unittest test_artwork_release test_phonics_release test_props_release
```

The focused artwork test uses a temporary asset tree. The phonics and prop tests
load the app (which can generate missing cached stickers), and the phonics test
rebuilds the portal. Run suites in a disposable copy to avoid changing your working
library. None of these three suites calls a generation provider. The existing
`test_full_system.py` additionally includes a live TTS test.
