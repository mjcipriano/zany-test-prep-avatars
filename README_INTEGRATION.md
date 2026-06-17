# Zany Test Prep Avatar Dataset

This repository contains the production-ready avatar customization dataset for the Zany Test Prep Flutter app.

## Source Of Truth

Use this JSON catalog at runtime:

`assets/avatar/manifest/avatar_catalog.json`

The catalog contains:

- 10 starter avatars
- 100 advanced avatars
- 272 unlockable items
- 90 pet companions
- four side slots for pets and floating props
- XP costs, rarity, unlock metadata, placement targets, sprite sizes, z-index values, and preview paths

Base avatar PNGs are 512x512 RGBA. Item and pet PNGs are tightly trimmed RGBA sprites. The catalog keeps `canvas_size: 512x512` as the virtual composition frame and exposes each trimmed PNG's real bounds in `sprite_size`.

## Placement Contract

Catalog `schema_version: 2.1.0` uses `placement_contract_version: target_box_v1`.

Render each layer this way:

1. Sort equipped layers and the base avatar by `z_index`.
2. Render the base avatar full-frame in the 512x512 virtual canvas.
3. For item and pet layers, choose `asset.placement.targets_by_slot[equippedSlot]` when present; otherwise use `asset.placement.target`.
4. Center the trimmed sprite at `target.cx,target.cy` in normalized 0..1 canvas space.
5. Fit the sprite inside `target.w,target.h` using `BoxFit.contain`, preserving aspect ratio.

`scale` remains present for older builds. In v2.1 it is defined as an optional multiplier on `placement.target.w/h`; new integrations can usually leave it at `1.0`.

## Flutter Integration

Add the asset paths from:

`manifest/flutter_pubspec_snippet.yaml`

This repo also includes a minimal `pubspec.yaml` so the Flutter example files can be analyzed directly.

Use the example model and renderer as the integration reference:

- `flutter_example/avatar_pack_catalog.dart`
- `flutter_example/avatar_preview.dart`

Load the catalog, store equipped asset IDs, and render layers by `z_index` plus the normalized `placement` target boxes. Do not hardcode item definitions in widgets.

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

The pet catalog contains 90 unlockable companions. Pets use the same side-slot placement contract as floating props and are rendered from the catalog metadata, not from a separate pet system.

## Validation

Run:

```bash
python3 scripts/validate_avatar_catalog.py
python3 scripts/qa_avatar_visuals.py
python3 -m unittest tests/test_avatar_catalog.py
flutter analyze
```

These checks validate manifest paths, PNG alpha/dimensions, trimmed sprite bounds, placement target bounds, XP ranges, slot compatibility, pet side-slot rules, loadout behavior, and basic visual crop sanity.
