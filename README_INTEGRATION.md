# Zany Test Prep Avatar Dataset

This repository contains the production-ready avatar customization dataset for the Zany Test Prep Flutter app.

## Source Of Truth

Use this JSON catalog at runtime:

`assets/avatar/manifest/avatar_catalog.json`

The catalog contains:

- 10 starter avatars
- 100 advanced avatars
- 376 unlockable items (272 base items plus 104 "Prism" recolour variants)
- 270 pet companions (90 pet lines, each with Base, Shiny and Radiant evolution stages)
- 756 catalog assets in total
- four side slots for pets and floating props
- XP costs, rarity, unlock metadata, placement targets, sprite sizes, z-index values, and preview paths
- a `pet_evolution_v1` evolution contract (`evolution` object on every pet) and `variant_of` links on Prism items

Base avatar PNGs are 512x512 RGBA. Item and pet PNGs are tightly trimmed RGBA sprites. The catalog keeps `canvas_size: 512x512` as the virtual composition frame and exposes each trimmed PNG's real bounds in `sprite_size`.

## Placement Contract

Catalog `schema_version: 3.0.0` keeps `placement_contract_version: target_box_v1` (unchanged since 2.1) and adds `evolution_contract_version: pet_evolution_v1`.

Render each layer this way:

1. Sort equipped layers and the base avatar by `z_index`.
2. Render the base avatar full-frame in the 512x512 virtual canvas.
3. For item and pet layers, choose `asset.placement.targets_by_slot[equippedSlot]` when present; otherwise use `asset.placement.target`.
4. Center the trimmed sprite at `target.cx,target.cy` in normalized 0..1 canvas space.
5. Fit the sprite inside `target.w,target.h` using `BoxFit.contain`, preserving aspect ratio.

`scale` remains present for older builds. In v2.1 it is defined as an optional multiplier on `placement.target.w/h`; new integrations can usually leave it at `1.0`.

The app may bottom-align `headwear` on the brow line (y = 0.245 of the frame) instead of centring it in the target box. Headwear tagged `floating` (currently `item_007_halo_ring` and `item_027_orbit_headband`, plus their Prism variants) is exempt from that alignment and keeps the centred target box so it hovers above the head.

## Pet Evolution (`pet_evolution_v1`)

Every pet carries an `evolution` object:

```json
"evolution": {
  "line_id": "pet_fox_study_cap",
  "stage": 2,
  "stage_name": "Shiny",
  "base_id": "pet_fox_study_cap_001",
  "next_id": "pet_fox_study_cap_003",
  "requires_level": 5
}
```

- Each line has three stages: `<line>_001` Base (level 1), `<line>_002` Shiny (level 5) and `<line>_003` Radiant (level 10).
- Base pets are bought with XP as before. Evolved stages have `xp_cost: 0`, `default_unlocked: false` and `unlock_condition: "evolve:<base_id>:level:<n>"`.
- Pets gain XP while equipped; when the equipped pet's level reaches `requires_level` of its `next_id`, the app unlocks `next_id`. The player keeps every unlocked stage and can equip any of them.
- Evolved stages inherit `rarity`, `placement`, `z_index`, `allowed_slots`, `pet_species` and the rest of the base metadata, so the render rule is unchanged. Only `sprite_size` differs for Radiant stages, whose glow pads the sprite by up to 12% per side.

## Prism Item Variants

Items `item_301_*_prism` through `item_404_*_prism` are procedural recolours of every rare, epic and legendary item in the headwear, ear, neck, floating-prop and background-frame categories. Each has `variant_of: "<base item id>"`, the base's placement, sprite size and slots, rarity bumped one tier, 1.5x the base XP cost (clamped to the rarity band) and the tags `prism` and `variant`.

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

The pet catalog contains 270 companions: 90 lines, each with three evolution stages. Pets use the same side-slot placement contract as floating props and are rendered from the catalog metadata, not from a separate pet system.

## Validation

Run:

```bash
python3 scripts/validate_avatar_catalog.py
python3 scripts/qa_avatar_visuals.py
python3 -m unittest tests/test_avatar_catalog.py
flutter analyze
```

These checks validate manifest paths, PNG alpha/dimensions, trimmed sprite bounds, placement target bounds, XP ranges, unlock conditions (`default`, `spend_xp:<n>`, `evolve:<id>:level:<n>`), evolution chain integrity, `variant_of` resolution, slot compatibility, pet side-slot rules, loadout behavior, and basic visual crop sanity. `qa_avatar_visuals.py` also runs a geometric overlap pass that contain-fits every sprite into every slot it can occupy and checks the fitted rectangles against the canvas, the rig head/face regions, the other side slots and the neighbouring worn slots.

Rebuild the generated assets with:

```bash
python3 scripts/build_pet_evolutions.py     # Shiny/Radiant pet stages
python3 scripts/build_item_variants.py      # Prism item variants
python3 scripts/build_flutter_manifest.py   # manifest/flutter_avatar_catalog.json + pubspec snippet
python3 scripts/build_sprite_atlas.py --sheet items_prism --sheet pets_shiny --sheet pets_radiant
```

## Releasing the pack

Releases are cut by GitHub Actions (`.github/workflows/release.yml`): bump
`version:` in `pubspec.yaml`, merge to `master`, and the workflow validates the
catalog, runs the visual QA and tests, creates the `vX.Y.Z` tag on that commit
and publishes a GitHub Release. It can also be run manually from the Actions tab
with a `version` input. No local tag push is needed (sandboxed environments often
cannot push tags). The app then vendors it with
`python3 tools/sync_avatars.py --tag vX.Y.Z --full`.
