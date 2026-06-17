import json
import unittest
from pathlib import Path

from PIL import Image


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
        self.assertEqual("2.1.0", self.catalog["schema_version"])
        self.assertEqual("target_box_v1", self.catalog["placement_contract_version"])
        self.assertEqual(10, len(self.catalog["avatars"]) - 100)
        self.assertEqual(110, len(self.catalog["avatars"]))
        self.assertEqual(272, len(self.catalog["items"]))
        self.assertEqual(90, len(self.catalog["pets"]))
        self.assertEqual(472, len(self.catalog["assets"]))

    def test_advertised_worn_slots_are_populated(self):
        categories = {}
        for item in self.catalog["items"]:
            categories[item["category"]] = categories.get(item["category"], 0) + 1
        self.assertEqual(24, categories["background_frame"])
        self.assertEqual(24, categories["jacket_overlay"])
        self.assertEqual(24, categories["ear_accessory"])

    def test_required_pet_set_is_present(self):
        required_pet_ids = {
            "pet_fox_study_cap_001",
            "pet_hoodie_cat_001",
            "pet_backpack_dog_001",
            "pet_raven_scholar_001",
            "pet_mini_owl_001",
            "pet_cyber_dragon_001",
            "pet_neon_gecko_001",
            "pet_varsity_bulldog_001",
            "pet_calculator_bot_001",
            "pet_nebula_rabbit_001",
            "pet_pixel_ghost_001",
            "pet_book_turtle_001",
            "pet_coffee_raccoon_001",
            "pet_sneaker_penguin_001",
            "pet_cloud_axolotl_001",
            "pet_flame_salamander_001",
            "pet_ice_wolf_pup_001",
            "pet_electric_ferret_001",
            "pet_chess_crow_001",
            "pet_comet_hamster_001",
            "pet_test_prep_tiger_cub_001",
            "pet_origami_crane_001",
            "pet_robot_raven_001",
            "pet_moon_moth_001",
            "pet_hoodie_frog_001",
            "pet_gaming_mouse_001",
            "pet_prism_fox_001",
            "pet_data_sprite_001",
            "pet_lucky_cat_001",
            "pet_golden_griffin_001",
        }
        pet_ids = {pet["id"] for pet in self.catalog["pets"]}
        self.assertTrue(required_pet_ids.issubset(pet_ids))
        self.assertNotIn("pet_midnight_phoenix_001", pet_ids)

    def test_expanded_pet_set_is_present(self):
        expanded_pet_ids = {
            "pet_debate_parrot_001",
            "pet_library_hedgehog_001",
            "pet_hoodie_corgi_001",
            "pet_sleepy_panda_001",
            "pet_note_squirrel_001",
            "pet_campus_sparrow_001",
            "pet_bubble_tea_capybara_001",
            "pet_study_ferret_001",
            "pet_desk_lamp_moth_001",
            "pet_flashcard_crab_001",
            "pet_sneaker_hamster_001",
            "pet_graph_paper_snail_001",
            "pet_algebra_lynx_001",
            "pet_vocabulary_viper_001",
            "pet_eclipse_bat_001",
            "pet_neon_koi_001",
            "pet_campus_fox_001",
            "pet_lab_rat_001",
            "pet_constellation_deer_001",
            "pet_backpack_koala_001",
            "pet_quiz_bee_001",
            "pet_ink_raven_001",
            "pet_moon_jellyfish_001",
            "pet_thunder_chinchilla_001",
            "pet_hologram_wolf_001",
            "pet_chrome_phoenix_chick_001",
            "pet_circuit_turtle_drone_001",
            "pet_asteroid_armadillo_001",
            "pet_rune_otter_001",
            "pet_plasma_kitten_001",
            "pet_cyber_mantis_001",
            "pet_aurora_seal_pup_001",
            "pet_quantum_rabbit_bot_001",
            "pet_crystal_tarantula_001",
            "pet_solar_lion_cub_001",
            "pet_glitch_sprite_owl_001",
            "pet_crown_stag_001",
            "pet_obsidian_dragon_hatchling_001",
            "pet_sapphire_tiger_001",
            "pet_lunar_kitsune_001",
            "pet_royal_peacock_scholar_001",
            "pet_mythic_sphinx_cub_001",
            "pet_radiant_unicorn_foal_001",
            "pet_clockwork_griffin_chick_001",
            "pet_nebula_whale_001",
            "pet_emerald_basilisk_001",
            "pet_starforge_bear_cub_001",
            "pet_phoenix_fox_001",
            "pet_coding_raccoon_001",
            "pet_varsity_otter_001",
            "pet_skateboard_lizard_001",
            "pet_headphones_bat_001",
            "pet_study_alpaca_001",
            "pet_calculator_crab_bot_001",
            "pet_neon_ferret_hacker_001",
            "pet_journal_bunny_001",
            "pet_compass_falcon_001",
            "pet_pixel_panda_001",
            "pet_chemistry_chameleon_001",
            "pet_focus_sloth_001",
        }
        pet_ids = {pet["id"] for pet in self.catalog["pets"]}
        self.assertTrue(expanded_pet_ids.issubset(pet_ids))

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

    def test_every_asset_has_placement_target_inside_canvas(self):
        for asset in self.catalog["assets"]:
            placement = asset["placement"]
            targets = [placement["target"], *placement.get("targets_by_slot", {}).values()]
            for target in targets:
                self.assertGreater(target["w"], 0, asset["id"])
                self.assertGreater(target["h"], 0, asset["id"])
                self.assertGreaterEqual(target["cx"] - target["w"] / 2, 0, asset["id"])
                self.assertLessEqual(target["cx"] + target["w"] / 2, 1, asset["id"])
                self.assertGreaterEqual(target["cy"] - target["h"] / 2, 0, asset["id"])
                self.assertLessEqual(target["cy"] + target["h"] / 2, 1, asset["id"])

    def test_non_avatar_sprites_are_trimmed_and_sized(self):
        for asset in self.catalog["assets"]:
            path = ROOT / asset["asset_path"]
            with Image.open(path) as image:
                image = image.convert("RGBA")
                self.assertEqual(
                    (asset["sprite_size"]["width"], asset["sprite_size"]["height"]),
                    image.size,
                    asset["id"],
                )
                if asset["type"] == "avatar":
                    self.assertEqual((512, 512), image.size, asset["id"])
                    self.assertFalse(asset["trimmed_sprite"], asset["id"])
                else:
                    self.assertTrue(asset["trimmed_sprite"], asset["id"])
                    self.assertEqual(image.getchannel("A").getbbox(), (0, 0, image.width, image.height), asset["id"])

    def test_side_assets_have_targets_for_each_allowed_slot(self):
        for asset in self.catalog["assets"]:
            allowed_side_slots = SIDE_SLOTS.intersection(asset["allowed_slots"])
            if allowed_side_slots:
                self.assertEqual(allowed_side_slots, set(asset["placement"]["targets_by_slot"]), asset["id"])

    def test_side_slot_assets_are_mirrorable(self):
        side_assets = [
            a for a in self.catalog["assets"]
            if a["slot_type"] == "side" or SIDE_SLOTS.intersection(a["allowed_slots"])
        ]
        self.assertTrue(side_assets)
        self.assertTrue(all(a.get("mirrored_supported") for a in side_assets))


if __name__ == "__main__":
    unittest.main()
