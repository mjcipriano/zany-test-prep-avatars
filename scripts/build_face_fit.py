#!/usr/bin/env python3
"""Apply the ``face_fit_v1`` contract to the catalog (and tidy the sprites it relies on).

The ``target_box_v1`` boxes are one size and position per slot, but the avatars'
heads are not: they sit at different heights and sizes, so a mask meant for the
mouth covered some avatars' eyes and earrings landed on cheeks. ``face_fit_v1``
anchors worn items to each avatar's own face instead:

* every avatar gets a ``face_rig`` (named points + reference widths, measured by
  ``measure_face_rigs.py`` into ``data/face_rigs.json``);
* every headwear / eyewear / face / ear item gets a ``fit``: which rig point it
  hangs on (``anchor``), which point of the sprite goes there (``sprite_anchor``,
  0..1 of the sprite), and how wide it is (``width`` x the rig's ``width_ref``),
  plus ``behind`` for items drawn behind the avatar (hoods, the headset).

Renderer rule: ``w = rig.widths[width_ref] * width * 512``, ``h = w / sprite
aspect``, ``left = rig.points[anchor].x * 512 - sprite_anchor.x * w`` (same for
y). Items without a ``fit``, or avatars without a ``face_rig``, keep using the
``target_box_v1`` placement.

It also fixes the sprites the fit depends on, idempotently:

* removes stray thin horizontal lines detached from the art (24 eyewear sprites
  and 10 avatars carried one), re-trimming items;
* re-lays each earring pair so neither earring dwarfs the face and records the
  pair's attachment points as the fit (studs hang at their centre, drops and
  hoops at their top);
* corrects display names that did not match the art (``data/item_fit.json``).

Run after build_item_variants.py; then build_flutter_manifest.py and
build_sprite_atlas.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pack_image_ops import ROOT, load_catalog, save_catalog, save_png, trim_to_alpha  # noqa: E402

FACE_FIT_CONTRACT_VERSION = "face_fit_v1"
SCHEMA_VERSION = "3.2.0"
RIGS_PATH = ROOT / "data" / "face_rigs.json"
FIT_PATH = ROOT / "data" / "item_fit.json"

RIG_POINTS = (
    "eye_l", "eye_r", "eyes", "brow", "forehead", "nose_bridge", "nose", "under_nose",
    "mouth", "chin", "cheek_l", "cheek_r", "cheeks", "face_l", "face_r", "ear_l", "ear_r", "ears",
    "crown",
)
RIG_WIDTHS = ("face", "eyes", "mouth", "ears", "head", "hair")
FRONT_STRIP_ALPHA = 40
FIT_CATEGORIES = ("headwear", "eyewear", "face_accessory", "ear_accessory")

# Stray-line detection: a band of rows at most LINE_MAX_ROWS tall, spanning at least
# LINE_MIN_SPAN of the width, separated from the art by fully transparent rows.
LINE_ALPHA = 40
LINE_MAX_ROWS = 8
LINE_MIN_SPAN = 0.25
# Re-trim at the QA visibility threshold so no near-invisible fringe is left as border.
TRIM_ALPHA = 12

# Earrings are scaled down (about their attachment point) until each is at most this
# share of the distance between the pair's attachment points.
EARRING_MAX_H = 0.30
EARRING_MAX_W = 0.14
EARRING_TOLERANCE = 0.05


# --------------------------------------------------------------------------- sprites


def _row_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    occupied = mask.any(axis=1)
    segments, start = [], None
    for y, filled in enumerate(occupied):
        if filled and start is None:
            start = y
        elif not filled and start is not None:
            segments.append((start, y))
            start = None
    if start is not None:
        segments.append((start, len(occupied)))
    return segments


def stray_line_rows(image: Image.Image) -> list[tuple[int, int]]:
    """Row ranges to clear: each detached thin line plus the faint gap to the art."""
    mask = np.asarray(image.convert("RGBA"))[:, :, 3] > LINE_ALPHA
    segments = _row_segments(mask)
    if len(segments) < 2:
        return []
    main = max(segments, key=lambda s: int(mask[s[0]:s[1]].sum()))
    lines = [
        s for s in segments
        if s != main
        and s[1] - s[0] <= LINE_MAX_ROWS
        and mask[s[0]:s[1]].any(axis=0).sum() >= LINE_MIN_SPAN * mask.shape[1]
    ]
    kept = [s for s in segments if s not in lines]
    ranges = []
    for start, end in lines:
        above = [k[1] for k in kept if k[1] <= start]
        below = [k[0] for k in kept if k[0] >= end]
        ranges.append((max(above) if above else 0, min(below) if below else mask.shape[0]))
    return ranges


def remove_stray_lines(image: Image.Image) -> Image.Image | None:
    """The image with stray lines cleared, or None when it has none."""
    ranges = stray_line_rows(image)
    if not ranges:
        return None
    pixels = np.array(image.convert("RGBA"))
    for start, end in ranges:
        pixels[start:end, :, 3] = 0
        pixels[start:end, :, :3] = 0
    return Image.fromarray(pixels, "RGBA")


def _split_column(mask: np.ndarray) -> int:
    """Column between the two earrings: the middle of the widest empty run near the centre."""
    cols = mask.any(axis=0)
    width = mask.shape[1]
    best, run = None, None
    for x in range(int(width * 0.2), int(width * 0.8)):
        if cols[x]:
            run = None
            continue
        run = (run[0], x) if run else (x, x)
        if best is None or run[1] - run[0] > best[1] - best[0]:
            best = run
    return (best[0] + best[1]) // 2 if best else width // 2


def _box(mask: np.ndarray, x0: int, x1: int) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask[:, x0:x1])
    return x0 + int(xs.min()), int(ys.min()), x0 + int(xs.max()) + 1, int(ys.max()) + 1


def _attach(box: tuple[int, int, int, int]) -> tuple[float, float]:
    """Where an earring meets the lobe: a round stud's centre, a drop's top."""
    left, top, right, bottom = box
    return (left + right) / 2, top + min(right - left, bottom - top) / 2


def fit_earring_pair(image: Image.Image) -> tuple[Image.Image, dict, float]:
    """Re-lay a left/right earring pair; returns (sprite, sprite_anchor, span share).

    ``span share`` is the distance between the two attachment points as a share of
    the returned sprite's width, so ``width = 1 / span`` makes the attachment points
    land on the rig's ear points. Idempotent: a re-laid pair comes back unchanged.
    """
    image = image.convert("RGBA")
    mask = np.asarray(image)[:, :, 3] > LINE_ALPHA
    cut = _split_column(mask)
    boxes = (_box(mask, 0, cut), _box(mask, cut, mask.shape[1]))
    attach = [_attach(b) for b in boxes]
    span = attach[1][0] - attach[0][0]
    parts = []
    for (left, top, right, bottom), (ax, ay) in zip(boxes, attach):
        w, h = right - left, bottom - top
        s = min(1.0, EARRING_MAX_H * span / h, EARRING_MAX_W * span / w)
        if s > 1.0 - EARRING_TOLERANCE:  # already re-laid: rounding must not shrink it again
            s = 1.0
        crop = image.crop((left, top, right, bottom))
        if s < 1.0:
            crop = crop.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
        parts.append((crop, round(ax - (ax - left) * s), round(ay - (ay - top) * s)))
    min_x = min(x for _, x, _ in parts)
    min_y = min(y for _, _, y in parts)
    width = max(x + c.width for c, x, _ in parts) - min_x
    height = max(y + c.height for c, _, y in parts) - min_y
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for crop, x, y in parts:
        canvas.alpha_composite(crop, (x - min_x, y - min_y))
    trimmed = trim_to_alpha(canvas, TRIM_ALPHA)
    bbox = canvas.getchannel("A").point(lambda a: 255 if a > TRIM_ALPHA else 0).getbbox()
    off_x, off_y = (bbox[0], bbox[1]) if bbox else (0, 0)
    mid_x = (attach[0][0] + attach[1][0]) / 2 - min_x - off_x
    mid_y = (attach[0][1] + attach[1][1]) / 2 - min_y - off_y
    anchor = {"x": round(mid_x / trimmed.width, 4), "y": round(mid_y / trimmed.height, 4)}
    return trimmed, anchor, span / trimmed.width


def _run_around(row: np.ndarray, x: int) -> tuple[int, int]:
    """[left, right) of the opaque run in ``row`` that contains column ``x``."""
    left = right = x
    while left > 0 and row[left - 1]:
        left -= 1
    while right < len(row) - 1 and row[right + 1]:
        right += 1
    return left, right + 1


def head_metrics(image: Image.Image, rig: dict) -> dict:
    """Hair-aware head measurements from the avatar's silhouette (alpha), to add to its rig.

    Face landmarks say nothing about hair volume, so hats sized from the face sat on top
    of big curly hair. From the silhouette: ``crown`` (top of the head above the eyes),
    ``head`` (silhouette width at the brow line) and ``hair`` (the smaller of that and
    the width halfway between crown and brow, so buns and ponytails do not count).
    """
    alpha = np.asarray(image.convert("RGBA"))[:, :, 3] > 128
    height, width = alpha.shape
    points = rig["points"]
    cx = int(round(points["eyes"]["x"] * width))
    half = max(2, int(0.25 * rig["widths"]["face"] * width))
    band = alpha[:, max(0, cx - half): cx + half]
    rows = np.nonzero(band.any(axis=1))[0]
    crown_y = rows.min() / height if len(rows) else points["forehead"]["y"]
    brow_row = min(height - 1, int(points["brow"]["y"] * height))
    mid_row = min(height - 1, int((crown_y + points["brow"]["y"]) / 2 * height))
    if not alpha[brow_row, cx] or not alpha[mid_row, cx]:
        head = hair = rig["widths"]["face"]
    else:
        left, right = _run_around(alpha[brow_row], cx)
        head = (right - left) / width
        left, right = _run_around(alpha[mid_row], cx)
        hair = min(head, (right - left) / width)
    return {
        "crown": {"x": points["eyes"]["x"], "y": round(float(crown_y), 4)},
        "head": round(float(head), 4),
        "hair": round(float(hair), 4),
    }


def front_strip(image: Image.Image) -> Image.Image:
    """Keep only the front band of a ring drawn from above (headbands).

    A headband drawn from slightly above shows its back arc over the top of the head;
    worn, that arc is hidden behind the head. Per column keep the bottom-most strip as
    thick as the front band at the centre column. Idempotent.
    """
    pixels = np.array(image.convert("RGBA"))
    mask = pixels[:, :, 3] > FRONT_STRIP_ALPHA
    height, width = mask.shape
    centre = np.nonzero(mask[:, width // 2])[0]
    if len(centre) == 0:
        return image
    # Thickness of the lowest run at the centre column.
    bottom = centre[-1]
    top = bottom
    while top > 0 and mask[top - 1, width // 2]:
        top -= 1
    thickness = bottom - top + 1
    for x in range(width):
        ys = np.nonzero(mask[:, x])[0]
        if len(ys):
            pixels[: max(0, ys[-1] - thickness + 1), x, 3] = 0
    return trim_to_alpha(Image.fromarray(pixels, "RGBA"), TRIM_ALPHA)


# --------------------------------------------------------------------------- catalog


def fit_from_kind(kind: str, spec: dict) -> dict:
    fit = {
        "kind": kind,
        "anchor": spec["anchor"],
        "sprite_anchor": {"x": spec["sprite_anchor"]["x"], "y": spec["sprite_anchor"]["y"]},
        "width_ref": spec["width_ref"],
        "width": spec["width"],
        "behind": bool(spec.get("behind", False)),
    }
    if "width_floor" in spec:
        fit["width_floor"] = {"ref": spec["width_floor"]["ref"], "width": spec["width_floor"]["width"]}
    if spec.get("clip_avatar_above") is not None:
        fit["clip_avatar_above"] = spec["clip_avatar_above"]
    return fit


def _store(asset: dict, image: Image.Image) -> None:
    path = ROOT / asset["asset_path"]
    save_png(image, path)
    asset["sprite_size"] = {"width": image.width, "height": image.height}


def apply(catalog: dict, rigs: dict, fit_data: dict) -> dict[str, int]:
    """Mutate ``catalog`` in place; returns counts of what changed (for the log)."""
    stats = {"rigs": 0, "fits": 0, "lines_removed": 0, "earrings": 0, "renamed": 0, "strips": 0, "built_in": 0}
    built_in = fit_data.get("built_in", {})
    kind_of = {item_id: kind for kind, ids in fit_data["items"].items() for item_id in ids}
    renames = fit_data.get("renames", {})

    for avatar in catalog["avatars"]:
        path = ROOT / avatar["asset_path"]
        with Image.open(path) as image:
            cleaned = remove_stray_lines(image)
        if cleaned is not None:
            save_png(cleaned, path)
            stats["lines_removed"] += 1
        rig = rigs.get(avatar["id"])
        if rig is not None:
            rig = json.loads(json.dumps(rig))  # don't mutate the measured data
            with Image.open(path) as image:
                extra = head_metrics(image, rig)
            rig["points"]["crown"] = extra["crown"]
            rig["widths"]["head"] = extra["head"]
            rig["widths"]["hair"] = extra["hair"]
            avatar["face_rig"] = rig
            stats["rigs"] += 1
        slots = built_in.get(avatar["id"])
        if slots:
            avatar["built_in_slots"] = list(slots)
            stats["built_in"] += 1
        else:
            avatar.pop("built_in_slots", None)

    by_id = {item["id"]: item for item in catalog["items"]}
    for item in catalog["items"]:
        base_id = item.get("variant_of", item["id"])
        if base_id in renames:
            name = renames[base_id]
            name = f"{name} (Prism)" if "variant_of" in item else name
            if item["name"] != name:
                item["name"] = name
                stats["renamed"] += 1
        if item["category"] not in FIT_CATEGORIES:
            continue
        path = ROOT / item["asset_path"]
        with Image.open(path) as opened:
            image = opened.convert("RGBA")
        cleaned = remove_stray_lines(image)
        if cleaned is not None:
            image = trim_to_alpha(cleaned, TRIM_ALPHA)
            _store(item, image)
            stats["lines_removed"] += 1
        if item["category"] == "ear_accessory":
            relaid, anchor, span = fit_earring_pair(image)
            if relaid.size != image.size or np.any(np.asarray(relaid) != np.asarray(image)):
                _store(item, relaid)
                stats["earrings"] += 1
            item["fit"] = {
                "kind": "earring",
                "anchor": "ears",
                "sprite_anchor": anchor,
                "width_ref": "ears",
                "width": round(1.0 / span, 4),
                "behind": False,
            }
        elif base_id in kind_of:
            kind = kind_of[base_id]
            spec = fit_data["kinds"][kind]
            if spec.get("front_strip"):
                strip = front_strip(image)
                if strip.size != image.size or np.any(np.asarray(strip) != np.asarray(image)):
                    _store(item, strip)
                    stats["strips"] += 1
            item["fit"] = fit_from_kind(kind, spec)
        else:
            continue
        stats["fits"] += 1
    # Variants must keep their base's geometry (validator rule): copy it across.
    for item in catalog["items"]:
        base = by_id.get(item.get("variant_of"))
        if base is not None and "fit" in base:
            item["sprite_size"] = dict(base["sprite_size"])
    catalog["schema_version"] = SCHEMA_VERSION
    catalog["face_fit_contract_version"] = FACE_FIT_CONTRACT_VERSION
    return stats


def main() -> int:
    catalog = load_catalog()
    rigs = json.loads(RIGS_PATH.read_text())
    fit_data = json.loads(FIT_PATH.read_text())
    stats = apply(catalog, rigs, fit_data)
    save_catalog(catalog)
    print(
        "face_fit_v1: {rigs} avatar rigs, {fits} item fits, {lines_removed} stray lines removed, "
        "{earrings} earring pairs re-laid, {strips} headbands stripped, {renamed} names fixed, "
        "{built_in} avatars with built-in items".format(**stats)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
