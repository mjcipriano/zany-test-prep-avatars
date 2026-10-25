#!/usr/bin/env python3
"""Render contact sheets of fitted items on a spread of avatars (visual QA for face_fit_v1).

Composes exactly as the app does: avatar full-frame (hidden above any hat's
``clip_avatar_above`` line), ``behind`` items first, worn items placed by their ``fit`` on
the avatar's ``face_rig``. Writes one PNG per category into
``--out`` (default ``build/fit_sheets``, git-ignored)::

    python3 scripts/render_fit_sheets.py --avatars 6 --category ear_accessory
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from pack_image_ops import ROOT, avatar_clip_top, fit_rect, load_catalog  # noqa: E402

FRAME = 512


def compose(avatar: dict, items: list[dict], size: int = FRAME) -> Image.Image:
    frame = Image.new("RGBA", (size, size), (236, 236, 242, 255))
    behind = [i for i in items if i["fit"].get("behind")]
    front = sorted((i for i in items if not i["fit"].get("behind")), key=lambda i: i["z_index"])
    layers = [*behind, avatar, *front]
    for layer in layers:
        image = Image.open(ROOT / layer["asset_path"]).convert("RGBA")
        if layer is avatar:
            image = image.resize((size, size), Image.LANCZOS)
            clip = int(avatar_clip_top(items, avatar["face_rig"], size))
            if clip > 0:  # hair that would be under the hat
                pixels = np.array(image)
                pixels[:clip, :, 3] = 0
                image = Image.fromarray(pixels, "RGBA")
            frame.alpha_composite(image)
            continue
        left, top, width, height = fit_rect(layer, avatar["face_rig"], size)
        sprite = image.resize((max(1, round(width)), max(1, round(height))), Image.LANCZOS)
        overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        overlay.paste(sprite, (round(left), round(top)))
        frame.alpha_composite(overlay)
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=str(ROOT / "build" / "fit_sheets"))
    parser.add_argument("--avatars", type=int, default=6, help="avatars per row (spread across the pack)")
    parser.add_argument("--category", action="append", help="limit to these categories")
    parser.add_argument("--tile", type=int, default=160)
    args = parser.parse_args()

    catalog = load_catalog()
    avatars = catalog["avatars"]
    step = max(1, len(avatars) // args.avatars)
    picks = avatars[::step][: args.avatars]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    categories = args.category or sorted({i["category"] for i in catalog["items"] if "fit" in i})
    for category in categories:
        items = [i for i in catalog["items"] if i["category"] == category and "fit" in i and "variant_of" not in i]
        tile = args.tile
        sheet = Image.new("RGB", (tile * len(picks), (tile + 14) * len(items)), "white")
        draw = ImageDraw.Draw(sheet)
        for row, item in enumerate(items):
            for col, avatar in enumerate(picks):
                image = compose(avatar, [item])
                eyes = avatar["face_rig"]["points"]["eyes"]
                cx, cy = eyes["x"] * FRAME, eyes["y"] * FRAME
                image = image.crop((cx - 130, cy - 140, cx + 130, cy + 120)).resize((tile, tile))
                sheet.paste(image.convert("RGB"), (col * tile, row * (tile + 14)))
            draw.text((2, row * (tile + 14) + tile), f"{item['id']}  {item['name']}  [{item['fit']['kind']}]", fill="black")
        path = out / f"{category}.png"
        sheet.save(path)
        print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
