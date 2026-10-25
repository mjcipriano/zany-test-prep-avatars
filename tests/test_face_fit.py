"""face_fit_v1: avatar face rigs, item fits and the sprite clean-up behind them."""

import json
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_face_fit  # noqa: E402
import qa_avatar_visuals  # noqa: E402
from pack_image_ops import ROOT as PACK_ROOT, fit_rect  # noqa: E402,F401
from validate_avatar_catalog import validate_catalog  # noqa: E402

CATALOG_PATH = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"
FIT_DATA = json.loads((ROOT / "data" / "item_fit.json").read_text())
RIGS = json.loads((ROOT / "data" / "face_rigs.json").read_text())


def _catalog():
    return json.loads(CATALOG_PATH.read_text())


def _blob(draw, box):
    draw.ellipse(box, fill=(200, 160, 40, 255))


class FaceRigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = _catalog()
        cls.by_id = {a["id"]: a for a in cls.catalog["assets"]}

    def test_contract_version(self):
        self.assertEqual("face_fit_v1", self.catalog["face_fit_contract_version"])
        self.assertEqual("3.2.0", self.catalog["schema_version"])

    def test_every_avatar_has_its_measured_rig(self):
        for avatar in self.catalog["avatars"]:
            rig = avatar["face_rig"]
            measured = RIGS[avatar["id"]]
            # Landmark points come from MediaPipe; crown/head/hair from the silhouette.
            for name, point in measured["points"].items():
                self.assertEqual(point, rig["points"][name], avatar["id"])
            for name, width in measured["widths"].items():
                self.assertEqual(width, rig["widths"][name], avatar["id"])
            self.assertIn("crown", rig["points"])
            self.assertLessEqual(rig["widths"]["hair"], rig["widths"]["head"])

    def test_heads_really_differ_so_one_box_cannot_fit_all(self):
        eye_ys = [a["face_rig"]["points"]["eyes"]["y"] for a in self.catalog["avatars"]]
        face_ws = [a["face_rig"]["widths"]["face"] for a in self.catalog["avatars"]]
        self.assertGreater(max(eye_ys) - min(eye_ys), 0.05)
        self.assertGreater(max(face_ws) / min(face_ws), 1.2)

    def test_rig_from_landmarks_names_and_orders_points(self):
        import measure_face_rigs

        lm = [(0.5, 0.5)] * 478
        lm = list(lm)
        def put(i, x, y):
            lm[i] = (x, y)
        put(10, 0.5, 0.15); put(105, 0.45, 0.2); put(334, 0.55, 0.2); put(66, 0.45, 0.2); put(296, 0.55, 0.2)
        put(33, 0.40, 0.25); put(133, 0.46, 0.25); put(362, 0.54, 0.25); put(263, 0.60, 0.25)
        put(6, 0.5, 0.26); put(1, 0.5, 0.31); put(2, 0.5, 0.33); put(13, 0.5, 0.36); put(152, 0.5, 0.45)
        put(205, 0.43, 0.32); put(425, 0.57, 0.32); put(234, 0.36, 0.26); put(454, 0.64, 0.26)
        put(93, 0.37, 0.31); put(323, 0.63, 0.31); put(61, 0.46, 0.37); put(291, 0.54, 0.37)
        rig = measure_face_rigs.rig_from_landmarks(lm)
        self.assertEqual(set(build_face_fit.RIG_POINTS) - {"crown"}, set(rig["points"]))
        self.assertAlmostEqual(0.28, rig["widths"]["face"], places=4)
        self.assertAlmostEqual(0.20, rig["widths"]["eyes"], places=4)
        self.assertAlmostEqual(0.33, rig["points"]["ear_l"]["y"], places=4)
        self.assertLess(rig["points"]["ear_l"]["x"], 0.37)  # just outside the contour
        self.assertAlmostEqual(0.25, rig["points"]["eyes"]["y"], places=4)


class ItemFitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = _catalog()
        cls.by_id = {a["id"]: a for a in cls.catalog["assets"]}

    def test_every_face_and_head_item_is_fitted(self):
        for item in self.catalog["items"]:
            fitted = item["category"] in build_face_fit.FIT_CATEGORIES
            self.assertEqual(fitted, "fit" in item, item["id"])

    def test_kind_table_covers_each_base_item_once(self):
        ids = [i for ids in FIT_DATA["items"].values() for i in ids]
        self.assertEqual(len(ids), len(set(ids)))
        for item_id in ids:
            self.assertIn(item_id, self.by_id)
            self.assertNotIn("variant_of", self.by_id[item_id])

    def test_prism_variants_inherit_fit(self):
        variants = [i for i in self.catalog["items"] if "variant_of" in i and "fit" in i]
        self.assertTrue(variants)
        for item in variants:
            self.assertEqual(self.by_id[item["variant_of"]]["fit"], item["fit"], item["id"])

    def test_hoods_headset_and_laurel_render_behind(self):
        behind = {i["fit"]["kind"] for i in self.catalog["items"] if i.get("fit", {}).get("behind")}
        self.assertEqual({"hood", "headphones", "laurel"}, behind)

    def test_fit_rect_maths(self):
        rig = {"points": {"eyes": {"x": 0.5, "y": 0.3}}, "widths": {"eyes": 0.2}}
        item = {
            "fit": {"anchor": "eyes", "sprite_anchor": {"x": 0.5, "y": 0.5}, "width_ref": "eyes", "width": 1.5},
            "sprite_size": {"width": 300, "height": 100},
        }
        left, top, width, height = fit_rect(item, rig, 1.0)
        self.assertAlmostEqual(0.3, width)
        self.assertAlmostEqual(0.1, height)
        self.assertAlmostEqual(0.35, left)
        self.assertAlmostEqual(0.25, top)

    def test_masks_sit_below_the_eyes_on_every_avatar(self):
        masks = [i for i in self.catalog["items"] if i.get("fit", {}).get("kind") in {"mask", "gaiter"}]
        for avatar in self.catalog["avatars"]:
            rig = avatar["face_rig"]
            for mask in masks:
                _, top, _, height = fit_rect(mask, rig, 1.0)
                self.assertGreaterEqual(top, rig["points"]["eyes"]["y"] - 0.01, (mask["id"], avatar["id"]))
                self.assertGreater(top + height, rig["points"]["mouth"]["y"] + 0.02, (mask["id"], avatar["id"]))

    def test_glasses_centre_on_each_avatars_eyes(self):
        glasses = [i for i in self.catalog["items"] if i.get("fit", {}).get("kind") == "glasses"]
        for avatar in self.catalog["avatars"][::7]:
            eyes = avatar["face_rig"]["points"]["eyes"]
            for item in glasses:
                left, top, width, height = fit_rect(item, avatar["face_rig"], 1.0)
                self.assertAlmostEqual(eyes["x"], left + width / 2, delta=0.02)
                self.assertAlmostEqual(eyes["y"], top + height / 2, delta=0.02)

    def test_renamed_items_match_their_art(self):
        for item_id, name in FIT_DATA["renames"].items():
            self.assertEqual(name, self.by_id[item_id]["name"])
        self.assertEqual("Mythic Monocle", self.by_id["item_069_mythic_goggles"]["name"])

    def test_catalog_validates_and_face_fit_qa_is_clean(self):
        self.assertEqual([], validate_catalog(CATALOG_PATH))
        self.assertEqual([], qa_avatar_visuals.face_fit_checks(self.catalog))


class HatFitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = _catalog()
        cls.by_id = {a["id"]: a for a in cls.catalog["assets"]}

    def _avatar(self, avatar_id):
        return self.by_id[avatar_id]

    def test_big_hair_measures_wider_than_short_hair(self):
        short = self._avatar("avatar_basic_001_nova_learner")["face_rig"]["widths"]
        curly = self._avatar("avatar_basic_008_kiki_quest")["face_rig"]["widths"]
        self.assertGreater(curly["hair"], short["hair"] * 1.2)
        self.assertGreater(curly["hair"], curly["face"] * 1.5)

    def test_hats_grow_to_cover_big_hair(self):
        cap = self.by_id["item_001_classic_cap"]
        short = self._avatar("avatar_basic_001_nova_learner")["face_rig"]
        curly = self._avatar("avatar_basic_008_kiki_quest")["face_rig"]
        _, _, w_short, _ = fit_rect(cap, short, 1.0)
        _, _, w_curly, _ = fit_rect(cap, curly, 1.0)
        self.assertGreater(w_curly, w_short * 1.2)
        self.assertGreaterEqual(w_curly, curly["widths"]["hair"])  # covers the hair

    def test_hats_hide_the_hair_above_them(self):
        from pack_image_ops import avatar_clip_top

        cap = self.by_id["item_001_classic_cap"]
        crown = self.by_id["item_030_galaxy_hood"]  # a crown: worn over the hair, no clip
        hood = self.by_id["item_016_calculator_cap"]  # behind the avatar, no clip
        for avatar in self.catalog["avatars"][::9]:
            rig = avatar["face_rig"]
            _, top, _, height = fit_rect(cap, rig, 1.0)
            line = avatar_clip_top([cap], rig, 1.0)
            self.assertGreater(line, top)
            self.assertLess(line, top + height * 0.5)  # never cuts into the face
            self.assertLess(line, rig["points"]["brow"]["y"])
            self.assertEqual(0.0, avatar_clip_top([crown, hood], rig, 1.0))

    def test_headbands_are_front_strips(self):
        bands = [i for i in self.catalog["items"] if i.get("fit", {}).get("kind") == "headband"]
        self.assertEqual(14, len(bands))
        for band in bands:
            image = Image.open(ROOT / band["asset_path"]).convert("RGBA")
            mask = np.asarray(image)[:, :, 3] > build_face_fit.FRONT_STRIP_ALPHA
            for x in range(0, mask.shape[1], 7):
                ys = np.nonzero(mask[:, x])[0]
                if len(ys):  # one band per column (tiny anti-alias gaps aside): no back arc above it
                    self.assertLessEqual(ys[-1] - ys[0] + 1, len(ys) + 6, band["id"])

    def test_front_strip_keeps_only_the_front_band(self):
        image = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, 199, 99), outline=(200, 20, 20, 255), width=12)
        strip = build_face_fit.front_strip(image)
        self.assertLess(strip.height, 60)
        again = build_face_fit.front_strip(strip)
        self.assertEqual(strip.size, again.size)

    def test_built_in_headwear_and_glasses_are_flagged(self):
        flagged = {a["id"]: a.get("built_in_slots") for a in self.catalog["avatars"] if a.get("built_in_slots")}
        self.assertEqual(FIT_DATA["built_in"], flagged)
        self.assertEqual(["headwear"], flagged["avatar_advanced_034_vocab_knight"])  # beanie in the art
        self.assertEqual(["eyewear"], flagged["avatar_advanced_007_algebra_dragon"])  # glasses in the art

    def test_head_metrics_on_a_synthetic_head(self):
        image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((156, 40, 356, 300), fill=(90, 60, 30, 255))  # hair + head silhouette
        rig = {
            "points": {
                "eyes": {"x": 0.5, "y": 0.4},
                "brow": {"x": 0.5, "y": 0.33},
                "forehead": {"x": 0.5, "y": 0.25},
            },
            "widths": {"face": 0.25},
        }
        m = build_face_fit.head_metrics(image, rig)
        self.assertAlmostEqual(40 / 512, m["crown"]["y"], delta=0.01)
        self.assertGreater(m["head"], 0.3)
        self.assertLessEqual(m["hair"], m["head"])


class SpriteCleanupTest(unittest.TestCase):
    def test_detached_thin_line_is_removed(self):
        image = Image.new("RGBA", (200, 120), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 10, 180, 80), fill=(10, 10, 10, 255))
        draw.line((0, 116, 199, 116), fill=(255, 255, 255, 255), width=2)
        cleaned = build_face_fit.remove_stray_lines(image)
        self.assertIsNotNone(cleaned)
        self.assertEqual((20, 10, 181, 81), cleaned.getchannel("A").getbbox())
        self.assertIsNone(build_face_fit.remove_stray_lines(cleaned))

    def test_art_without_lines_is_untouched(self):
        image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((10, 10, 90, 90), fill=(1, 2, 3, 255))
        self.assertIsNone(build_face_fit.remove_stray_lines(image))

    def _pair(self, left_box, right_box, size=(360, 170)):
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        _blob(draw, left_box)
        _blob(draw, right_box)
        return image

    def test_studs_hang_from_their_centres(self):
        image = self._pair((0, 0, 59, 59), (300, 0, 359, 59), size=(360, 60))
        relaid, anchor, span = build_face_fit.fit_earring_pair(image)
        self.assertAlmostEqual(0.5, anchor["y"], delta=0.05)
        self.assertAlmostEqual(0.5, anchor["x"], delta=0.02)
        self.assertLess(relaid.height, 60)  # 60px studs on a 300px span are shrunk to <=14%

    def test_drops_hang_from_their_tops_and_are_shrunk(self):
        image = self._pair((0, 0, 39, 169), (200, 0, 239, 169), size=(240, 170))
        relaid, anchor, span = build_face_fit.fit_earring_pair(image)
        self.assertLess(anchor["y"], 0.3)
        attach_distance = span * relaid.width
        self.assertLessEqual(relaid.height, build_face_fit.EARRING_MAX_H * attach_distance + 2)

    def test_relaying_is_idempotent(self):
        image = self._pair((0, 0, 39, 169), (200, 0, 239, 169), size=(240, 170))
        once, anchor, span = build_face_fit.fit_earring_pair(image)
        twice, anchor2, span2 = build_face_fit.fit_earring_pair(once)
        self.assertEqual(once.size, twice.size)
        self.assertTrue(np.array_equal(np.asarray(once), np.asarray(twice)))
        self.assertEqual(anchor, anchor2)


if __name__ == "__main__":
    unittest.main()
