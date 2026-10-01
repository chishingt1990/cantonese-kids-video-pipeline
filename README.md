# cantonese-kids-video-pipeline

## Approved artwork library

Open [the asset portal](generated-asset-portal.html) from a local clone, or visit
`/asset-library` when running the studio. GitHub's file view shows HTML source;
download/clone the repository to use the interactive portal.

The release contains 60 approved assets: six twin action poses, six Cantonese
word badges, and 48 illustrated props. Of these, 52 PNGs are additions and eight
are intentional replacements. Previous versions of the replaced props remain
in Git history. Existing backgrounds and character identity anchors are unchanged.

`config/artwork_release_v1.json` records production/source hashes, processing and
replacement provenance. The portal uses relative repository links and embedded
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
python -m unittest test_artwork_release
```

The focused artwork tests isolate cache writes in temporary directories and do
not call generation providers. The existing `test_full_system.py` also includes
a live TTS test and file-writing tests; run it in a disposable copy when testing
artwork without changing your working library.
