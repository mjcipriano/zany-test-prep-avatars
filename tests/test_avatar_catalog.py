import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"
SIDE_SLOTS = {"side_left_1", "side_left_2", "side_right_1", "side_right_2"}


class Loadout:
    def __init__(self, avatar_id, equipped=None):
        self.avatar_id = avatar_id
        self.equipped = dict(equipped or {})

    def equip(self, catalog, slot, asset_id):
        avatar = catalog["by_id"][self.avatar_id]
        asset = catalog["by_id"][asset_id]
        if slot not in avatar["compatible_slots"]:
            raise ValueError(f"avatar incompatible with {slot}")
        if slot not in asset["allowed_slots"]:
            raise ValueError(f"asset incompatible with {slot}")
        next_equipped = dict(self.equipped)
        next_equipped[slot] = asset_id
        return Loadout(self.avatar_id, next_equipped)

    def unequip(self, slot):
        next_equipped = dict(self.equipped)
        next_equipped.pop(slot, None)
        return Loadout(self.avatar_id, next_equipped)

    def preview_stack(self, catalog):
        layers = [catalog["by_id"][asset_id] for asset_id in self.equipped.values()]
        layers.append(catalog["by_id"][self.avatar_id])
        return sorted(layers, key=lambda asset: asset["z_index"])


def load_catalog():
    catalog = json.loads(CATALOG_PATH.read_text())
    catalog["by_id"] = {asset["id"]: asset for asset in catalog["assets"]}
    return catalog


class AvatarCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_catalog_loads_with_expected_counts(self):
        self.assertEqual(10, len(self.catalog["avatars"]) - 100)
        self.assertEqual(110, len(self.catalog["avatars"]))
        self.assertEqual(272, len(self.catalog["items"]))
        self.assertGreaterEqual(len(self.catalog["pets"]), 30)

    def test_advertised_worn_slots_are_populated(self):
        categories = {}
        for item in self.catalog["items"]:
            categories[item["category"]] = categories.get(item["category"], 0) + 1
        self.assertEqual(24, categories["background_frame"])
        self.assertEqual(24, categories["jacket_overlay"])
        self.assertEqual(24, categories["ear_accessory"])

    def test_starter_and_advanced_unlock_defaults(self):
        starters = [a for a in self.catalog["avatars"] if a["avatar_type"] == "starter"]
        advanced = [a for a in self.catalog["avatars"] if a["avatar_type"] == "advanced"]
        self.assertTrue(all(a["default_unlocked"] for a in starters))
        self.assertTrue(all(not a["default_unlocked"] for a in advanced))

    def test_equip_and_unequip_asset(self):
        loadout = Loadout("avatar_basic_001_nova_learner")
        loadout = loadout.equip(self.catalog, "headwear", "item_001_classic_cap")
        self.assertEqual("item_001_classic_cap", loadout.equipped["headwear"])
        loadout = loadout.unequip("headwear")
        self.assertNotIn("headwear", loadout.equipped)

    def test_prevents_incompatible_slot(self):
        loadout = Loadout("avatar_basic_001_nova_learner")
        with self.assertRaises(ValueError):
            loadout.equip(self.catalog, "eyewear", "item_001_classic_cap")

    def test_prevents_two_items_in_same_slot_by_replacing(self):
        loadout = Loadout("avatar_basic_001_nova_learner")
        loadout = loadout.equip(self.catalog, "headwear", "item_001_classic_cap")
        loadout = loadout.equip(self.catalog, "headwear", "item_002_streak_beanie")
        self.assertEqual(1, len(loadout.equipped))
        self.assertEqual("item_002_streak_beanie", loadout.equipped["headwear"])

    def test_new_worn_slots_are_equippable(self):
        loadout = Loadout("avatar_basic_001_nova_learner")
        loadout = loadout.equip(self.catalog, "background_frame", "item_201_neon_focus_ring")
        loadout = loadout.equip(self.catalog, "jacket_or_top_overlay", "item_225_black_varsity_jacket")
        loadout = loadout.equip(self.catalog, "ear_accessory", "item_249_silver_studs")
        self.assertEqual("item_201_neon_focus_ring", loadout.equipped["background_frame"])
        self.assertEqual("item_225_black_varsity_jacket", loadout.equipped["jacket_or_top_overlay"])
        self.assertEqual("item_249_silver_studs", loadout.equipped["ear_accessory"])

    def test_allows_pets_and_props_in_side_slots(self):
        loadout = Loadout("avatar_basic_001_nova_learner")
        loadout = loadout.equip(self.catalog, "side_left_1", "pet_fox_study_cap_001")
        loadout = loadout.equip(self.catalog, "side_right_2", "item_177_open_book")
        self.assertEqual("pet_fox_study_cap_001", loadout.equipped["side_left_1"])
        self.assertEqual("item_177_open_book", loadout.equipped["side_right_2"])

    def test_total_unlocked_assets_by_xp(self):
        unlocked = [a for a in self.catalog["assets"] if a.get("default_unlocked") or a["xp_cost"] <= 3000]
        self.assertGreater(len(unlocked), 10)
        self.assertTrue(all(a["xp_cost"] <= 3000 or a.get("default_unlocked") for a in unlocked))

    def test_preview_stack_sorts_without_crashing(self):
        demo = self.catalog["demo_loadouts"][0]
        loadout = Loadout(demo["avatar_id"], demo["equipped"])
        stack = loadout.preview_stack(self.catalog)
        self.assertEqual(len(demo["equipped"]) + 1, len(stack))
        self.assertEqual(sorted(a["z_index"] for a in stack), [a["z_index"] for a in stack])

    def test_side_slot_assets_are_mirrorable(self):
        side_assets = [
            a for a in self.catalog["assets"]
            if a["slot_type"] == "side" or SIDE_SLOTS.intersection(a["allowed_slots"])
        ]
        self.assertTrue(side_assets)
        self.assertTrue(all(a.get("mirrored_supported") for a in side_assets))


if __name__ == "__main__":
    unittest.main()
