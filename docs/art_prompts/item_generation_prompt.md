# Item Generation Prompt

Create a transparent PNG avatar-worn accessory for a teen-focused SAT prep mobile app. Style is modern, clean, semi-flat cartoon with light cel shading. The item must align to one modular worn slot: headwear, eyewear, face_accessory, ear_accessory, neck_accessory, chest_badge, jacket_or_top_overlay, back_or_aura, or background_frame.

Use a 512x512 transparent canvas matching the base avatar coordinate system. Keep the silhouette readable at small sizes. Avoid tiny details, full outfit redraws, and any hand-dependent placement. The item should work as a clean overlay on multiple avatars in `style_version: teen_modular_v1`.

Slot placement notes:
- `background_frame`: full-canvas open-center frame, behind or around the avatar, with padding so art does not touch the image edge.
- `jacket_or_top_overlay`: torso-only garment layer, no head, face, hands, legs, logos, or full outfit redraw; keep the neck area open and the silhouette simple.
- `ear_accessory`: matched left/right pair positioned near the avatar ear area, with the center of the canvas empty; no mannequin, head, hair, or face.

Headwear that hovers (halos, orbiting rings, floating crowns) must be tagged `floating` in the catalog. The app bottom-aligns other headwear on the brow line (y = 0.245 of the frame); `floating` headwear keeps the centred target box.

## Prism variants

Rare, epic and legendary items in the headwear, ear, neck, floating-prop and background-frame categories also ship as procedural "Prism" variants (`item_3NN_<slug>_prism`, `variant_of: <base id>`), built by `scripts/build_item_variants.py`. A Prism variant is the base sprite with a deterministic hue rotation (60-300 degrees from the id hash), a horizontal hue gradient of +/-25 degrees across the sprite and a faint iridescent sheen on bright, low-saturation pixels; the alpha channel is byte-identical to the base. When a new rare+ item is added in one of those categories, re-run the script to regenerate its Prism variant. Do not hand-draw Prism variants; if a hand-made alternate colourway is wanted, add it as a separate base item instead.
