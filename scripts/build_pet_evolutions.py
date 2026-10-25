#!/usr/bin/env python3
"""Generate the Shiny (stage 2) and Radiant (stage 3) evolutions of every base pet.

Every base pet (id ending in ``_001``) gets two procedurally derived sprites:

* ``<line>_002`` **Shiny** – a deterministic hue rotation (40–140°, chosen from the
  line id hash) with a little more saturation and contrast, plus a few 4-point star
  sparkles in the transparent margin. The alpha of every base pixel is unchanged and
  the sprite keeps the exact base ``sprite_size``.
* ``<line>_003`` **Radiant** – the Shiny recolour plus a soft rarity-tinted outer glow,
  a thin bright rim light and more sparkles. The glow needs room, so the canvas grows
  by ``GLOW_PADDING`` (12%) per side and is then re-trimmed to its alpha bounds.

The script is idempotent: it removes previously generated stage 2/3 entries and files
first, uses fixed seeds, and writes the same PNG bytes for the same inputs. It also
stamps the ``evolution`` object on every pet (base included), bumps the catalog header
to ``schema_version 3.0.0`` / ``evolution_contract_version pet_evolution_v1`` and
rebuilds the flattened ``assets`` list.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pack_image_ops import (  # noqa: E402
    ROOT,
    add_outer_glow,
    add_rim_light,
    alpha_mask,
    draw_sparkles,
    load_catalog,
    recolour_hue,
    save_catalog,
    save_png,
    sparkle_positions,
    stable_hash,
    trim_to_alpha,
)


SCHEMA_VERSION = "3.2.0"
EVOLUTION_CONTRACT_VERSION = "pet_evolution_v1"
PETS_DIR = ROOT / "assets" / "avatar" / "pets"

HUE_MIN, HUE_MAX = 40, 140
SHINY_SATURATION = 1.08
SHINY_CONTRAST = 1.06
GLOW_PADDING = 0.12
GLOW_STRENGTH = 0.62
GLOW_SPREAD_FRACTION = 0.025
RIM_STRENGTH = 0.5
RIM_THICKNESS_FRACTION = 0.012
# Radiant sprites are trimmed where the glow tail drops to the QA visibility threshold
# (alpha > 12, i.e. under 5%), so the recorded sprite_size is the visible extent.
RADIANT_TRIM_ALPHA = 12
SHINY_SPARKLES = 4
RADIANT_SPARKLES = 8

GLOW_COLOURS = {
    "common": (255, 255, 255),
    "uncommon": (120, 235, 150),
    "rare": (95, 170, 255),
    "epic": (190, 115, 255),
    "legendary": (255, 205, 90),
}
RIM_COLOURS = {
    "common": (255, 255, 255),
    "uncommon": (205, 255, 215),
    "rare": (195, 225, 255),
    "epic": (230, 200, 255),
    "legendary": (255, 240, 190),
}

STAGES = {
    1: {"suffix": "_001", "stage_name": "Base", "requires_level": 1, "tag": None},
    2: {"suffix": "_002", "stage_name": "Shiny", "requires_level": 5, "tag": "stage_2"},
    3: {"suffix": "_003", "stage_name": "Radiant", "requires_level": 10, "tag": "stage_3"},
}


def line_id_of(base_id: str) -> str:
    assert base_id.endswith("_001"), base_id
    return base_id[: -len("_001")]


def hue_shift_for(line_id: str) -> int:
    return HUE_MIN + stable_hash(line_id) % (HUE_MAX - HUE_MIN + 1)


def shiny_recolour(base: Image.Image, line_id: str) -> Image.Image:
    return recolour_hue(base, hue_shift_for(line_id), SHINY_SATURATION, SHINY_CONTRAST)


def sparkle_radius(image: Image.Image) -> int:
    return max(5, round(min(image.size) * 0.035))


def build_shiny(base: Image.Image, line_id: str) -> Image.Image:
    image = shiny_recolour(base, line_id)
    rng = random.Random(stable_hash(f"{line_id}:shiny") & 0xFFFFFFFF)
    radius = sparkle_radius(image)
    positions = sparkle_positions(image, SHINY_SPARKLES, rng, radius, min_gap=4, max_gap=radius * 4)
    # Sparkles live in the margin only: every pixel the base pet covers keeps its exact alpha.
    return draw_sparkles(image, positions, rng, radius, protect=alpha_mask(base))


def build_radiant(base: Image.Image, line_id: str, rarity: str) -> Image.Image:
    image = shiny_recolour(base, line_id)
    rim_thickness = max(2, round(min(image.size) * RIM_THICKNESS_FRACTION))
    image = add_rim_light(image, RIM_COLOURS[rarity], rim_thickness, RIM_STRENGTH)
    pad_x = round(image.width * GLOW_PADDING)
    pad_y = round(image.height * GLOW_PADDING)
    spread = max(2, round(min(image.size) * GLOW_SPREAD_FRACTION))
    image = add_outer_glow(image, pad_x, pad_y, GLOW_COLOURS[rarity], GLOW_STRENGTH, spread)
    rng = random.Random(stable_hash(f"{line_id}:radiant") & 0xFFFFFFFF)
    radius = round(sparkle_radius(base) * 1.15)
    silhouette = Image.new("L", image.size, 0)
    silhouette.paste(alpha_mask(base), (pad_x, pad_y))
    # Sparkles hug the glow: between the silhouette edge and ~85% of the glow padding.
    positions = sparkle_positions(
        image, RADIANT_SPARKLES, rng, radius, min_gap=3, max_gap=max(4, round(0.85 * min(pad_x, pad_y)))
    )
    image = draw_sparkles(image, positions, rng, radius, protect=silhouette)
    return trim_to_alpha(image, RADIANT_TRIM_ALPHA)


def evolution_block(line_id: str, stage: int) -> dict:
    return {
        "line_id": line_id,
        "stage": stage,
        "stage_name": STAGES[stage]["stage_name"],
        "base_id": f"{line_id}_001",
        "next_id": f"{line_id}{STAGES[stage + 1]['suffix']}" if stage < 3 else None,
        "requires_level": STAGES[stage]["requires_level"],
    }


def evolved_entry(base_entry: dict, stage: int, image: Image.Image) -> dict:
    line_id = line_id_of(base_entry["id"])
    spec = STAGES[stage]
    entry = dict(base_entry)
    entry["id"] = f"{line_id}{spec['suffix']}"
    entry["name"] = f"{base_entry['name']} ({spec['stage_name']})"
    relative = f"assets/avatar/pets/{base_entry['rarity']}/{entry['id']}.png"
    entry["asset_path"] = relative
    entry["preview_asset_path"] = relative
    entry["sprite_size"] = {"width": image.width, "height": image.height}
    entry["xp_cost"] = 0
    entry["unlock_condition"] = f"evolve:{base_entry['id']}:level:{spec['requires_level']}"
    entry["default_unlocked"] = False
    entry["tags"] = [*base_entry["tags"], "evolved", spec["tag"]]
    entry["evolution"] = evolution_block(line_id, stage)
    return entry


def is_generated(pet: dict) -> bool:
    return not pet["id"].endswith("_001")


def hand_drawn_stages(base: dict) -> set[int]:
    """Stages whose PNG is supplied by an artist instead of generated (``hand_drawn_stages`` on the base)."""
    return {int(stage) for stage in base.get("hand_drawn_stages", [])}


def remove_stale(catalog: dict) -> int:
    by_id = {pet["id"]: pet for pet in catalog["pets"]}
    stale = [pet for pet in catalog["pets"] if is_generated(pet)]
    for pet in stale:
        base = by_id.get(pet.get("evolution", {}).get("base_id", ""), {})
        if pet.get("evolution", {}).get("stage") in hand_drawn_stages(base):
            continue
        path = ROOT / pet["asset_path"]
        if path.exists() and path.is_relative_to(PETS_DIR):
            path.unlink()
    catalog["pets"] = [pet for pet in catalog["pets"] if not is_generated(pet)]
    for pet in catalog["pets"]:
        pet.pop("evolution", None)
        pet["tags"] = [tag for tag in pet["tags"] if tag not in {"evolved", "stage_2", "stage_3"}]
    return len(stale)


def build(catalog: dict, only: set[str] | None = None) -> list[dict]:
    removed = remove_stale(catalog)
    if removed:
        print(f"Removed {removed} stale evolved pet entries")
    new_pets: list[dict] = []
    for base in catalog["pets"]:
        base_id = base["id"]
        line_id = line_id_of(base_id)
        base["evolution"] = evolution_block(line_id, 1)
        new_pets.append(base)
        if only and base_id not in only:
            continue
        with Image.open(ROOT / base["asset_path"]) as source:
            base_image = source.convert("RGBA")
        keep = hand_drawn_stages(base)
        sizes = []
        for stage in (2, 3):
            if stage in keep:
                path = ROOT / f"assets/avatar/pets/{base['rarity']}/{line_id}{STAGES[stage]['suffix']}.png"
                with Image.open(path) as supplied:
                    image = trim_to_alpha(supplied.convert("RGBA"))
                if image.size != supplied.size:
                    raise SystemExit(f"{path}: hand-drawn stage must be tightly trimmed to its alpha bounds")
            elif stage == 2:
                image = build_shiny(base_image, line_id)
            else:
                image = build_radiant(base_image, line_id, base["rarity"])
            entry = evolved_entry(base, stage, image)
            if stage not in keep:
                save_png(image, ROOT / entry["asset_path"])
            new_pets.append(entry)
            sizes.append(f"{STAGES[stage]['stage_name'].lower()} {image.size}{' (hand-drawn)' if stage in keep else ''}")
        print(f"{base_id}: hue +{hue_shift_for(line_id)}° " + " ".join(sizes))
    catalog["pets"] = new_pets
    catalog["schema_version"] = SCHEMA_VERSION
    catalog["evolution_contract_version"] = EVOLUTION_CONTRACT_VERSION
    return new_pets


def preview(catalog: dict, ids: list[str], out: Path) -> None:
    """Render base / shiny / radiant for a few pets to one contact sheet (no catalog writes)."""
    by_id = {pet["id"]: pet for pet in catalog["pets"]}
    cell = 230
    sheet = Image.new("RGBA", (3 * cell, len(ids) * cell), (46, 46, 56, 255))
    for row, pet_id in enumerate(ids):
        base = by_id[pet_id]
        line_id = line_id_of(pet_id)
        with Image.open(ROOT / base["asset_path"]) as source:
            base_image = source.convert("RGBA")
        variants = (base_image, build_shiny(base_image, line_id), build_radiant(base_image, line_id, base["rarity"]))
        for col, image in enumerate(variants):
            thumb = image.copy()
            thumb.thumbnail((cell - 10, cell - 10))
            sheet.alpha_composite(thumb, (col * cell + (cell - thumb.width) // 2, row * cell + (cell - thumb.height) // 2))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"Preview written to {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", type=Path, help="Write a base/shiny/radiant contact sheet here instead of building.")
    parser.add_argument("--ids", nargs="*", help="Limit --preview to these base pet ids.")
    args = parser.parse_args()
    catalog = load_catalog()
    if args.preview:
        ids = args.ids or [pet["id"] for pet in catalog["pets"][:6]]
        preview(catalog, ids, args.preview)
        return 0
    pets = build(catalog)
    save_catalog(catalog)
    print(f"Pets: {len(pets)} ({sum(1 for p in pets if p['evolution']['stage'] == 1)} lines x 3 stages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
