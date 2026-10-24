#!/usr/bin/env python3
"""Validate the Zany Test Prep modular avatar catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "3.0.0"
PLACEMENT_CONTRACT_VERSION = "target_box_v1"
EVOLUTION_CONTRACT_VERSION = "pet_evolution_v1"
EVOLUTION_STAGES = {1: ("Base", 1), 2: ("Shiny", 5), 3: ("Radiant", 10)}
EVOLUTION_FIELDS = {"line_id", "stage", "stage_name", "base_id", "next_id", "requires_level"}
RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]
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


def validate_unlock_condition(errors: list[str], asset: dict, by_id: dict[str, dict]) -> None:
    """Accept ``default``, ``spend_xp:<cost>`` and ``evolve:<base_id>:level:<n>``."""
    asset_id = asset.get("id", "<missing id>")
    condition = asset.get("unlock_condition")
    if not isinstance(condition, str):
        fail(errors, f"{asset_id}: unlock_condition must be a string")
        return
    parts = condition.split(":")
    if parts == ["default"]:
        if asset.get("xp_cost") != 0:
            fail(errors, f"{asset_id}: default unlock must have xp_cost 0")
        return
    if len(parts) == 2 and parts[0] == "spend_xp":
        if not parts[1].isdigit() or int(parts[1]) != asset.get("xp_cost"):
            fail(errors, f"{asset_id}: spend_xp unlock {condition} does not match xp_cost {asset.get('xp_cost')}")
        return
    if len(parts) == 4 and parts[0] == "evolve" and parts[2] == "level":
        base_id, level = parts[1], parts[3]
        evolution = asset.get("evolution") or {}
        if asset.get("type") != "pet" or evolution.get("stage", 1) == 1:
            fail(errors, f"{asset_id}: evolve unlock is only valid on evolved pets")
        if base_id not in by_id:
            fail(errors, f"{asset_id}: evolve unlock references unknown base {base_id}")
        elif base_id != evolution.get("base_id"):
            fail(errors, f"{asset_id}: evolve unlock base {base_id} != evolution.base_id {evolution.get('base_id')}")
        if not level.isdigit() or int(level) != evolution.get("requires_level"):
            fail(errors, f"{asset_id}: evolve unlock level {level} != evolution.requires_level")
        if asset.get("default_unlocked") is not False:
            fail(errors, f"{asset_id}: evolved pet must be locked by default")
        return
    fail(errors, f"{asset_id}: unsupported unlock_condition {condition}")


def validate_evolution(errors: list[str], asset: dict, by_id: dict[str, dict]) -> None:
    """Every pet carries an ``evolution`` block describing its place in a 3-stage line."""
    asset_id = asset.get("id", "<missing id>")
    evolution = asset.get("evolution")
    if not isinstance(evolution, dict):
        fail(errors, f"{asset_id}: pet is missing the evolution object")
        return
    missing = EVOLUTION_FIELDS - set(evolution)
    if missing:
        fail(errors, f"{asset_id}: evolution missing {sorted(missing)}")
        return
    stage = evolution["stage"]
    if stage not in EVOLUTION_STAGES:
        fail(errors, f"{asset_id}: evolution.stage must be 1, 2 or 3")
        return
    stage_name, level = EVOLUTION_STAGES[stage]
    line_id = evolution["line_id"]
    expected_id = f"{line_id}_{stage:03d}"
    if asset_id != expected_id:
        fail(errors, f"{asset_id}: id must be {expected_id} for evolution stage {stage}")
    if evolution["stage_name"] != stage_name:
        fail(errors, f"{asset_id}: evolution.stage_name must be {stage_name}")
    if evolution["requires_level"] != level:
        fail(errors, f"{asset_id}: evolution.requires_level must be {level}")
    base_id = evolution["base_id"]
    if base_id != f"{line_id}_001":
        fail(errors, f"{asset_id}: evolution.base_id must be {line_id}_001")
    base = by_id.get(base_id)
    if base is None:
        fail(errors, f"{asset_id}: evolution.base_id {base_id} does not resolve")
    next_id = evolution["next_id"]
    expected_next = f"{line_id}_{stage + 1:03d}" if stage < 3 else None
    if next_id != expected_next:
        fail(errors, f"{asset_id}: evolution.next_id must be {expected_next}")
    if next_id is not None and next_id not in by_id:
        fail(errors, f"{asset_id}: evolution.next_id {next_id} does not resolve")
    if stage == 1:
        if asset_id.endswith("_001") is False:
            fail(errors, f"{asset_id}: base pet ids must end in _001")
        if "evolved" in asset.get("tags", []):
            fail(errors, f"{asset_id}: base pet must not be tagged evolved")
    else:
        tags = set(asset.get("tags", []))
        if not {"evolved", f"stage_{stage}"} <= tags:
            fail(errors, f"{asset_id}: evolved pet must be tagged evolved and stage_{stage}")
        if not str(asset.get("unlock_condition", "")).startswith("evolve:"):
            fail(errors, f"{asset_id}: evolved pet must use an evolve unlock_condition")
        if base is not None:
            for field in ("rarity", "placement", "z_index", "allowed_slots", "pet_species", "category", "slot_type"):
                if asset.get(field) != base.get(field):
                    fail(errors, f"{asset_id}: {field} must match base pet {base_id}")


def validate_variant(errors: list[str], asset: dict, by_id: dict[str, dict]) -> None:
    asset_id = asset.get("id", "<missing id>")
    base = by_id.get(asset.get("variant_of"))
    if base is None:
        fail(errors, f"{asset_id}: variant_of {asset.get('variant_of')} does not resolve")
        return
    if base.get("type") != "item" or "variant_of" in base:
        fail(errors, f"{asset_id}: variant_of must point at a base item")
    if RARITY_ORDER.index(asset.get("rarity", "common")) < RARITY_ORDER.index(base.get("rarity", "common")):
        fail(errors, f"{asset_id}: variant rarity must not be lower than its base")
    if not {"prism", "variant"} <= set(asset.get("tags", [])):
        fail(errors, f"{asset_id}: variant must be tagged prism and variant")
    if asset.get("default_unlocked") is not False:
        fail(errors, f"{asset_id}: variant must be locked by default")
    for field in ("category", "slot_type", "allowed_slots", "placement", "z_index", "sprite_size"):
        if asset.get(field) != base.get(field):
            fail(errors, f"{asset_id}: {field} must match base item {base['id']}")


def validate_catalog(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text())
    assets = data.get("assets", [])
    ids: set[str] = set()

    if data.get("style_version") != "teen_modular_v1":
        fail(errors, "catalog style_version must be teen_modular_v1")
    if data.get("schema_version") != SCHEMA_VERSION:
        fail(errors, f"catalog schema_version must be {SCHEMA_VERSION}")
    if data.get("placement_contract_version") != PLACEMENT_CONTRACT_VERSION:
        fail(errors, f"catalog placement_contract_version must be {PLACEMENT_CONTRACT_VERSION}")
    if data.get("evolution_contract_version") != EVOLUTION_CONTRACT_VERSION:
        fail(errors, f"catalog evolution_contract_version must be {EVOLUTION_CONTRACT_VERSION}")
    by_id = {asset.get("id"): asset for asset in assets}
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

        evolution = asset.get("evolution")
        is_evolved = isinstance(evolution, dict) and evolution.get("stage", 1) != 1
        rarity = asset.get("rarity")
        cost = asset.get("xp_cost")
        if rarity not in VALID_RARITIES:
            fail(errors, f"{asset_id}: invalid rarity {rarity}")
        elif is_evolved:
            if cost != 0:
                fail(errors, f"{asset_id}: evolved pet xp_cost must be 0, got {cost}")
        else:
            lo, hi = RARITY_COSTS[rarity]
            if not isinstance(cost, int) or not lo <= cost <= hi:
                fail(errors, f"{asset_id}: xp_cost {cost} outside {rarity} range {lo}-{hi}")
        validate_unlock_condition(errors, asset, by_id)

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
            validate_evolution(errors, asset, by_id)
        elif "evolution" in asset:
            fail(errors, f"{asset_id}: only pets may carry an evolution object")

        if "variant_of" in asset:
            validate_variant(errors, asset, by_id)

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
