# Hats on independently drawn avatars: limits and the art fix

## What the code does (3.2.0)

The 110 avatars were drawn one by one: head height, head size and hair volume all differ,
and the hats were drawn as isolated objects. The pack now does what code can do:

- **Fit to the face and hair.** `face_rig` points (MediaPipe face landmarks) place the
  brim on the brow; the `hair` width (from the silhouette) makes the hat at least wide
  enough to cover the hair (`width_floor`).
- **Hat hair.** `clip_avatar_above` hides the avatar's pixels above the hat's crown, the
  hair that would be squashed under it, so buns and curls no longer poke through. This
  is the 2D equivalent of Terraria's `DrawHatHair` and Stardew Valley's "show real hair"
  hat setting.
- **Front/back.** Hoods, the headset and the laurel are drawn behind the head; headbands
  keep only their front band.
- **Built-in items.** Avatars whose art already wears a cap, beanie or glasses
  (`built_in_slots`) don't stack a second one.

## What code cannot fix

- **Perspective.** Most caps and bucket hats are drawn in a three-quarter view, while the
  faces look straight ahead. However well a 3/4 cap is placed, it reads as "pasted on".
- **Hair compression.** Hiding the hair above the hat is a cut, not a redraw: hair
  beside the hat keeps its full volume instead of being pressed flat under the brim.

## How other dress-up systems avoid this

Every system that layers items well authors them against a **shared base**: one body/head
template (Picrew, Habitica, Neopets per species, Terraria, Stardew Valley), a shared 2D
skeleton (Spine, Live2D, Rive) or a shared 3D rig (Bitmoji, Memoji, Roblox). Hats are
drawn on that template's head, and the template's hair has a "hat hair" variant or rule.
Nobody fits independently drawn hats onto independently drawn heads at scale.

## Recommended art pipeline (next)

1. **Regenerate hats front-facing on one reference head** (same canvas, scale, brim
   line). Prompt: "front view, straight on, symmetrical, eye level, [hat], worn on a
   plain mannequin head, flat lighting, transparent background, same art style as the
   avatars". Remove the head, keep the hat; mark the brim line and crown. Front-facing
   hats are what make placement look right; the existing fit/clip data keeps working.
2. **Split brimmed and open hats into back and front PNGs** (back drawn behind the hair,
   front over it) where the inside of the hat shows.
3. **Optional: one "hat hair" version per avatar** (hair flattened under a cap/beanie),
   made with an image-editing model and reviewed by hand: about 110 x 3 hat classes. The
   renderer would swap to it while a hat is equipped, like Stardew Valley's hat hairstyles.
4. Regenerating every avatar from one shared base is the full industry fix, but it
   throws away the existing art; only worth it if the avatars are being redrawn anyway.
