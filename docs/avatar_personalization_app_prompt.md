# Application Implementation Prompt

Use this prompt when adding the Zany Test Prep avatar and personalization system to the Flutter app.

```text
You are implementing the avatar customization system for the Zany Test Prep Flutter app.

Use the dataset source of truth at:
assets/avatar/manifest/avatar_catalog.json

Do not hardcode avatars, items, pets, unlock costs, rarity, asset paths, or render order in widgets. Load the JSON catalog at runtime and build the UI from catalog data.

Implement these model concepts:
- AvatarCatalog
- AvatarAsset
- AvatarItem
- AvatarPet
- AvatarSlot
- EquippedAvatarLoadout

The catalog contains 110 base avatars, 376 worn/side-prop items (272 base items + 104 Prism variants), 270 pets (90 lines x 3 evolution stages), XP costs, rarity, unlock conditions, preview asset paths, canvas size, trimmed sprite size, placement targets, scale, z_index, tags, and style_version. Catalog `schema_version` is 3.0.0.

Use the placement contract (target_box_v1, unchanged from v2.1):
- `canvas_size` is the virtual 512x512 composition frame.
- Avatar PNGs are 512x512.
- Item and pet PNGs are tightly trimmed sprites, with dimensions in `sprite_size`.
- For each equipped layer, use `placement.targets_by_slot[equippedSlot]` when present, otherwise `placement.target`.
- Center the sprite at `target.cx,target.cy` in normalized 0..1 canvas space.
- Fit inside `target.w,target.h` using contain, preserving aspect ratio.
- Keep `z_index` as the stacking order.
- Treat `scale` as an optional multiplier on target box size, not as full-canvas scale.
- Bottom-align `headwear` on the brow line (y = 0.245 of the frame) instead of centring it in the target box, except headwear tagged `floating` (art that genuinely hovers, e.g. a halo), which keeps the centred target box. Decide by the tag only, never by the item id or name.

Implement the pet evolution contract (`evolution_contract_version: pet_evolution_v1`):
- Every pet has an `evolution` object: `line_id`, `stage` (1-3), `stage_name` (Base/Shiny/Radiant), `base_id`, `next_id` (null on stage 3) and `requires_level` (1/5/10).
- Base pets (`_001`) are bought with XP via `spend_xp:<cost>` as before.
- Evolved pets (`_002`, `_003`) have `xp_cost: 0`, `default_unlocked: false` and `unlock_condition: "evolve:<base_id>:level:<n>"`. They are never sold.
- Pets gain XP while equipped in a side slot (award pet XP alongside player XP for completed study sessions). Track a level per pet line.
- When an equipped pet's line reaches the `requires_level` of the current stage's `next_id`, unlock `next_id` and offer to equip it. Previously unlocked stages stay available.
- Evolved stages inherit rarity, placement, z_index, allowed slots and species from the base, so the render rule is unchanged; only `sprite_size` differs for Radiant stages.
- Show the three stages together in the pet inventory as one line with a progress bar to the next stage.

Implement item variants:
- Items with `variant_of` are Prism recolours of a base item. Group them with their base in the inventory, show the `prism` tag as a badge, and unlock them with `spend_xp` like any other item. They do not require owning the base item.

Supported worn slots:
- headwear
- eyewear
- face_accessory
- ear_accessory
- neck_accessory
- chest_badge
- jacket_or_top_overlay
- back_or_aura
- background_frame

All worn slots above are populated in the catalog. `ear_accessory`, `jacket_or_top_overlay`, and `background_frame` should be presented as first-class customization categories, not hidden placeholder categories.

Supported side slots:
- side_left_1
- side_left_2
- side_right_1
- side_right_2

Side slots can equip pets or floating props. They are independent layers beside the avatar and must not be treated as handheld items.

Build these user-facing flows:
1. Load the catalog from JSON.
2. Show starter avatars as unlocked by default.
3. Show advanced avatars, items, pets, and side props as locked or unlocked based on XP and unlock_condition.
4. Let the user equip exactly one asset per slot.
5. Prevent incompatible slot assignments using allowed_slots and compatible_slots.
6. Let the user unequip optional slots.
7. Render the preview by stacking assets sorted by z_index.
8. Use placement target boxes so worn items land on the correct body region and side pets/props appear around the avatar without covering the face.
9. Persist equipped loadouts by asset ID, not by file path.
10. Gracefully handle missing assets by showing a fallback placeholder and logging the missing ID/path.

Render order:
1. background_frame
2. back_or_aura
3. side slot lower/back effects if z_index requires it
4. avatar base
5. jacket_or_top_overlay
6. neck_accessory
7. face_accessory
8. eyewear
9. ear_accessory
10. headwear
11. chest_badge
12. side slot pets/items
13. foreground effects if any

Use the existing example files as a reference:
- flutter_example/avatar_pack_catalog.dart
- flutter_example/avatar_preview.dart

Add tests for:
- parsing the catalog
- unlocked asset calculation from XP
- equipping and unequipping slots
- rejecting incompatible slot assignments
- allowing pets and floating props in side slots
- pet evolution: `next_id` unlocks when the equipped pet reaches `requires_level`, evolved pets are never purchasable
- `variant_of` resolves to a base item and Prism items are equippable in the base item's slot
- preventing two assets in the same slot
- preview stack generation without crashing

Keep the UI teen-focused and app-native. Avoid treating this as a landing page or marketing experience. The customization screen should be a practical app tool with an avatar preview, slot controls, inventory grid, rarity/XP labels, and locked/unlocked states.
```
