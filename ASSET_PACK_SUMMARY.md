# Asset Pack Summary

Style version: `teen_modular_v1`
Schema version: `3.2.0`
Placement contract: `target_box_v1` + `face_fit_v1` (per-avatar face rigs, per-item fits)
Evolution contract: `pet_evolution_v1`

## Catalog Counts

- Avatars: 110
- Starter avatars: 10
- Advanced avatars: 100
- Items: 376 (272 base + 104 Prism variants)
- Pets: 270 (90 lines x Base/Shiny/Radiant)
- Total catalog assets: 756

## Item Categories

- `headwear`: 80 (40 base + 40 Prism)
- `eyewear`: 30
- `face_accessory`: 25
- `ear_accessory`: 36 (24 base + 12 Prism)
- `neck_accessory`: 50 (25 base + 25 Prism)
- `chest_badge`: 30
- `jacket_overlay`: 24
- `back_aura`: 25
- `background_frame`: 36 (24 base + 12 Prism)
- `floating_props`: 40 (25 base + 15 Prism)

## Pet Evolution

- 90 pet lines, each with `_001` Base, `_002` Shiny (level 5) and `_003` Radiant (level 10) stages.
- Every pet has an `evolution` object (`line_id`, `stage`, `stage_name`, `base_id`, `next_id`, `requires_level`).
- Evolved stages are free (`xp_cost: 0`), locked by default and unlocked with `evolve:<base_id>:level:<n>` once the equipped pet reaches that level.

## Sprite Sheets

- `avatars_starter_sheet.png`, `avatars_advanced_sheet.png`, `items_sheet.png`, `pets_sheet.png` (unchanged base sheets)
- `items_prism_sheet.png` (104 frames), `pets_shiny_sheet.png` (90 frames), `pets_radiant_sheet.png` (90 frames)

## Runtime Files

- `assets/avatar/manifest/avatar_catalog.json`
- `assets/avatar/manifest/avatar_catalog.schema.json`
- `assets/avatar/manifest/sprite_atlas.json`
- `manifest/flutter_avatar_catalog.json`
- `manifest/flutter_pubspec_snippet.yaml`
- `pubspec.yaml`

## QA Status

The dataset is intended to pass:

```bash
python3 scripts/validate_avatar_catalog.py
python3 scripts/qa_avatar_visuals.py
python3 -m unittest tests/test_avatar_catalog.py
flutter analyze
```

Base avatar PNGs are 512x512 RGBA. Items and pets are trimmed RGBA sprites with `sprite_size` metadata and normalized placement target boxes in the catalog.

The pet catalog now includes 270 side-slot companions (90 lines x 3 evolution stages) across common, uncommon, rare, epic, and legendary rarity tiers.
