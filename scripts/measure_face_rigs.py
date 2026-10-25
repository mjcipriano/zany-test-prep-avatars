#!/usr/bin/env python3
"""Measure a face rig for every avatar and write ``data/face_rigs.json``.

The avatars share a waist-up framing, but each one's head sits at its own height
and size, so a single target box per slot puts masks over eyes and earrings on
cheeks. This script runs MediaPipe's face landmarker over every avatar PNG and
records a handful of named points (eyes, brow, nose, mouth, chin, cheeks, ears)
plus reference widths, all normalised to the 512 canvas. ``build_face_fit.py``
copies the rigs into the catalog as each avatar's ``face_rig``.

MediaPipe is only needed to re-measure (new or redrawn avatars); the measured
rigs are committed, so CI and the build scripts never import it::

    python3 -m venv .venv && .venv/bin/pip install mediapipe pillow numpy
    curl -LO https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
    .venv/bin/python scripts/measure_face_rigs.py --model face_landmarker.task
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pack_image_ops import ROOT, load_catalog  # noqa: E402

RIGS_PATH = ROOT / "data" / "face_rigs.json"

# MediaPipe face-mesh landmark indices (person's right = viewer's left = "_l").
EYE_L = (33, 133)
EYE_R = (362, 263)
BROW = (105, 334, 66, 296)
FOREHEAD = 10
NOSE_BRIDGE = 6
NOSE_TIP = 1
SUBNASALE = 2
UPPER_LIP = 13
CHIN = 152
CHEEK_L, CHEEK_R = 205, 425
CONTOUR_L, CONTOUR_R = 234, 454  # face edge at the eye line
JAW_L, JAW_R = 93, 323  # face edge at the nose line
MOUTH_L, MOUTH_R = 61, 291
EAR_OUTSET = 0.05  # ears sit just outside the face contour, as a share of face width


def _mean(lm, *idx):
    return (sum(lm[i][0] for i in idx) / len(idx), sum(lm[i][1] for i in idx) / len(idx))


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def rig_from_landmarks(lm: list[tuple[float, float]]) -> dict:
    """Named rig points and widths from 478 normalised (x, y) face-mesh landmarks."""
    face_w = lm[CONTOUR_R][0] - lm[CONTOUR_L][0]
    eye_l, eye_r = _mean(lm, *EYE_L), _mean(lm, *EYE_R)
    cheek_l, cheek_r = _mean(lm, CHEEK_L), _mean(lm, CHEEK_R)
    lobe_y = lm[SUBNASALE][1]
    ear_l = (lm[JAW_L][0] - EAR_OUTSET * face_w, lobe_y)
    ear_r = (lm[JAW_R][0] + EAR_OUTSET * face_w, lobe_y)
    points = {
        "eye_l": eye_l,
        "eye_r": eye_r,
        "eyes": _mid(eye_l, eye_r),
        "brow": _mean(lm, *BROW),
        "forehead": _mean(lm, FOREHEAD),
        "nose_bridge": _mean(lm, NOSE_BRIDGE),
        "nose": _mean(lm, NOSE_TIP),
        "under_nose": _mid(_mean(lm, SUBNASALE), _mean(lm, UPPER_LIP)),
        "mouth": _mean(lm, UPPER_LIP),
        "chin": _mean(lm, CHIN),
        "cheek_l": cheek_l,
        "cheek_r": cheek_r,
        "cheeks": _mid(cheek_l, cheek_r),
        "face_l": _mean(lm, CONTOUR_L),
        "face_r": _mean(lm, CONTOUR_R),
        "ear_l": ear_l,
        "ear_r": ear_r,
        "ears": _mid(ear_l, ear_r),
    }
    widths = {
        "face": face_w,
        "eyes": lm[EYE_R[1]][0] - lm[EYE_L[0]][0],
        "mouth": lm[MOUTH_R][0] - lm[MOUTH_L][0],
        "ears": ear_r[0] - ear_l[0],
    }
    return {
        "points": {k: {"x": round(x, 4), "y": round(y, 4)} for k, (x, y) in points.items()},
        "widths": {k: round(v, 4) for k, v in widths.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", required=True, help="Path to face_landmarker.task")
    args = parser.parse_args()

    import mediapipe as mp  # noqa: PLC0415 - optional, re-measure only
    import numpy as np  # noqa: PLC0415
    from mediapipe.tasks import python as mp_tasks  # noqa: PLC0415
    from mediapipe.tasks.python import vision  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    options = vision.FaceLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=args.model),
        num_faces=1,
        min_face_detection_confidence=0.2,
        min_face_presence_confidence=0.2,
    )
    detector = vision.FaceLandmarker.create_from_options(options)
    rigs: dict[str, dict] = {}
    missing: list[str] = []
    for avatar in load_catalog()["avatars"]:
        image = Image.open(ROOT / avatar["asset_path"]).convert("RGBA")
        flat = Image.new("RGBA", image.size, (255, 255, 255, 255))
        flat.alpha_composite(image)
        pixels = np.ascontiguousarray(np.asarray(flat.convert("RGB").resize((1024, 1024))))
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels))
        if not result.face_landmarks:
            missing.append(avatar["id"])
            continue
        rigs[avatar["id"]] = rig_from_landmarks([(p.x, p.y) for p in result.face_landmarks[0]])
    detector.close()
    RIGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RIGS_PATH.write_text(json.dumps(rigs, indent=1, sort_keys=True) + "\n")
    print(f"Wrote {len(rigs)} face rigs to {RIGS_PATH.relative_to(ROOT)}")
    if missing:
        print("No face found for: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
