# Asset Pack Summary

Style version: `teen_modular_v1`

## Catalog Counts

- Avatars: 110
- Starter avatars: 10
- Advanced avatars: 100
- Items: 272
- Pets: 30
- Total catalog assets: 412

## Item Categories

- `headwear`: 40
- `eyewear`: 30
- `face_accessory`: 25
- `ear_accessory`: 24
- `neck_accessory`: 25
- `chest_badge`: 30
- `jacket_overlay`: 24
- `back_aura`: 25
- `background_frame`: 24
- `floating_props`: 25

## Runtime Files

- `assets/avatar/manifest/avatar_catalog.json`
- `assets/avatar/manifest/avatar_catalog.schema.json`
- `assets/avatar/manifest/sprite_atlas.json`
- `manifest/flutter_avatar_catalog.json`
- `manifest/flutter_pubspec_snippet.yaml`

## QA Status

The dataset is intended to pass:

```bash
python3 scripts/validate_avatar_catalog.py
python3 scripts/qa_avatar_visuals.py
python3 -m unittest tests/test_avatar_catalog.py
```

All app-facing PNG assets are expected to be 512x512 RGBA PNGs with transparent alpha.
