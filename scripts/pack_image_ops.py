#!/usr/bin/env python3
"""Shared procedural image operations and catalog helpers for the avatar pack build scripts.

Everything here is deterministic: the same input PNG bytes, the same parameters and the
same seed always produce the same output pixels, so the generated assets are
reproducible and can be rebuilt from the base art at any time.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"

PALE_GOLD = (255, 236, 170)
WHITE = (255, 255, 255)


# --------------------------------------------------------------------------- catalog


def load_catalog(path: Path = CATALOG_PATH) -> dict:
    return json.loads(path.read_text())


def save_catalog(catalog: dict, path: Path = CATALOG_PATH) -> None:
    """Rebuild the flattened ``assets`` list from the typed lists and write the catalog.

    The catalog keeps ``avatars``, ``items`` and ``pets`` as the editable lists and
    ``assets`` as their concatenation in that order. Rebuilding here keeps both views
    identical no matter which build script touched the catalog last.
    """
    catalog["assets"] = [*catalog["avatars"], *catalog["items"], *catalog["pets"]]
    path.write_text(json.dumps(catalog, indent=2) + "\n")


def stable_hash(text: str) -> int:
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16)


def fit_rect(item: dict, rig: dict, size: float = 512) -> tuple[float, float, float, float]:
    """(left, top, width, height) of a ``face_fit_v1`` item on an avatar's rig, in a ``size`` frame.

    ``width = rig.widths[width_ref] * fit.width``, raised to at least
    ``rig.widths[width_floor.ref] * width_floor.width`` when the fit has a floor (hats
    cover big hair); the height follows the sprite's aspect; the sprite point
    ``fit.sprite_anchor`` lands on ``rig.points[fit.anchor]``.
    """
    fit = item["fit"]
    point = rig["points"][fit["anchor"]]
    width = rig["widths"][fit["width_ref"]] * fit["width"]
    floor = fit.get("width_floor")
    if floor and floor["ref"] in rig["widths"]:
        width = max(width, rig["widths"][floor["ref"]] * floor["width"])
    width *= size
    sprite = item["sprite_size"]
    height = width * sprite["height"] / sprite["width"]
    left = point["x"] * size - fit["sprite_anchor"]["x"] * width
    top = point["y"] * size - fit["sprite_anchor"]["y"] * height
    return left, top, width, height


def avatar_clip_top(items: list[dict], rig: dict, size: float = 512) -> float:
    """Top edge (pixels) above which the avatar is hidden: hair that would be under a hat.

    Each fitted item with ``clip_avatar_above: f`` hides the avatar above ``top + f *
    height`` of its rect; the lowest such line wins. 0 when nothing clips.
    """
    line = 0.0
    for item in items:
        fraction = item.get("fit", {}).get("clip_avatar_above")
        if fraction is None:
            continue
        _, top, _, height = fit_rect(item, rig, size)
        line = max(line, top + fraction * height)
    return line


# --------------------------------------------------------------------------- colour maths


def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """Vectorised RGB (0..1 floats, shape (..., 3)) to HSV (h in 0..1)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-12), 0.0)
    safe_delta = np.where(delta > 0, delta, 1.0)
    rc = (maxc - r) / safe_delta
    gc = (maxc - g) / safe_delta
    bc = (maxc - b) / safe_delta
    h = np.where(
        maxc == r,
        bc - gc,
        np.where(maxc == g, 2.0 + rc - bc, 4.0 + gc - rc),
    )
    h = np.where(delta > 0, (h / 6.0) % 1.0, 0.0)
    return np.stack([h, s, v], axis=-1)


def hsv_to_rgb(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0] % 1.0, hsv[..., 1], hsv[..., 2]
    i = np.floor(h * 6.0).astype(np.int64) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def recolour_hue(
    image: Image.Image,
    hue_degrees: float | np.ndarray,
    saturation_gain: float = 1.0,
    contrast: float = 1.0,
) -> Image.Image:
    """Rotate hue (and optionally boost saturation/contrast) without touching alpha.

    The maths runs on alpha-premultiplied colour so anti-aliased edge pixels keep the
    same coverage and do not pick up halos. ``hue_degrees`` may be a scalar or a
    per-column array of length ``image.width`` (used for the prism gradient). Fully
    transparent pixels are left exactly as they were and the alpha channel is copied
    through unchanged.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
    alpha = rgba[..., 3:4]
    visible = rgba[..., 3] > 0
    premultiplied = rgba[..., :3] * alpha
    hsv = rgb_to_hsv(premultiplied)
    if np.isscalar(hue_degrees):
        shift = np.full(hsv.shape[:2], float(hue_degrees), dtype=np.float32)
    else:
        shift = np.broadcast_to(np.asarray(hue_degrees, dtype=np.float32)[None, :], hsv.shape[:2])
    hsv[..., 0] = (hsv[..., 0] + shift / 360.0) % 1.0
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation_gain, 0.0, 1.0)
    if contrast != 1.0:
        hsv[..., 2] = np.clip((hsv[..., 2] - 0.5 * alpha[..., 0]) * contrast + 0.5 * alpha[..., 0], 0.0, 1.0)
    rotated = hsv_to_rgb(hsv)
    straight = np.where(alpha > 0, rotated / np.maximum(alpha, 1e-6), 0.0)
    straight = np.clip(straight, 0.0, 1.0)
    out = rgba.copy()
    out[..., :3] = np.where(visible[..., None], straight, rgba[..., :3])
    return Image.fromarray(np.round(out * 255.0).astype(np.uint8), "RGBA")


def tint_towards(image: Image.Image, weight: np.ndarray, colour: tuple[int, int, int]) -> Image.Image:
    """Lerp visible pixel colour towards ``colour`` by a per-pixel ``weight`` (0..1)."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float32)
    target = np.asarray(colour, dtype=np.float32)
    w = np.clip(weight, 0.0, 1.0)[..., None]
    out = rgba.copy()
    out[..., :3] = rgba[..., :3] * (1.0 - w) + target * w
    return Image.fromarray(np.round(out).astype(np.uint8), "RGBA")


# --------------------------------------------------------------------------- masks


def alpha_mask(image: Image.Image, threshold: int = 0) -> Image.Image:
    return image.getchannel("A").point(lambda value: 255 if value > threshold else 0)


def dilate(mask: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return mask
    return mask.filter(ImageFilter.MaxFilter(2 * radius + 1))


def erode(mask: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return mask
    return mask.filter(ImageFilter.MinFilter(2 * radius + 1))


# --------------------------------------------------------------------------- sparkles


def sparkle_positions(
    image: Image.Image,
    count: int,
    rng: random.Random,
    radius: int,
    min_gap: int,
    max_gap: int,
) -> list[tuple[int, int]]:
    """Pick sparkle centres in the transparent margin around the silhouette.

    Candidates sit between ``min_gap`` and ``max_gap`` pixels away from any visible
    pixel, at least ``radius + 1`` px from the canvas edge (so the sprite's trim box
    does not change) and at least ``3 * radius`` px apart from each other.
    """
    base = alpha_mask(image)
    ring = np.asarray(dilate(base, max_gap), dtype=bool) & ~np.asarray(dilate(base, min_gap), dtype=bool)
    height, width = ring.shape
    margin = radius + 1
    ring[:margin, :] = False
    ring[height - margin :, :] = False
    ring[:, :margin] = False
    ring[:, width - margin :] = False
    ys, xs = np.nonzero(ring)
    if len(xs) == 0:
        return []
    order = list(range(len(xs)))
    rng.shuffle(order)
    chosen: list[tuple[int, int]] = []
    min_dist_sq = (3 * radius) ** 2
    for index in order:
        x, y = int(xs[index]), int(ys[index])
        if all((x - cx) ** 2 + (y - cy) ** 2 >= min_dist_sq for cx, cy in chosen):
            chosen.append((x, y))
            if len(chosen) >= count:
                break
    return chosen


def draw_sparkles(
    image: Image.Image,
    positions: list[tuple[int, int]],
    rng: random.Random,
    radius: int,
    colours: tuple[tuple[int, int, int], ...] = (WHITE, PALE_GOLD),
    protect: Image.Image | None = None,
) -> Image.Image:
    """Composite anti-aliased 4-point star sparkles (with a soft halo) onto ``image``.

    ``protect`` is an optional ``L`` mask; where it is non-zero the sparkle layer is
    erased before compositing, so sparkles never cover (or change the alpha of) the
    protected pixels. The pet builders pass the base silhouette here.
    """
    if not positions:
        return image
    scale = 4
    width, height = image.size
    layer = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    halo = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(layer)
    halo_draw = ImageDraw.Draw(halo)
    for x, y in positions:
        size = radius * rng.uniform(0.7, 1.0) * scale
        colour = colours[rng.randrange(len(colours))]
        alpha = rng.randint(190, 235)
        angle = rng.choice((0.0, 0.0, 22.5))
        cx, cy = x * scale + scale / 2, y * scale + scale / 2
        points = []
        for k in range(8):
            theta = np.deg2rad(angle + k * 45.0)
            r = size if k % 2 == 0 else size * 0.28
            points.append((cx + r * np.cos(theta), cy + r * np.sin(theta)))
        draw.polygon(points, fill=(*colour, alpha))
        halo_draw.ellipse((cx - size * 0.9, cy - size * 0.9, cx + size * 0.9, cy + size * 0.9), fill=110)
    halo = halo.filter(ImageFilter.GaussianBlur(radius * scale * 0.6))
    halo_rgba = Image.new("RGBA", layer.size, (*PALE_GOLD, 0))
    halo_rgba.putalpha(halo)
    layer = Image.alpha_composite(halo_rgba, layer)
    layer = layer.resize((width, height), Image.Resampling.LANCZOS)
    if protect is not None:
        layer_alpha = np.asarray(layer.getchannel("A"), dtype=np.uint8)
        keep = np.asarray(protect, dtype=np.uint8) == 0
        layer.putalpha(Image.fromarray(np.where(keep, layer_alpha, 0).astype(np.uint8), "L"))
    return Image.alpha_composite(image, layer)


# --------------------------------------------------------------------------- glow / rim


def add_outer_glow(
    image: Image.Image,
    pad_x: int,
    pad_y: int,
    colour: tuple[int, int, int],
    strength: float,
    spread: int,
) -> Image.Image:
    """Return ``image`` on a canvas enlarged by ``pad_x``/``pad_y`` with a soft glow behind it.

    The glow is the dilated silhouette, Gaussian blurred so its tail reaches zero inside
    the padding, tinted with ``colour`` and composited *under* the sprite. Opaque pixels
    are therefore unchanged; the glow only shows outside (and faintly through
    anti-aliased edges of) the silhouette.
    """
    width, height = image.size
    canvas_size = (width + 2 * pad_x, height + 2 * pad_y)
    padded = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    padded.alpha_composite(image, (pad_x, pad_y))
    silhouette = alpha_mask(padded, 40)
    sigma = max(1.0, min(pad_x, pad_y) / 3.2)
    blurred = dilate(silhouette, spread).filter(ImageFilter.GaussianBlur(sigma))
    glow_alpha = np.asarray(blurred, dtype=np.float32) / 255.0
    glow_alpha = np.clip(glow_alpha * 1.25, 0.0, 1.0) * strength
    glow = Image.new("RGBA", canvas_size, (*colour, 0))
    glow.putalpha(Image.fromarray(np.round(glow_alpha * 255.0).astype(np.uint8), "L"))
    return Image.alpha_composite(glow, padded)


def add_rim_light(image: Image.Image, colour: tuple[int, int, int], thickness: int, strength: float) -> Image.Image:
    """Brighten a thin band just inside the silhouette edge towards ``colour``."""
    solid = alpha_mask(image, 128)
    band = np.asarray(solid, dtype=np.float32) - np.asarray(erode(solid, thickness), dtype=np.float32)
    band = Image.fromarray(np.clip(band, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8))
    weight = np.asarray(band, dtype=np.float32) / 255.0 * strength
    return tint_towards(image, weight, colour)


def trim_to_alpha(image: Image.Image, threshold: int = 0) -> Image.Image:
    """Crop to the bounding box of pixels with alpha above ``threshold``."""
    bbox = alpha_mask(image, threshold).getbbox()
    if bbox is None:
        raise ValueError("image has no visible pixels")
    return image.crop(bbox)


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False, compress_level=9)
