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

Catalog `schema_version: 3.2.0` keeps `placement_contract_version: target_box_v1` (unchanged since 2.1), `evolution_contract_version: pet_evolution_v1`, and adds `face_fit_contract_version: face_fit_v1` (below), which supersedes target boxes for head, face and ear items.

Render each layer this way:

1. Sort equipped layers and the base avatar by `z_index`.
2. Render the base avatar full-frame in the 512x512 virtual canvas.
3. For item and pet layers, choose `asset.placement.targets_by_slot[equippedSlot]` when present; otherwise use `asset.placement.target`.
4. Center the trimmed sprite at `target.cx,target.cy` in normalized 0..1 canvas space.
5. Fit the sprite inside `target.w,target.h` using `BoxFit.contain`, preserving aspect ratio.

`scale` remains present for older builds. In v2.1 it is defined as an optional multiplier on `placement.target.w/h`; new integrations can usually leave it at `1.0`.

Head, face and ear items should be placed with `face_fit_v1` instead; the target boxes remain as a fallback for renderers that do not read it.

## Face Fit Contract (`face_fit_v1`)

`target_box_v1` gives every slot one box in the 512 frame, but the avatars' heads sit at
different heights and sizes (eye lines range over ~0.07 of the frame, face widths over
~1.4x), so one box put masks over some avatars' eyes and earrings on cheeks. Catalog
`schema_version: 3.1.0` added `face_fit_contract_version: face_fit_v1` (3.2.0 adds hair
widths, `width_floor`, `clip_avatar_above` and `built_in_slots`):

- Every avatar carries a `face_rig`: named `points` (`eye_l`, `eye_r`, `eyes`, `brow`,
  `forehead`, `nose_bridge`, `nose`, `under_nose`, `mouth`, `chin`, `cheek_l`, `cheek_r`,
  `cheeks`, `face_l`, `face_r`, `ear_l`, `ear_r`, `ears`, `crown`) and reference `widths`
  (`face`, `eyes`, `mouth`, `ears`, `head`, `hair`), all normalised to the 512 frame.
  `_l` is the viewer's left. The face points come from face landmarks; `crown`, `head`
  (silhouette width at the brow) and `hair` (the narrower of that and the width halfway
  up to the crown, so buns don't count) come from the avatar's silhouette.
- Every `headwear`, `eyewear`, `face_accessory` and `ear_accessory` item carries a `fit`:

  ```json
  "fit": {"kind": "mask", "anchor": "nose_bridge", "sprite_anchor": {"x": 0.5, "y": 0.04},
          "width_ref": "face", "width": 1.1, "behind": false}
  ```

Render a fitted item on an avatar with a rig like this (all in 0..1 frame units):

1. `w = face_rig.widths[fit.width_ref] * fit.width`, raised to at least
   `face_rig.widths[fit.width_floor.ref] * fit.width_floor.width` when the fit has a
   `width_floor` (hats use the `hair` width so they cover big hair);
   `h = w * sprite_size.height / sprite_size.width`.
2. `left = face_rig.points[fit.anchor].x - fit.sprite_anchor.x * w`; `top = ...y - fit.sprite_anchor.y * h`.
3. Items with `behind: true` (hoods, the headset, the laurel wreath) are drawn under the avatar; the rest by `z_index` above it.
4. "Hat hair": when an equipped item has `clip_avatar_above: f`, hide the avatar's pixels
   above `top + f * h` of that item (the lowest such line wins). That is the hair that
   would be under the hat; without it buns and curls poke through the crown.
5. Avatars with `built_in_slots` (e.g. `["headwear"]`) already wear that item in their
   art: hide equipped items in those slots instead of stacking a second hat or pair of
   glasses.
6. Fall back to `target_box_v1` when the avatar has no `face_rig` or the item has no `fit`.

Some hats reach a little above the frame on avatars whose heads sit high; renderers should
leave headroom (the app shrinks the scene, anchored at the bottom, until every layer fits).

Inputs live in `data/`: `face_rigs.json` (measured by `scripts/measure_face_rigs.py` with
MediaPipe's face landmarker; only needed again for new or redrawn avatars) and
`item_fit.json` (fit kinds, the kind of each base item, and display-name fixes).
`scripts/build_face_fit.py` writes them into the catalog. It also removes stray thin lines
detached from the art (24 glasses sprites and 10 avatars had one, which made glasses sit
high), and re-lays every earring pair so the earrings are in proportion and hang from their
attachment points. `scripts/render_fit_sheets.py` renders contact sheets of every fitted
item on a spread of avatars into `build/fit_sheets/` for review.

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
python3 -m unittest discover -s tests -p "test_*.py"
flutter analyze
```

These checks validate manifest paths, PNG alpha/dimensions, trimmed sprite bounds, placement target bounds, XP ranges, unlock conditions (`default`, `spend_xp:<n>`, `evolve:<id>:level:<n>`), evolution chain integrity, `variant_of` resolution, slot compatibility, pet side-slot rules, loadout behavior, and basic visual crop sanity, face rigs (every avatar, points ordered top to bottom) and item fits (every head/face/ear item, Prism variants matching their base). `qa_avatar_visuals.py` also runs a geometric overlap pass that contain-fits every sprite into every slot it can occupy and checks the fitted rectangles against the canvas, the rig head/face regions, the other side slots and the neighbouring worn slots. It also places every fitted item on every avatar and checks that masks, gaiters, nose strips and moustaches stay below the eye line, glasses centre on the eyes and nothing extends more than 0.15 of the frame past its edge.

Rebuild the generated assets with:

```bash
python3 scripts/build_pet_evolutions.py     # Shiny/Radiant pet stages
python3 scripts/build_item_variants.py      # Prism item variants
python3 scripts/build_face_fit.py           # face_rig/fit, stray-line + earring clean-up, name fixes
python3 scripts/build_flutter_manifest.py   # manifest/flutter_avatar_catalog.json + pubspec snippet
python3 scripts/build_sprite_atlas.py
```

## Releasing the pack

Releases are cut by GitHub Actions (`.github/workflows/release.yml`): bump
`version:` in `pubspec.yaml`, merge to `master`, and the workflow validates the
catalog, runs the visual QA and tests, creates the `vX.Y.Z` tag on that commit
and publishes a GitHub Release. It can also be run manually from the Actions tab
with a `version` input. No local tag push is needed (sandboxed environments often
cannot push tags). The app then vendors it with
`python3 tools/sync_avatars.py --tag vX.Y.Z --full`.
