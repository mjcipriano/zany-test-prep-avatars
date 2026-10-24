# Pet Generation Prompt

Create a transparent PNG side-slot pet companion for a teen-focused SAT prep mobile app. The pet should be cool, collectible, and readable at small sizes. It should fit beside the avatar in one of four side slots, not overlap the avatar face, and require no hand contact. Use the same modern semi-flat cartoon / light cel-shaded style as the avatar pack. Transparent background. No full scene background. Keep silhouette clean.

Additional constraints:
- Canvas: 512x512 PNG with alpha.
- The pet should support left/right mirroring.
- Avoid toddler mascot proportions and excessive cuteness.
- Keep the design legible in a 96px preview.
- Output should match `style_version: teen_modular_v1`.

## Evolution stages

Every pet line ships three stages. Only the Base stage (`<line>_001`) is hand-made art; the other two are derived procedurally from it by `scripts/build_pet_evolutions.py` and regenerate byte-for-byte from the same base PNG:

- **Shiny (`_002`, level 5)**: the base sprite with its hue rotated by a fixed per-line amount (40-140 degrees, chosen from the line id hash so each line reads as its own colour morph), saturation x1.08, contrast x1.06, plus four small 4-point star sparkles in the transparent margin. The hue maths runs on alpha-premultiplied colour and never touches the alpha of any base pixel, so the sprite size, silhouette and outlines are identical to the base. Eye highlights stay white and outlines stay dark because the rotation preserves value.
- **Radiant (`_003`, level 10)**: the Shiny recolour plus a thin bright rim light inside the silhouette edge, a soft Gaussian outer glow tinted by rarity (common soft white, uncommon green, rare blue, epic violet, legendary gold) and eight sparkles. The glow pads the canvas by 12% per side and the sprite is re-trimmed where the glow fades below 5% alpha, so its `sprite_size` is larger than the base while the pet itself still fills at least 80% of its contain-fitted box.

Supplying a hand-drawn stage instead of the procedural one:
- Draw it on the same 512x512 canvas as the base, in the same pose, scale and position, so the base's side-slot targets still fit. Keep the silhouette within the base silhouette plus at most 12% padding per side for glow or effects.
- Trim it tightly to its alpha bounds and save it as `assets/avatar/pets/<rarity>/<line>_002.png` or `<line>_003.png` (same rarity folder as the base).
- Add `"hand_drawn_stages": [2]` (or `[2, 3]`) to the base pet's catalog entry. `scripts/build_pet_evolutions.py` then keeps those files, reads their `sprite_size` from the PNG and only regenerates the procedural stages; without the flag a re-run overwrites the file.
- Keep the catalog entry fields the same as the generated one (`evolution`, `xp_cost: 0`, `evolve:` unlock condition, `evolved` and `stage_N` tags); only `sprite_size` and the pixels change.
- Run `python3 scripts/validate_avatar_catalog.py` and `python3 scripts/qa_avatar_visuals.py`; the QA checks that a Shiny stage keeps the base alpha mask and that a Radiant stage's opaque core is at least the base silhouette.
