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

The catalog contains 110 base avatars, 272 worn/side-prop items, 30 pets, XP costs, rarity, unlock conditions, preview asset paths, canvas size, anchors, scale, z_index, tags, and style_version.

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
8. Use side-slot anchors/placement so pets and props appear around the avatar without covering the face.
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
- preventing two assets in the same slot
- preview stack generation without crashing

Keep the UI teen-focused and app-native. Avoid treating this as a landing page or marketing experience. The customization screen should be a practical app tool with an avatar preview, slot controls, inventory grid, rarity/XP labels, and locked/unlocked states.
```
