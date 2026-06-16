# Item Generation Prompt

Create a transparent PNG avatar-worn accessory for a teen-focused SAT prep mobile app. Style is modern, clean, semi-flat cartoon with light cel shading. The item must align to one modular worn slot: headwear, eyewear, face_accessory, ear_accessory, neck_accessory, chest_badge, jacket_or_top_overlay, back_or_aura, or background_frame.

Use a 512x512 transparent canvas matching the base avatar coordinate system. Keep the silhouette readable at small sizes. Avoid tiny details, full outfit redraws, and any hand-dependent placement. The item should work as a clean overlay on multiple avatars in `style_version: teen_modular_v1`.

Slot placement notes:
- `background_frame`: full-canvas open-center frame, behind or around the avatar, with padding so art does not touch the image edge.
- `jacket_or_top_overlay`: torso-only garment layer, no head, face, hands, legs, logos, or full outfit redraw; keep the neck area open and the silhouette simple.
- `ear_accessory`: matched left/right pair positioned near the avatar ear area, with the center of the canvas empty; no mannequin, head, hair, or face.
