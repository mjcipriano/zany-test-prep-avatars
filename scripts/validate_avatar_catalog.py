#!/usr/bin/env python3
"""Validate the Zany Test Prep modular avatar catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
VALID_RARITIES = {"starter", "common", "uncommon", "rare", "epic", "legendary"}
VALID_SLOTS = {
    "avatar",
    "headwear",
    "eyewear",
    "face_accessory",
    "ear_accessory",
    "neck_accessory",
    "chest_badge",
    "jacket_or_top_overlay",
    "back_or_aura",
    "background_frame",
    "side_left_1",
    "side_left_2",
    "side_right_1",
    "side_right_2",
}
SIDE_SLOTS = {"side_left_1", "side_left_2", "side_right_1", "side_right_2"}
RARITY_COSTS = {
    "starter": (0, 0),
    "common": (300, 1000),
    "uncommon": (1000, 2500),
    "rare": (2500, 5000),
    "epic": (5000, 10000),
    "legendary": (10000, 25000),
}
REQUIRED_FIELDS = {
    "id",
    "name",
    "type",
    "category",
    "slot_type",
    "allowed_slots",
    "rarity",
    "xp_cost",
    "unlock_condition",
    "asset_path",
    "preview_asset_path",
    "canvas_size",
    "sprite_size",
    "trimmed_sprite",
    "placement",
    "anchor",
    "scale",
    "z_index",
    "tags",
    "style_version",
}
SANE_SLOT_BOUNDS = {
    "headwear": (0.20, 0.10, 0.55, 0.32),
    "eyewear": (0.18, 0.05, 0.46, 0.18),
    "face_accessory": (0.18, 0.08, 0.46, 0.28),
    "ear_accessory": (0.28, 0.06, 0.58, 0.24),
    "neck_accessory": (0.18, 0.08, 0.48, 0.26),
    "chest_badge": (0.06, 0.06, 0.26, 0.26),
    "jacket_or_top_overlay": (0.30, 0.20, 0.76, 0.55),
    "back_or_aura": (0.45, 0.35, 0.98, 0.90),
    "background_frame": (0.70, 0.70, 1.00, 1.00),
    "side_left_1": (0.12, 0.12, 0.38, 0.38),
    "side_left_2": (0.12, 0.12, 0.42, 0.42),
    "side_right_1": (0.12, 0.12, 0.38, 0.38),
    "side_right_2": (0.12, 0.12, 0.42, 0.42),
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = image.convert("RGBA").getchannel("A")
    return alpha.point(lambda value: 255 if value > 0 else 0).getbbox()


def validate_target(errors: list[str], owner: str, slot: str, target: dict) -> None:
    required = {"cx", "cy", "w", "h"}
    missing = required - set(target)
    if missing:
        fail(errors, f"{owner}: placement target for {slot} missing {sorted(missing)}")
        return
    cx, cy, width, height = (target["cx"], target["cy"], target["w"], target["h"])
    if not all(isinstance(value, (int, float)) for value in (cx, cy, width, height)):
        fail(errors, f"{owner}: placement target for {slot} must be numeric")
        return
    if width <= 0 or height <= 0:
        fail(errors, f"{owner}: placement target for {slot} must have positive w/h")
    if cx - width / 2 < 0 or cx + width / 2 > 1 or cy - height / 2 < 0 or cy + height / 2 > 1:
        fail(errors, f"{owner}: placement target for {slot} exceeds normalized canvas bounds")
    if slot in SANE_SLOT_BOUNDS:
        min_w, min_h, max_w, max_h = SANE_SLOT_BOUNDS[slot]
        if not (min_w <= width <= max_w and min_h <= height <= max_h):
            fail(errors, f"{owner}: placement target for {slot} size {width:.3f}x{height:.3f} outside sane bounds")


def validate_catalog(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text())
    assets = data.get("assets", [])
    ids: set[str] = set()

    if data.get("style_version") != "teen_modular_v1":
        fail(errors, "catalog style_version must be teen_modular_v1")
    if data.get("schema_version") != "2.1.0":
        fail(errors, "catalog schema_version must be 2.1.0")
    if data.get("placement_contract_version") != "target_box_v1":
        fail(errors, "catalog placement_contract_version must be target_box_v1")
    if data.get("canvas") != {"width": 512, "height": 512}:
        fail(errors, "catalog canvas must be 512x512")

    for slot, spec in data.get("slots", {}).items():
        if slot not in VALID_SLOTS - {"avatar"}:
            fail(errors, f"slots: invalid slot {slot}")
            continue
        validate_target(errors, f"slots.{slot}", slot, spec.get("target", {}))

    for asset in assets:
        asset_id = asset.get("id", "<missing id>")
        missing = REQUIRED_FIELDS - set(asset)
        if missing:
            fail(errors, f"{asset_id}: missing required fields {sorted(missing)}")

        if asset_id in ids:
            fail(errors, f"{asset_id}: duplicate id")
        ids.add(asset_id)

        rarity = asset.get("rarity")
        if rarity not in VALID_RARITIES:
            fail(errors, f"{asset_id}: invalid rarity {rarity}")
        else:
            lo, hi = RARITY_COSTS[rarity]
            cost = asset.get("xp_cost")
            if not isinstance(cost, int) or not lo <= cost <= hi:
                fail(errors, f"{asset_id}: xp_cost {cost} outside {rarity} range {lo}-{hi}")

        allowed_slots = set(asset.get("allowed_slots", []))
        invalid_slots = allowed_slots - VALID_SLOTS
        if invalid_slots:
            fail(errors, f"{asset_id}: invalid allowed_slots {sorted(invalid_slots)}")

        canvas_size = asset.get("canvas_size", {})
        if canvas_size != {"width": 512, "height": 512}:
            fail(errors, f"{asset_id}: canvas_size must remain virtual 512x512")

        placement = asset.get("placement", {})
        if placement.get("fit") != "contain":
            fail(errors, f"{asset_id}: placement.fit must be contain")
        if placement.get("scale_basis") != "target_box":
            fail(errors, f"{asset_id}: placement.scale_basis must be target_box")
        if not isinstance(asset.get("scale"), (int, float)) or asset.get("scale") <= 0:
            fail(errors, f"{asset_id}: scale must be a positive target-box multiplier")
        primary_slot = next(iter(asset.get("allowed_slots", ["avatar"])), "avatar")
        validate_target(errors, asset_id, primary_slot, placement.get("target", {}))
        targets_by_slot = placement.get("targets_by_slot", {})
        if targets_by_slot:
            if set(targets_by_slot) != allowed_slots:
                fail(errors, f"{asset_id}: targets_by_slot keys must match allowed_slots")
            for slot, target in targets_by_slot.items():
                validate_target(errors, asset_id, slot, target)

        asset_path = ROOT / asset.get("asset_path", "")
        if not asset_path.exists():
            fail(errors, f"{asset_id}: asset path missing {asset_path}")
        else:
            try:
                with Image.open(asset_path) as image:
                    image = image.convert("RGBA")
                    if image.mode not in {"RGBA", "LA"} and "transparency" not in image.info:
                        fail(errors, f"{asset_id}: PNG does not expose alpha channel")
                    sprite_size = asset.get("sprite_size", {})
                    if image.size != (sprite_size.get("width"), sprite_size.get("height")):
                        fail(errors, f"{asset_id}: image size {image.size} != sprite_size {sprite_size}")
                    bbox = alpha_bbox(image)
                    if bbox is None:
                        fail(errors, f"{asset_id}: empty alpha")
                    elif asset.get("type") == "avatar":
                        if image.size != (512, 512):
                            fail(errors, f"{asset_id}: avatar image must stay 512x512")
                        if asset.get("trimmed_sprite") is not False:
                            fail(errors, f"{asset_id}: avatar trimmed_sprite must be false")
                    else:
                        if asset.get("trimmed_sprite") is not True:
                            fail(errors, f"{asset_id}: non-avatar asset must be a trimmed sprite")
                        if bbox != (0, 0, image.width, image.height):
                            fail(errors, f"{asset_id}: sprite is not tightly trimmed to alpha bounds")
            except Exception as exc:
                fail(errors, f"{asset_id}: failed to inspect PNG: {exc}")

        preview_path = ROOT / asset.get("preview_asset_path", "")
        if not preview_path.exists():
            fail(errors, f"{asset_id}: preview path missing {preview_path}")

        if asset.get("type") == "avatar":
            avatar_type = asset.get("avatar_type")
            default_unlocked = asset.get("default_unlocked")
            if avatar_type == "starter" and default_unlocked is not True:
                fail(errors, f"{asset_id}: starter avatar must be unlocked by default")
            if avatar_type == "advanced" and default_unlocked is not False:
                fail(errors, f"{asset_id}: advanced avatar must be locked by default")

        if asset.get("type") == "pet":
            if not allowed_slots or not allowed_slots <= SIDE_SLOTS:
                fail(errors, f"{asset_id}: pet allowed_slots must be side slots")
            if asset.get("mirrored_supported") is not True:
                fail(errors, f"{asset_id}: pet must support mirroring or provide variants")

        if asset.get("slot_type") == "side":
            if not allowed_slots <= SIDE_SLOTS:
                fail(errors, f"{asset_id}: side asset allowed_slots must be side slots")
            if asset.get("mirrored_supported") is not True:
                fail(errors, f"{asset_id}: side asset must be mirrored or have left/right variants")

    for loadout in data.get("demo_loadouts", []):
        avatar_id = loadout.get("avatar_id")
        if avatar_id not in ids:
            fail(errors, f"{loadout.get('id')}: unknown avatar_id {avatar_id}")
        seen_slots = set()
        for slot, asset_id in loadout.get("equipped", {}).items():
            if slot in seen_slots:
                fail(errors, f"{loadout.get('id')}: duplicate slot {slot}")
            seen_slots.add(slot)
            if slot not in VALID_SLOTS:
                fail(errors, f"{loadout.get('id')}: invalid equipped slot {slot}")
            if asset_id not in ids:
                fail(errors, f"{loadout.get('id')}: unknown equipped asset {asset_id}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "catalog",
        nargs="?",
        default="assets/avatar/manifest/avatar_catalog.json",
        help="Catalog JSON path to validate.",
    )
    args = parser.parse_args()
    errors = validate_catalog(ROOT / args.catalog)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Avatar catalog validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
