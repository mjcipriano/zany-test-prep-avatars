# Avatar Pack Migration Notes

The previous stub pack has been superseded by the production-ready modular pack in `assets/avatar`. Runtime integration should use only `assets/avatar/manifest/avatar_catalog.json`.

Stable IDs:
- Starter avatars keep their existing `avatar_basic_*` IDs and are marked `avatar_type: starter`.
- Advanced avatars keep their existing `avatar_advanced_*` IDs and are marked `avatar_type: advanced`.
- Existing item IDs are preserved where possible.
- New item IDs `item_201_*` through `item_272_*` populate the previously scaffolded `background_frame`, `jacket_overlay`, and `ear_accessory` slots.

Category changes:
- `avatars/basic` -> `avatars/starter`
- `items/glasses` -> `items/eyewear`
- `items/badge` -> `items/chest_badge`
- `items/neckwear` -> `items/neck_accessory`
- `items/back_accessory` -> `items/back_aura`
- `items/hand_prop` -> `items/floating_props`
- New `items/background_frame`, `items/jacket_overlay`, and `items/ear_accessory` folders contain catalog-backed production assets rather than empty slot scaffolds.

Slot changes:
- Legacy `hand` is removed from the render model.
- Former handheld props are side-slot floating props.
- Side-slot assets support `side_left_1`, `side_left_2`, `side_right_1`, and `side_right_2`.
- Pets are not a separate app system; they are unlockable avatar catalog assets with `type: pet` and `slot_type: side`.

Manifest changes:
- New source of truth: `assets/avatar/manifest/avatar_catalog.json`
- New schema: `assets/avatar/manifest/avatar_catalog.schema.json`
- New atlas metadata: `assets/avatar/manifest/sprite_atlas.json`
- Compatibility pointer: `manifest/flutter_avatar_catalog.json`

Version `2.1.0` changes:
- Adds `placement_contract_version: target_box_v1`.
- Adds top-level `rig` and slot `target` boxes in normalized 0..1 canvas coordinates.
- Adds per-asset `placement` metadata with `target`, `fit: contain`, and `scale_basis: target_box`.
- Adds `targets_by_slot` for side-slot assets.
- Adds `sprite_size` and `trimmed_sprite`.
- Item and pet PNGs are now tightly trimmed sprites instead of 512x512 padded canvases.
- `canvas_size` remains 512x512 and now means the virtual composition frame, not necessarily the PNG dimensions for items and pets.

Version `2.2.0` changes:
- Expands the pet companion selection from 30 to 90 catalog-backed side-slot pets.
- Keeps the `2.1.0` schema and `target_box_v1` placement contract unchanged.
- Rebuilds `assets/avatar/spritesheets/pets_sheet.png` and the `pets` atlas frame metadata for all 90 pets.

The ID migration map is embedded in `assets/avatar/manifest/avatar_catalog.json` under `migration_map`. It is intended for saved inventory/import migration; it is not a runtime asset dependency.
