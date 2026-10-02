# cantonese-kids-video-pipeline

## Approved artwork library

Open [the asset portal](generated-asset-portal.html) from a local clone, or visit
`/asset-library` when running the studio. GitHub's file view shows HTML source;
download/clone the repository to use the interactive portal.

The portal contains **374 assets**: the original 60-asset release, 73 glyph-shaped
phonics stickers (A-Z, a-z, 0-20), 56 additional toys/vehicles/fruit/vegetables/dishes,
53 approved family-expansion v3 sprites (7 individual relatives, 34 additional solo
poses for mom/dad/grandparents/auntie/cousins, and 12 contact composite sprites for
hug / handholding / adult-carrying-child), and 32 family-interactions v4 contact
composites (26 twin-focused 2- and 3-person interactions plus 6 four-person family
groups covering mom+dad+twins and both grandparent pairs with the twins; actions
include hug, holding hands, holding both hands, carrying child, high five, passing
toy, reading together, building blocks together, and group play), plus 100 library
expansion v5 stickers (20 vehicles, 20 toys, 12 shapes, 28 food/fruit items, and
20 animals). The phonics update
replaces the six old boxed ABC/123 PNGs under compatible IDs and adds 67 glyph PNGs.
The prop expansion adds 56 PNGs. Eight unrecovered prop requests and one unavailable
family-expansion job (`paternal_grandpa_seated_storytelling_r01`) are explicitly
excluded, not represented as completed assets. Existing backgrounds and character
identity anchors are unchanged.

`config/artwork_release_v1.json`, `config/phonics_release_v2.json`,
`config/props_release_v2.json`, `config/family_release_v3.json`,
`config/family_interactions_v4.json`, and `config/library_expansion_v5.json`
record the released artwork and hashes.
Each manifest lists its excluded requests. The portal uses relative repository
links and embedded previews, without private local paths or Copilot conversation
links. Raw generator downloads and superseded trials are not included.

Rebuild the portal after changing any approved release manifest:

```powershell
python scripts\build_asset_portal.py
```

Rebuild either family release from the approved candidates (idempotent):

```powershell
python scripts\build_family_release_v3.py
python scripts\build_family_interactions_v4.py
```

Read [STYLE_GUIDE.md](STYLE_GUIDE.md) before creating or replacing artwork.
Approved props are loaded from the release manifest into the sticker catalog;
they must not be regenerated from placeholder drawing recipes. Missing approved
prop PNGs produce an explicit error.

## Artwork integration tests

Install the dependencies in `requirements.txt` in your environment, plus the
HTTP test-client dependency used by the existing tests (`httpx`). Then run:

```powershell
python -m unittest test_artwork_release test_phonics_release test_props_release test_family_release test_family_interactions_release test_library_expansion_release test_legacy_sticker_cleanup
```

The focused artwork test uses a temporary asset tree. The phonics and prop tests
load the app (which can generate missing cached stickers), and the phonics test
rebuilds the portal. Run suites in a disposable copy to avoid changing your working
library. None of these three suites calls a generation provider. The existing
`test_full_system.py` additionally includes a live TTS test.
