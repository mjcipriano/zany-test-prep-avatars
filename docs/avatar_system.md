# Modular Avatar System

The production catalog lives at `assets/avatar/manifest/avatar_catalog.json`. It is the JSON source of truth for Flutter. The legacy `manifest/flutter_avatar_catalog.json` now points to the new catalog and includes flattened avatar, item, and pet lists for compatibility.

Directory layout:
- `assets/avatar/avatars/starter`
- `assets/avatar/avatars/advanced`
- `assets/avatar/items/headwear`
- `assets/avatar/items/eyewear`
- `assets/avatar/items/face_accessory`
- `assets/avatar/items/ear_accessory`
- `assets/avatar/items/neck_accessory`
- `assets/avatar/items/chest_badge`
- `assets/avatar/items/jacket_overlay`
- `assets/avatar/items/back_aura`
- `assets/avatar/items/background_frame`
- `assets/avatar/items/floating_props`
- `assets/avatar/pets/common`
- `assets/avatar/pets/uncommon`
- `assets/avatar/pets/rare`
- `assets/avatar/pets/epic`
- `assets/avatar/pets/legendary`
- `assets/avatar/spritesheets`
- `assets/avatar/manifest`

Catalog counts:
- 110 avatars: 10 starter and 100 advanced
- 272 unlockable items across 10 worn/side-prop categories
- 30 pet companions
- 412 total catalog assets

Supported slots:
- Worn: `headwear`, `eyewear`, `face_accessory`, `ear_accessory`, `neck_accessory`, `chest_badge`, `jacket_or_top_overlay`, `back_or_aura`, `background_frame`
- Side: `side_left_1`, `side_left_2`, `side_right_1`, `side_right_2`

Side-slot assets are pets or floating props. They are independent layers around the avatar and must not require finger alignment. Legacy `hand_prop` assets are migrated to `floating_props` with side-slot metadata.

Placement contract:
- `schema_version: 2.1.0`
- `placement_contract_version: target_box_v1`
- `canvas_size` remains the virtual 512x512 composition frame.
- Avatar PNGs stay 512x512.
- Item and pet PNGs are tightly trimmed sprites; their real PNG dimensions are recorded in `sprite_size`.
- Each asset has `placement.anchor`, `placement.target`, `placement.fit: contain`, and `placement.scale_basis: target_box`.
- Side assets also have `placement.targets_by_slot`, keyed by `side_left_1`, `side_left_2`, `side_right_1`, and `side_right_2`.

Render rule:
1. Sort by `z_index`.
2. Render the base avatar full-frame.
3. For each equipped non-avatar layer, use `placement.targets_by_slot[equippedSlot]` when present, otherwise `placement.target`.
4. Center the trimmed sprite at `(target.cx, target.cy)` in normalized 0..1 canvas space.
5. Fit the sprite inside `(target.w, target.h)` of the 512 frame using contain, preserving aspect ratio.

`scale` is kept for compatibility and is now defined as an optional multiplier on the target box. New renderers should use `target.w/h` as the primary size contract.

Add a new asset by creating a transparent PNG, tightly trimming it to its alpha bounds, placing it in the matching folder, and adding a manifest entry with all required fields. Keep `style_version` set to `teen_modular_v1`, set `allowed_slots`, provide `placement`, `sprite_size`, `scale`, and `z_index`.

Current item category counts:
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

Validation:

```bash
python3 scripts/validate_avatar_catalog.py
python3 -m unittest tests/test_avatar_catalog.py
```

Flutter integration:
- Load `AvatarCatalog.load()` from `flutter_example/avatar_pack_catalog.dart`.
- Store equipped assets in `EquippedAvatarLoadout.equipped`.
- Render with `AvatarPreview(catalog: catalog, loadout: loadout)`.
- Do not hardcode unlockables in widgets; resolve assets by ID from the catalog.

Migration notes:
- Starter avatar IDs are preserved as `avatar_basic_*`, with `avatar_type: starter`.
- Advanced avatar IDs are preserved as `avatar_advanced_*`.
- Legacy `glasses` category is now `eyewear`.
- Legacy `badge` category is now `chest_badge`.
- Legacy `neckwear` category is now `neck_accessory`.
- Legacy `back_accessory` category is now `back_aura`.
- Legacy `hand_prop` category is now `floating_props` and uses side slots.
- A full path-level migration map is embedded in `avatar_catalog.json` under `migration_map`.
