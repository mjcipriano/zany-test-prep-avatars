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

Version `3.0.0` changes (additive only, all existing ids, paths, placement targets and sprites are unchanged):
- Bumps `schema_version` to `3.0.0`; `placement_contract_version` stays `target_box_v1`.
- Adds `evolution_contract_version: pet_evolution_v1` and an `evolution` object on every pet (`line_id`, `stage`, `stage_name`, `base_id`, `next_id`, `requires_level`). Existing pets are stage 1 (`Base`) of their line.
- Adds 180 evolved pets: `<line>_002` Shiny and `<line>_003` Radiant for all 90 lines (270 pets total). They have `xp_cost: 0`, `default_unlocked: false`, `unlock_condition: "evolve:<base_id>:level:5|10"` and the tags `evolved` plus `stage_2`/`stage_3`.
- Adds 104 Prism item variants `item_301_*_prism` to `item_404_*_prism` with `variant_of`, `default_unlocked: false` and the tags `prism`/`variant` (376 items total, 756 assets total).
- Adds the `floating` tag to headwear that should hover above the head (`item_007_halo_ring`, `item_027_orbit_headband` and their Prism variants) for apps that bottom-align headwear on the brow line.
- Adds three sprite sheets (`items_prism`, `pets_shiny`, `pets_radiant`) to `sprite_atlas.json`; the existing sheets are byte-identical to 2.2.0.
- Adds `evolutionContractVersion` to `manifest/flutter_avatar_catalog.json`.
- New unlock condition form `evolve:<base_id>:level:<n>`; apps that only understand `default` and `spend_xp:<n>` should treat unknown conditions as locked.
- Saved loadouts need no migration: every pre-3.0 id still resolves.

Version `3.1.0` changes (all ids and paths unchanged; no saved-loadout migration):
- Bumps `schema_version` to `3.1.0` and adds `face_fit_contract_version: face_fit_v1`: a measured `face_rig` on every avatar and a `fit` on every headwear, eyewear, face and ear item (Prism variants share their base's fit). `target_box_v1` placement is unchanged and stays the fallback.
- Removes stray thin lines detached from the art in 24 eyewear sprites (re-trimmed, so their `sprite_size` shrank) and 10 avatars (`avatar_advanced_066` to `075`; still 512x512).
- Re-lays all 36 ear-accessory sprites (24 base + 12 Prism) so each earring is in proportion to the pair's spacing; their `sprite_size` changed.
- Fixes 19 eyewear display names that did not match the art (e.g. `item_069_mythic_goggles` is now "Mythic Monocle").
- Adds `data/face_rigs.json`, `data/item_fit.json`, `scripts/measure_face_rigs.py`, `scripts/build_face_fit.py`, `scripts/render_fit_sheets.py`.

The ID migration map is embedded in `assets/avatar/manifest/avatar_catalog.json` under `migration_map`. It is intended for saved inventory/import migration; it is not a runtime asset dependency.
