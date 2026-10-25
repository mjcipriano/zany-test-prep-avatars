#!/usr/bin/env python3
"""Visual sanity checks for the avatar pack: per-PNG pixel checks plus a geometric overlap pass.

The overlap pass reproduces the renderer's contain-fit with Pillow/numpy only (no
Flutter): for every non-avatar asset and every slot it may occupy, the trimmed sprite is
fitted inside the slot's target box (centre ``cx,cy``; size ``w,h``; aspect preserved)
and the resulting rectangle is checked against the rig regions, the other slots and the
canvas. Evolved pets and prism variants are additionally checked against their base.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pack_image_ops import fit_rect  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"
SIDE_SLOTS = ("side_left_1", "side_left_2", "side_right_1", "side_right_2")

# Worn-slot pairs whose fitted rectangles must not overlap by more than this fraction of
# the smaller rectangle. The default is 35%. headwear/eyewear and eyewear/face_accessory
# target boxes overlap by design in target_box_v1 (a cap brim sits over the glasses, a
# mask sits under them), so their limits are calibrated to the contract: measured
# worst cases are 45.7% and 55.5%.
DEFAULT_PAIR_OVERLAP_LIMIT = 0.35
PAIR_OVERLAP_LIMITS = {
    ("headwear", "eyewear"): 0.50,
    ("eyewear", "face_accessory"): 0.60,
    ("headwear", "face_accessory"): DEFAULT_PAIR_OVERLAP_LIMIT,
    ("neck_accessory", "chest_badge"): DEFAULT_PAIR_OVERLAP_LIMIT,
    ("chest_badge", "face_accessory"): DEFAULT_PAIR_OVERLAP_LIMIT,
}
# The upper side-slot boxes end at x=0.355 / 0.645 while the rig head envelope starts at
# x=0.33 / 0.67 and the face box at x=0.35 / 0.65, so a near-square side sprite may reach
# at most 0.025 into the head box and 0.005 (2.5 px) into the face box. Both are inherent
# to the target_box_v1 slot geometry, not art defects; anything beyond these tolerances
# means a sprite or target box has moved over the avatar's face.
HEAD_INTRUSION_TOLERANCE = 0.03
FACE_INTRUSION_TOLERANCE = 0.01
EVOLVED_CORE_MIN_FILL = 0.70
MAX_TRANSPARENT_BORDER_PX = 2
CANVAS_EPSILON = 1e-6

Rect = tuple[float, float, float, float]


# --------------------------------------------------------------------------- pixel helpers


def alpha_bbox(image: Image.Image, threshold: int = 12) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > threshold else 0)
    return mask.getbbox()


def has_edge_contact(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    width, height = image.size
    edge_pixels = []
    edge_pixels.extend(alpha.crop((0, 0, width, 4)).getdata())
    edge_pixels.extend(alpha.crop((0, height - 4, width, height)).getdata())
    edge_pixels.extend(alpha.crop((0, 0, 4, height)).getdata())
    edge_pixels.extend(alpha.crop((width - 4, 0, width, height)).getdata())
    return any(value > 12 for value in edge_pixels)


def has_green_fringe(image: Image.Image) -> bool:
    rgba = np.asarray(image.convert("RGBA"))
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    count = int(np.count_nonzero((a > 20) & (g > 220) & (r < 90) & (b < 90)))
    return count > 80


def transparent_border(image: Image.Image) -> tuple[int, int, int, int]:
    """Fully transparent rows/columns at the left, top, right and bottom edges."""
    alpha = np.asarray(image.getchannel("A"))
    cols = np.flatnonzero(alpha.any(axis=0))
    rows = np.flatnonzero(alpha.any(axis=1))
    if len(cols) == 0 or len(rows) == 0:
        return (image.width, image.height, image.width, image.height)
    return (int(cols[0]), int(rows[0]), int(image.width - 1 - cols[-1]), int(image.height - 1 - rows[-1]))


# --------------------------------------------------------------------------- geometry helpers


def target_rect(target: dict) -> Rect:
    return (
        target["cx"] - target["w"] / 2,
        target["cy"] - target["h"] / 2,
        target["cx"] + target["w"] / 2,
        target["cy"] + target["h"] / 2,
    )


def contain_fit(sprite_size: dict, target: dict) -> Rect:
    """Rectangle (x0, y0, x1, y1) of ``sprite_size`` contain-fitted into ``target``, in 0..1 canvas units."""
    width, height = sprite_size["width"], sprite_size["height"]
    scale = min(target["w"] / width, target["h"] / height)
    fitted_w, fitted_h = width * scale, height * scale
    return (
        target["cx"] - fitted_w / 2,
        target["cy"] - fitted_h / 2,
        target["cx"] + fitted_w / 2,
        target["cy"] + fitted_h / 2,
    )


def rect_area(rect: Rect) -> float:
    return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])


def intersection_area(a: Rect, b: Rect) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def intrusion_depth(rect: Rect, region: Rect) -> float:
    """How far ``rect`` reaches horizontally into ``region`` (0 when they do not overlap)."""
    if intersection_area(rect, region) <= 0:
        return 0.0
    return min(rect[2] - region[0], region[2] - rect[0])


def targets_for(asset: dict) -> dict[str, dict]:
    placement = asset["placement"]
    by_slot = placement.get("targets_by_slot")
    if by_slot:
        return by_slot
    return {slot: placement["target"] for slot in asset["allowed_slots"]}


def fitted_rects(asset: dict) -> dict[str, Rect]:
    return {slot: contain_fit(asset["sprite_size"], target) for slot, target in targets_for(asset).items()}


# --------------------------------------------------------------------------- passes


def pixel_checks(catalog: dict) -> list[str]:
    warnings: list[str] = []
    for asset in catalog["assets"]:
        path = ROOT / asset["asset_path"]
        image = Image.open(path).convert("RGBA")
        bbox = alpha_bbox(image)
        if bbox is None:
            warnings.append(f"{asset['id']}: empty alpha")
            continue
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        if asset["type"] == "avatar":
            if image.size != (512, 512):
                warnings.append(f"{asset['id']}: avatar image is not 512x512")
            if abs(center_x - 256) > 64 or abs(center_y - 278) > 90:
                warnings.append(f"{asset['id']}: avatar rig bbox center=({center_x:.1f},{center_y:.1f})")
            if width < 220 or height < 300:
                warnings.append(f"{asset['id']}: avatar crop looks too small for shared rig")
        else:
            if bbox != (0, 0, image.width, image.height):
                warnings.append(f"{asset['id']}: non-avatar sprite is not tightly trimmed")
            sprite_size = asset.get("sprite_size", {})
            if image.size != (sprite_size.get("width"), sprite_size.get("height")):
                warnings.append(f"{asset['id']}: image size does not match sprite_size")
            border = transparent_border(image)
            if max(border) > MAX_TRANSPARENT_BORDER_PX:
                warnings.append(f"{asset['id']}: transparent border {border} px exceeds {MAX_TRANSPARENT_BORDER_PX} px")
        # The chroma-fringe heuristic targets keyed source art. Procedurally derived sprites
        # (evolved pets, prism variants) reuse their base's alpha mask, so a green hue there
        # is an intentional recolour rather than a fringe.
        is_derived = "variant_of" in asset or asset.get("evolution", {}).get("stage", 1) != 1
        if not is_derived and has_green_fringe(image):
            warnings.append(f"{asset['id']}: likely green chroma fringe remains")
        if asset["type"] in {"item", "pet"} and (width < 20 or height < 20):
            warnings.append(f"{asset['id']}: item/pet crop looks too small")
        placement = asset.get("placement", {})
        for slot, target in placement.get("targets_by_slot", {}).items():
            # Side targets should remain beside the avatar and not cover the central face region.
            if slot.startswith("side_"):
                x0 = target["cx"] - target["w"] / 2
                x1 = target["cx"] + target["w"] / 2
                y0 = target["cy"] - target["h"] / 2
                y1 = target["cy"] + target["h"] / 2
                overlaps_face_x = x0 < 0.64 and x1 > 0.36
                overlaps_face_y = y0 < 0.44 and y1 > 0.18
                if overlaps_face_x and overlaps_face_y:
                    warnings.append(f"{asset['id']}: side target {slot} overlaps face region")
    return warnings


def geometry_checks(catalog: dict) -> list[str]:
    """Contain-fit overlap pass; pure catalog geometry, no PNG decoding."""
    warnings: list[str] = []
    by_id = {asset["id"]: asset for asset in catalog["assets"]}
    regions = catalog["rig"]["regions"]
    head = target_rect(regions["head"])
    face = target_rect(regions["face"])
    slots = catalog["slots"]

    # (b) the four side-slot target boxes never intersect each other.
    for slot_a, slot_b in itertools.combinations(SIDE_SLOTS, 2):
        if intersection_area(target_rect(slots[slot_a]["target"]), target_rect(slots[slot_b]["target"])) > 0:
            warnings.append(f"slots: side targets {slot_a} and {slot_b} intersect")

    rects_by_slot: dict[str, list[tuple[str, Rect]]] = {}
    for asset in catalog["assets"]:
        if asset["type"] == "avatar":
            continue
        for slot, rect in fitted_rects(asset).items():
            # (a) fitted rect lies inside the 0..1 canvas.
            if rect[0] < -CANVAS_EPSILON or rect[1] < -CANVAS_EPSILON or rect[2] > 1 + CANVAS_EPSILON or rect[3] > 1 + CANVAS_EPSILON:
                warnings.append(f"{asset['id']}: fitted rect for {slot} leaves the canvas {tuple(round(v, 4) for v in rect)}")
            # (b) side sprites keep off the face and reach at most marginally into the head envelope.
            if slot in SIDE_SLOTS:
                depth = intrusion_depth(rect, face)
                if depth > FACE_INTRUSION_TOLERANCE:
                    warnings.append(f"{asset['id']}: fitted rect for {slot} intersects rig face region ({depth:.3f})")
                depth = intrusion_depth(rect, head)
                if depth > HEAD_INTRUSION_TOLERANCE:
                    warnings.append(f"{asset['id']}: fitted rect for {slot} reaches {depth:.3f} into rig head region")
            rects_by_slot.setdefault(slot, []).append((asset["id"], rect))

    # (c) worn-slot pair overlap, as a fraction of the smaller fitted rect.
    for (slot_a, slot_b), limit in PAIR_OVERLAP_LIMITS.items():
        worst = (0.0, None, None)
        for id_a, rect_a in rects_by_slot.get(slot_a, []):
            for id_b, rect_b in rects_by_slot.get(slot_b, []):
                smaller = min(rect_area(rect_a), rect_area(rect_b))
                if smaller <= 0:
                    continue
                fraction = intersection_area(rect_a, rect_b) / smaller
                if fraction > worst[0]:
                    worst = (fraction, id_a, id_b)
        if worst[0] > limit:
            warnings.append(
                f"{worst[1]} x {worst[2]}: {slot_a}/{slot_b} fitted rects overlap {worst[0]:.1%} of the smaller rect (limit {limit:.0%})"
            )

    # (d) evolved pets inherit placement and keep their non-glow core large after contain-fit.
    for asset in catalog["assets"]:
        evolution = asset.get("evolution")
        if not evolution:
            continue
        base = by_id.get(evolution["base_id"])
        if base is None:
            warnings.append(f"{asset['id']}: evolution.base_id {evolution['base_id']} does not resolve")
            continue
        if evolution["next_id"] is not None and evolution["next_id"] not in by_id:
            warnings.append(f"{asset['id']}: evolution.next_id {evolution['next_id']} does not resolve")
        if evolution["stage"] == 1:
            continue
        if asset["placement"] != base["placement"]:
            warnings.append(f"{asset['id']}: placement differs from base {base['id']}")
        for slot, target in targets_for(asset).items():
            base_scale = min(target["w"] / base["sprite_size"]["width"], target["h"] / base["sprite_size"]["height"])
            evolved_scale = min(target["w"] / asset["sprite_size"]["width"], target["h"] / asset["sprite_size"]["height"])
            # The core (the base pet) fills the box in its limiting dimension at base_scale;
            # after the glow padding it fills evolved_scale / base_scale of that.
            core_fill = evolved_scale / base_scale
            if core_fill < EVOLVED_CORE_MIN_FILL:
                warnings.append(
                    f"{asset['id']}: non-glow core fills only {core_fill:.1%} of the {slot} box after contain-fit"
                )

    # variant_of resolution for prism items.
    for asset in catalog["assets"]:
        if "variant_of" in asset and asset["variant_of"] not in by_id:
            warnings.append(f"{asset['id']}: variant_of {asset['variant_of']} does not resolve")
    return warnings


def evolution_pixel_checks(catalog: dict) -> list[str]:
    """Stage 2 keeps the base alpha; stage 3's opaque core is still at least the base silhouette."""
    warnings: list[str] = []
    by_id = {asset["id"]: asset for asset in catalog["assets"]}
    for asset in catalog["assets"]:
        evolution = asset.get("evolution")
        if not evolution or evolution["stage"] == 1:
            continue
        base = by_id.get(evolution["base_id"])
        if base is None:
            continue
        base_alpha = np.asarray(Image.open(ROOT / base["asset_path"]).convert("RGBA").getchannel("A"))
        evolved_alpha = np.asarray(Image.open(ROOT / asset["asset_path"]).convert("RGBA").getchannel("A"))
        if evolution["stage"] == 2:
            if evolved_alpha.shape != base_alpha.shape:
                warnings.append(f"{asset['id']}: shiny sprite size differs from base")
            elif not np.array_equal(evolved_alpha[base_alpha > 0], base_alpha[base_alpha > 0]):
                warnings.append(f"{asset['id']}: shiny sprite changed alpha on base pixels")
        else:
            base_opaque = int(np.count_nonzero(base_alpha == 255))
            evolved_opaque = int(np.count_nonzero(evolved_alpha == 255))
            if evolved_opaque < base_opaque:
                warnings.append(f"{asset['id']}: radiant sprite lost opaque core pixels ({evolved_opaque} < {base_opaque})")
            pad_w = evolved_alpha.shape[1] - base_alpha.shape[1]
            pad_h = evolved_alpha.shape[0] - base_alpha.shape[0]
            if pad_w < 0 or pad_h < 0 or pad_w > 0.25 * base_alpha.shape[1] + 2 or pad_h > 0.25 * base_alpha.shape[0] + 2:
                warnings.append(f"{asset['id']}: radiant glow padding ({pad_w}x{pad_h} px) outside the 0..12% per side budget")
    return warnings


def variant_pixel_checks(catalog: dict) -> list[str]:
    warnings: list[str] = []
    by_id = {asset["id"]: asset for asset in catalog["assets"]}
    for asset in catalog["assets"]:
        base = by_id.get(asset.get("variant_of"))
        if base is None:
            continue
        base_alpha = np.asarray(Image.open(ROOT / base["asset_path"]).convert("RGBA").getchannel("A"))
        variant_alpha = np.asarray(Image.open(ROOT / asset["asset_path"]).convert("RGBA").getchannel("A"))
        if base_alpha.shape != variant_alpha.shape or not np.array_equal(base_alpha, variant_alpha):
            warnings.append(f"{asset['id']}: variant alpha differs from base {base['id']}")
    return warnings


# face_fit_v1 sanity bounds, as shares of the 512 frame.
FIT_MAX_OVERFLOW = 0.25  # renderers shrink the scene (to >= 0.8) for hats that poke above the frame
FIT_EYE_CLEARANCE = -0.01  # masks, gaiters, nose strips and moustaches start below the eye line
FIT_EYE_CENTRING = 0.02  # glasses centre on the eyes
LOWER_FACE_KINDS = {"mask", "gaiter", "nose_strip", "mustache"}


def face_fit_checks(catalog: dict) -> list[str]:
    """Place every fitted item on every avatar and check it lands where its kind belongs."""
    warnings: list[str] = []
    fitted = [item for item in catalog["items"] if "fit" in item]
    for avatar in catalog["avatars"]:
        rig = avatar.get("face_rig")
        if rig is None:
            warnings.append(f"{avatar['id']}: missing face_rig")
            continue
        points = rig["points"]
        for item in fitted:
            left, top, width, height = fit_rect(item, rig, 1.0)
            pair = f"{item['id']} on {avatar['id']}"
            overflow = max(-left, -top, left + width - 1.0, top + height - 1.0)
            if overflow > FIT_MAX_OVERFLOW:
                warnings.append(f"{pair}: extends {overflow:.3f} past the frame")
            kind = item["fit"]["kind"]
            if kind in LOWER_FACE_KINDS and top - points["eyes"]["y"] < FIT_EYE_CLEARANCE:
                warnings.append(f"{pair}: {kind} covers the eyes")
            if kind == "glasses":
                cx, cy = left + width / 2, top + height / 2
                if abs(cx - points["eyes"]["x"]) > FIT_EYE_CENTRING or abs(cy - points["eyes"]["y"]) > FIT_EYE_CENTRING:
                    warnings.append(f"{pair}: glasses are not centred on the eyes")
    return warnings


def qa(catalog: dict | None = None) -> list[str]:
    catalog = catalog or json.loads(CATALOG.read_text())
    return [
        *pixel_checks(catalog),
        *geometry_checks(catalog),
        *evolution_pixel_checks(catalog),
        *variant_pixel_checks(catalog),
        *face_fit_checks(catalog),
    ]


def main() -> int:
    warnings = qa()
    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 1
    print("Avatar visual QA passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
