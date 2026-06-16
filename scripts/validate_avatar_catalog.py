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
    "anchor",
    "scale",
    "z_index",
    "tags",
    "style_version",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_catalog(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text())
    assets = data.get("assets", [])
    ids: set[str] = set()

    if data.get("style_version") != "teen_modular_v1":
        fail(errors, "catalog style_version must be teen_modular_v1")

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

        asset_path = ROOT / asset.get("asset_path", "")
        if not asset_path.exists():
            fail(errors, f"{asset_id}: asset path missing {asset_path}")
        else:
            try:
                with Image.open(asset_path) as image:
                    if image.mode not in {"RGBA", "LA"} and "transparency" not in image.info:
                        fail(errors, f"{asset_id}: PNG does not expose alpha channel")
                    expected = asset.get("canvas_size", {})
                    if image.size != (expected.get("width"), expected.get("height")):
                        fail(errors, f"{asset_id}: image size {image.size} != canvas_size {expected}")
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
