# Zany Test Prep Avatar Dataset

This repository contains the production-ready avatar customization dataset for the Zany Test Prep Flutter app.

## Source Of Truth

Use this JSON catalog at runtime:

`assets/avatar/manifest/avatar_catalog.json`

The catalog contains:

- 10 starter avatars
- 100 advanced avatars
- 272 unlockable items
- 30 pet companions
- four side slots for pets and floating props
- XP costs, rarity, unlock metadata, anchors, scales, z-index values, and preview paths

All app-facing PNG assets are 512x512 RGBA PNGs with transparent alpha.

## Flutter Integration

Add the asset paths from:

`manifest/flutter_pubspec_snippet.yaml`

Use the example model and renderer as the integration reference:

- `flutter_example/avatar_pack_catalog.dart`
- `flutter_example/avatar_preview.dart`

Load the catalog, store equipped asset IDs, and render layers by `z_index`. Do not hardcode item definitions in widgets.

## Slots

Worn slots:

- `headwear`
- `eyewear`
- `face_accessory`
- `ear_accessory`
- `neck_accessory`
- `chest_badge`
- `jacket_or_top_overlay`
- `back_or_aura`
- `background_frame`

Side slots:

- `side_left_1`
- `side_left_2`
- `side_right_1`
- `side_right_2`

Side-slot assets are pets or floating props. They are independent layers around the avatar and do not align to hands.

## Validation

Run:

```bash
python3 scripts/validate_avatar_catalog.py
python3 scripts/qa_avatar_visuals.py
python3 -m unittest tests/test_avatar_catalog.py
```

These checks validate manifest paths, PNG alpha/dimensions, XP ranges, slot compatibility, pet side-slot rules, loadout behavior, and basic visual crop sanity.
