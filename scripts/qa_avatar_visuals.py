#!/usr/bin/env python3
"""Visual sanity checks for cropped avatar PNG assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"


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
    rgba = image.convert("RGBA")
    count = 0
    for r, g, b, a in rgba.getdata():
        if a > 20 and g > 220 and r < 90 and b < 90:
            count += 1
            if count > 80:
                return True
    return False


def qa() -> list[str]:
    catalog = json.loads(CATALOG.read_text())
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
        if has_green_fringe(image):
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
