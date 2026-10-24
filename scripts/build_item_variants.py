#!/usr/bin/env python3
"""Generate "Prism" recolour variants of the best worn/side items.

Every item with rarity ``rare``, ``epic`` or ``legendary`` in the categories listed in
``PRISM_CATEGORIES`` (``jacket_overlay`` is deliberately skipped) gets a procedural
variant:

* a deterministic hue rotation chosen from the base id hash,
* a gentle horizontal hue gradient of ``±PRISM_GRADIENT_DEGREES`` around that
  rotation so the sprite reads as slightly iridescent,
* a faint colour sheen on mid/high-value pixels so even mostly neutral items pick up
  a visible prism tint,
* the alpha channel is byte-identical to the base sprite.

Catalog entries are copied from the base, renumbered ``item_3NN_<slug>_prism``
consecutively from 301 in catalog order, bumped one rarity tier, priced at 1.5x the
base cost (rounded to the nearest 50 and clamped into the validator's cost band for
the new rarity) and tagged ``prism`` / ``variant`` with ``variant_of`` pointing at the
base. The script is idempotent: existing prism entries and files are removed first.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pack_image_ops import (  # noqa: E402
    ROOT,
    load_catalog,
    recolour_hue,
    rgb_to_hsv,
    hsv_to_rgb,
    save_catalog,
    save_png,
    stable_hash,
)
from validate_avatar_catalog import RARITY_COSTS  # noqa: E402


ITEMS_DIR = ROOT / "assets" / "avatar" / "items"
PRISM_CATEGORIES = (
    "headwear",
    "eyewear",
    "face_accessory",
    "ear_accessory",
    "neck_accessory",
    "chest_badge",
    "floating_props",
    "back_aura",
    "background_frame",
)
SOURCE_RARITIES = ("rare", "epic", "legendary")
RARITY_BUMP = {"rare": "epic", "epic": "legendary", "legendary": "legendary"}
FIRST_VARIANT_NUMBER = 301
COST_MULTIPLIER = 1.5
COST_STEP = 50

HUE_MIN, HUE_MAX = 60, 300
PRISM_GRADIENT_DEGREES = 25.0
PRISM_SATURATION = 1.1
SHEEN_STRENGTH = 0.14


def hue_shift_for(base_id: str) -> int:
    return HUE_MIN + stable_hash(f"prism:{base_id}") % (HUE_MAX - HUE_MIN + 1)


def prism_cost(base_cost: int, new_rarity: str) -> int:
    cost = int(round(base_cost * COST_MULTIPLIER / COST_STEP) * COST_STEP)
    lo, hi = RARITY_COSTS[new_rarity]
    return max(lo, min(hi, cost))


def slug_of(base_id: str) -> str:
    prefix, number, slug = base_id.split("_", 2)
    assert prefix == "item" and number.isdigit(), base_id
    return slug


def build_prism(base: Image.Image, base_id: str) -> Image.Image:
    """Hue-rotate with a left-to-right gradient, then add a faint iridescent sheen."""
    shift = hue_shift_for(base_id)
    columns = np.linspace(-1.0, 1.0, base.width, dtype=np.float32)
    per_column = shift + PRISM_GRADIENT_DEGREES * columns
    rotated = recolour_hue(base, per_column, PRISM_SATURATION, 1.0)

    rgba = np.asarray(rotated, dtype=np.float32) / 255.0
    alpha = rgba[..., 3]
    visible = alpha > 0
    hsv = rgb_to_hsv(rgba[..., :3])
    # Sheen hue sweeps across the sprite; strongest on bright, low-saturation pixels so
    # dark outlines stay dark and already-saturated colours are not pushed further.
    sheen_hue = ((shift + 90.0 + 120.0 * columns) / 360.0)[None, :] % 1.0
    sheen_hue = np.broadcast_to(sheen_hue, hsv.shape[:2])
    sheen_rgb = hsv_to_rgb(np.stack([sheen_hue, np.full_like(sheen_hue, 0.55), np.ones_like(sheen_hue)], axis=-1))
    brightness = np.clip((hsv[..., 2] - 0.3) / 0.7, 0.0, 1.0)
    neutrality = 1.0 - 0.6 * hsv[..., 1]
    weight = (SHEEN_STRENGTH * brightness * neutrality * visible)[..., None]
    out = rgba.copy()
    out[..., :3] = rgba[..., :3] * (1.0 - weight) + sheen_rgb * weight
    out[..., 3] = np.asarray(base.getchannel("A"), dtype=np.float32) / 255.0
    return Image.fromarray(np.round(np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8), "RGBA")


def is_prism(item: dict) -> bool:
    return "variant_of" in item or "prism" in item.get("tags", [])


def remove_stale(catalog: dict) -> int:
    stale = [item for item in catalog["items"] if is_prism(item)]
    for item in stale:
        path = ROOT / item["asset_path"]
        if path.exists() and path.is_relative_to(ITEMS_DIR):
            path.unlink()
    catalog["items"] = [item for item in catalog["items"] if not is_prism(item)]
    return len(stale)


def prism_entry(base: dict, number: int, image: Image.Image) -> dict:
    entry = dict(base)
    entry["id"] = f"item_{number:03d}_{slug_of(base['id'])}_prism"
    entry["name"] = f"{base['name']} (Prism)"
    entry["variant_of"] = base["id"]
    entry["rarity"] = RARITY_BUMP[base["rarity"]]
    entry["xp_cost"] = prism_cost(base["xp_cost"], entry["rarity"])
    entry["unlock_condition"] = f"spend_xp:{entry['xp_cost']}"
    entry["default_unlocked"] = False
    relative = f"{Path(base['asset_path']).parent.as_posix()}/{entry['id']}.png"
    entry["asset_path"] = relative
    entry["preview_asset_path"] = relative
    entry["sprite_size"] = {"width": image.width, "height": image.height}
    entry["tags"] = [*base["tags"], "prism", "variant"]
    return entry


def build(catalog: dict) -> list[dict]:
    removed = remove_stale(catalog)
    if removed:
        print(f"Removed {removed} stale prism entries")
    sources = [
        item
        for item in catalog["items"]
        if item["category"] in PRISM_CATEGORIES and item["rarity"] in SOURCE_RARITIES
    ]
    variants: list[dict] = []
    for offset, base in enumerate(sources):
        with Image.open(ROOT / base["asset_path"]) as source:
            base_image = source.convert("RGBA")
        image = build_prism(base_image, base["id"])
        assert image.size == base_image.size
        entry = prism_entry(base, FIRST_VARIANT_NUMBER + offset, image)
        save_png(image, ROOT / entry["asset_path"])
        variants.append(entry)
        print(f"{entry['id']}: hue +{hue_shift_for(base['id'])}° {base['rarity']}->{entry['rarity']} {base['xp_cost']}->{entry['xp_cost']} xp")
    catalog["items"].extend(variants)
    return variants


def main() -> int:
    catalog = load_catalog()
    variants = build(catalog)
    save_catalog(catalog)
    print(f"Prism variants: {len(variants)} (items now {len(catalog['items'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
