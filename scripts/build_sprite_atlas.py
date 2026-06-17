#!/usr/bin/env python3
"""Build sprite sheets and atlas metadata from the runtime catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"
ATLAS_PATH = ROOT / "assets" / "avatar" / "manifest" / "sprite_atlas.json"
SPRITESHEET_DIR = ROOT / "assets" / "avatar" / "spritesheets"
SHEET_WIDTH = 4096
PADDING = 0

SHEETS = {
    "avatars_starter": {
        "path": "assets/avatar/spritesheets/avatars_starter_sheet.png",
        "filter": lambda asset: asset["type"] == "avatar" and asset.get("avatar_type") == "starter",
    },
    "avatars_advanced": {
        "path": "assets/avatar/spritesheets/avatars_advanced_sheet.png",
        "filter": lambda asset: asset["type"] == "avatar" and asset.get("avatar_type") == "advanced",
    },
    "items": {
        "path": "assets/avatar/spritesheets/items_sheet.png",
        "filter": lambda asset: asset["type"] == "item",
    },
    "pets": {
        "path": "assets/avatar/spritesheets/pets_sheet.png",
        "filter": lambda asset: asset["type"] == "pet",
    },
}


def pack_assets(assets: list[dict]) -> tuple[Image.Image, dict[str, dict]]:
    x = 0
    y = 0
    row_height = 0
    placements: list[tuple[dict, Image.Image, tuple[int, int]]] = []

    for asset in assets:
        image = Image.open(ROOT / asset["asset_path"]).convert("RGBA")
        width, height = image.size
        if x and x + width > SHEET_WIDTH:
            x = 0
            y += row_height + PADDING
            row_height = 0
        placements.append((asset, image, (x, y)))
        x += width + PADDING
        row_height = max(row_height, height)

    sheet_height = max(1, y + row_height)
    sheet = Image.new("RGBA", (SHEET_WIDTH, sheet_height), (0, 0, 0, 0))
    frames: dict[str, dict] = {}
    for asset, image, (frame_x, frame_y) in placements:
        sheet.alpha_composite(image, (frame_x, frame_y))
        width, height = image.size
        frames[asset["id"]] = {
            "asset_path": asset["asset_path"],
            "sprite_size": {"width": width, "height": height},
            "source_canvas_size": asset["canvas_size"],
            "frame": {"x": frame_x, "y": frame_y, "w": width, "h": height},
        }
    return sheet, frames


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sheet",
        action="append",
        choices=sorted(SHEETS),
        help="Sheet to rebuild. Repeatable. Defaults to all sheets.",
    )
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text())
    atlas = json.loads(ATLAS_PATH.read_text())
    selected = args.sheet or sorted(SHEETS)
    atlas.setdefault("sheets", {})

    for sheet_name in selected:
        spec = SHEETS[sheet_name]
        assets = [asset for asset in catalog["assets"] if spec["filter"](asset)]
        sheet, frames = pack_assets(assets)
        sheet_path = ROOT / spec["path"]
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(sheet_path)
        atlas["sheets"][sheet_name] = {
            "sheet_path": spec["path"],
            "packing": "shelf_row_major",
            "padding": PADDING,
            "frames": frames,
        }
        print(f"Built {sheet_name}: {len(frames)} frames -> {sheet_path.relative_to(ROOT)}")

    ATLAS_PATH.write_text(json.dumps(atlas, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
