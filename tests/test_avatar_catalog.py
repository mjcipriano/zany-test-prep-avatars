import json
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.json"
SCHEMA_PATH = ROOT / "assets" / "avatar" / "manifest" / "avatar_catalog.schema.json"
SIDE_SLOTS = {"side_left_1", "side_left_2", "side_right_1", "side_right_2"}

sys.path.insert(0, str(ROOT / "scripts"))

import qa_avatar_visuals  # noqa: E402
from validate_avatar_catalog import RARITY_COSTS, validate_catalog  # noqa: E402

EXPECTED_AVATARS = 110
EXPECTED_BASE_ITEMS = 272
EXPECTED_PRISM_ITEMS = 104
EXPECTED_ITEMS = EXPECTED_BASE_ITEMS + EXPECTED_PRISM_ITEMS
EXPECTED_PET_LINES = 90
EXPECTED_PETS = EXPECTED_PET_LINES * 3
EXPECTED_ASSETS = EXPECTED_AVATARS + EXPECTED_ITEMS + EXPECTED_PETS
RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]


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


def alpha_of(asset):
    with Image.open(ROOT / asset["asset_path"]) as image:
        return np.asarray(image.convert("RGBA").getchannel("A"))


class AvatarCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.pets = cls.catalog["pets"]
        cls.base_pets = [p for p in cls.pets if p["evolution"]["stage"] == 1]
        cls.evolved_pets = [p for p in cls.pets if p["evolution"]["stage"] != 1]
        cls.prism_items = [i for i in cls.catalog["items"] if "variant_of" in i]

    # ------------------------------------------------------------------ header / counts

    def test_catalog_loads_with_expected_counts(self):
        self.assertEqual("3.0.0", self.catalog["schema_version"])
        self.assertEqual("target_box_v1", self.catalog["placement_contract_version"])
        self.assertEqual("pet_evolution_v1", self.catalog["evolution_contract_version"])
        self.assertEqual("zany_sat_avatar_pack_v2", self.catalog["pack_id"])
        self.assertEqual(10, len([a for a in self.catalog["avatars"] if a["avatar_type"] == "starter"]))
        self.assertEqual(EXPECTED_AVATARS, len(self.catalog["avatars"]))
        self.assertEqual(EXPECTED_ITEMS, len(self.catalog["items"]))
        self.assertEqual(EXPECTED_PRISM_ITEMS, len(self.prism_items))
        self.assertEqual(EXPECTED_PETS, len(self.catalog["pets"]))
        self.assertEqual(EXPECTED_PET_LINES, len(self.base_pets))
        self.assertEqual(EXPECTED_ASSETS, len(self.catalog["assets"]))

    def test_flattened_lists_match_assets(self):
        flattened = [*self.catalog["avatars"], *self.catalog["items"], *self.catalog["pets"]]
        self.assertEqual([a["id"] for a in flattened], [a["id"] for a in self.catalog["assets"]])
        self.assertEqual(len({a["id"] for a in self.catalog["assets"]}), len(self.catalog["assets"]))

    def test_catalog_matches_json_schema(self):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - optional dependency
            self.skipTest("jsonschema not installed")
        schema = json.loads(SCHEMA_PATH.read_text())
        catalog = json.loads(CATALOG_PATH.read_text())
        jsonschema.validate(catalog, schema)

    def test_validator_passes(self):
        self.assertEqual([], validate_catalog(CATALOG_PATH))

    def test_flutter_manifest_is_derived_from_catalog(self):
        flutter = json.loads((ROOT / "manifest" / "flutter_avatar_catalog.json").read_text())
        self.assertEqual(self.catalog["schema_version"], flutter["schemaVersion"])
        self.assertEqual(self.catalog["evolution_contract_version"], flutter["evolutionContractVersion"])
        self.assertEqual(self.catalog["items"], flutter["items"])
        self.assertEqual(self.catalog["pets"], flutter["pets"])
        self.assertEqual(self.catalog["avatars"], flutter["avatars"])

    def test_advertised_worn_slots_are_populated(self):
        categories = {}
        for item in self.catalog["items"]:
            if "variant_of" in item:
                continue
            categories[item["category"]] = categories.get(item["category"], 0) + 1
        self.assertEqual(24, categories["background_frame"])
        self.assertEqual(24, categories["jacket_overlay"])
        self.assertEqual(24, categories["ear_accessory"])

    def test_floating_tag_only_on_hovering_art(self):
        # Despite their ids, item_007_halo_ring and item_027_orbit_headband are
        # drawn as a bucket hat and a beanie, so no current headwear hovers.
        for item in self.catalog["items"]:
            self.assertNotIn("floating", item["tags"], item["id"])
        for item in self.prism_items:
            base = self.catalog["by_id"][item["variant_of"]]
            self.assertEqual("floating" in base["tags"], "floating" in item["tags"], item["id"])

    # ------------------------------------------------------------------ pets

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

    def test_every_pet_line_has_three_stages_in_order(self):
        by_id = self.catalog["by_id"]
        ids = [pet["id"] for pet in self.pets]
        for base in self.base_pets:
            line = base["evolution"]["line_id"]
            self.assertEqual(f"{line}_001", base["id"])
            self.assertEqual(f"{line}_002", base["evolution"]["next_id"])
            shiny = by_id[f"{line}_002"]
            radiant = by_id[f"{line}_003"]
            self.assertEqual(f"{line}_003", shiny["evolution"]["next_id"])
            self.assertIsNone(radiant["evolution"]["next_id"])
            # pets list keeps base, shiny, radiant adjacent and in stage order
            index = ids.index(base["id"])
            self.assertEqual([base["id"], shiny["id"], radiant["id"]], ids[index : index + 3])
            for stage, pet, name, level in ((1, base, "Base", 1), (2, shiny, "Shiny", 5), (3, radiant, "Radiant", 10)):
                self.assertEqual(
                    {
                        "line_id": line,
                        "stage": stage,
                        "stage_name": name,
                        "base_id": base["id"],
                        "next_id": pet["evolution"]["next_id"],
                        "requires_level": level,
                    },
                    pet["evolution"],
                    pet["id"],
                )

    def test_evolved_pets_inherit_base_metadata(self):
        by_id = self.catalog["by_id"]
        for pet in self.evolved_pets:
            base = by_id[pet["evolution"]["base_id"]]
            stage = pet["evolution"]["stage"]
            self.assertEqual(0, pet["xp_cost"], pet["id"])
            self.assertFalse(pet["default_unlocked"], pet["id"])
            self.assertEqual(f"evolve:{base['id']}:level:{pet['evolution']['requires_level']}", pet["unlock_condition"])
            self.assertEqual(f"{base['name']} ({pet['evolution']['stage_name']})", pet["name"])
            self.assertIn("evolved", pet["tags"])
            self.assertIn(f"stage_{stage}", pet["tags"])
            for field in ("rarity", "placement", "z_index", "allowed_slots", "pet_species", "category", "slot_type", "mirrored_supported"):
                self.assertEqual(base[field], pet[field], f"{pet['id']}.{field}")
            self.assertEqual(Path(base["asset_path"]).parent, Path(pet["asset_path"]).parent, pet["id"])
        for pet in self.base_pets:
            self.assertNotIn("evolved", pet["tags"])
            lo, hi = RARITY_COSTS[pet["rarity"]]
            self.assertTrue(lo <= pet["xp_cost"] <= hi, pet["id"])

    def test_shiny_sprites_keep_base_alpha_and_radiant_sprites_add_bounded_glow(self):
        by_id = self.catalog["by_id"]
        for pet in self.evolved_pets:
            base = by_id[pet["evolution"]["base_id"]]
            base_alpha = alpha_of(base)
            evolved_alpha = alpha_of(pet)
            if pet["evolution"]["stage"] == 2:
                self.assertEqual(base["sprite_size"], pet["sprite_size"], pet["id"])
                visible = base_alpha > 0
                self.assertTrue(np.array_equal(base_alpha[visible], evolved_alpha[visible]), pet["id"])
            else:
                pad_w = pet["sprite_size"]["width"] - base["sprite_size"]["width"]
                pad_h = pet["sprite_size"]["height"] - base["sprite_size"]["height"]
                self.assertGreaterEqual(pad_w, 0, pet["id"])
                self.assertGreaterEqual(pad_h, 0, pet["id"])
                self.assertLessEqual(pad_w, round(0.24 * base["sprite_size"]["width"]) + 2, pet["id"])
                self.assertLessEqual(pad_h, round(0.24 * base["sprite_size"]["height"]) + 2, pet["id"])
                self.assertGreaterEqual(int((evolved_alpha == 255).sum()), int((base_alpha == 255).sum()), pet["id"])

    # ------------------------------------------------------------------ prism variants

    def test_variant_of_resolves_and_copies_base_geometry(self):
        by_id = self.catalog["by_id"]
        for item in self.prism_items:
            base = by_id[item["variant_of"]]
            self.assertEqual("item", base["type"], item["id"])
            self.assertNotIn("variant_of", base, item["id"])
            self.assertEqual(f"{base['name']} (Prism)", item["name"])
            self.assertIn("prism", item["tags"])
            self.assertIn("variant", item["tags"])
            self.assertFalse(item["default_unlocked"])
            for field in ("placement", "z_index", "allowed_slots", "sprite_size", "category", "slot_type", "anchor"):
                self.assertEqual(base[field], item[field], f"{item['id']}.{field}")
            self.assertTrue(np.array_equal(alpha_of(base), alpha_of(item)), item["id"])

    def test_prism_ids_are_consecutive_from_301_in_catalog_order(self):
        numbers = [int(item["id"].split("_")[1]) for item in self.prism_items]
        self.assertEqual(list(range(301, 301 + len(self.prism_items))), numbers)
        self.assertTrue(all(item["id"].endswith("_prism") for item in self.prism_items))
        base_ids = [item["variant_of"] for item in self.prism_items]
        catalog_order = [item["id"] for item in self.catalog["items"] if item["id"] in set(base_ids)]
        self.assertEqual(catalog_order, base_ids)

    def test_prism_rarity_bump_and_cost_ranges(self):
        by_id = self.catalog["by_id"]
        bump = {"rare": "epic", "epic": "legendary", "legendary": "legendary"}
        for item in self.prism_items:
            base = by_id[item["variant_of"]]
            self.assertIn(base["rarity"], bump, item["id"])
            self.assertEqual(bump[base["rarity"]], item["rarity"], item["id"])
            self.assertNotIn(base["category"], {"jacket_overlay"}, item["id"])
            lo, hi = RARITY_COSTS[item["rarity"]]
            expected = max(lo, min(hi, int(round(base["xp_cost"] * 1.5 / 50) * 50)))
            self.assertEqual(expected, item["xp_cost"], item["id"])
            self.assertTrue(lo <= item["xp_cost"] <= hi, item["id"])
            self.assertEqual(f"spend_xp:{item['xp_cost']}", item["unlock_condition"])

    # ------------------------------------------------------------------ geometry QA

    def test_overlap_pass_has_no_warnings(self):
        self.assertEqual([], qa_avatar_visuals.geometry_checks(self.catalog))

    def test_contain_fit_matches_renderer_rule(self):
        rect = qa_avatar_visuals.contain_fit({"width": 200, "height": 100}, {"cx": 0.5, "cy": 0.5, "w": 0.4, "h": 0.4})
        self.assertAlmostEqual(0.3, rect[0])
        self.assertAlmostEqual(0.4, rect[1])
        self.assertAlmostEqual(0.7, rect[2])
        self.assertAlmostEqual(0.6, rect[3])

    def test_overlap_pass_flags_a_side_sprite_over_the_face(self):
        broken = json.loads(json.dumps({k: v for k, v in self.catalog.items() if k != "by_id"}))
        pet = next(a for a in broken["assets"] if a["id"] == "pet_fox_study_cap_001")
        pet["placement"]["targets_by_slot"]["side_left_1"]["cx"] = 0.45
        warnings = qa_avatar_visuals.geometry_checks(broken)
        self.assertTrue(any("intersects rig face region" in w for w in warnings), warnings)

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

    # ------------------------------------------------------------------ loadouts

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

    def test_evolved_pets_and_prism_items_are_equippable(self):
        loadout = Loadout("avatar_basic_001_nova_learner")
        loadout = loadout.equip(self.catalog, "side_left_1", "pet_fox_study_cap_003")
        loadout = loadout.equip(self.catalog, "side_right_1", "pet_fox_study_cap_002")
        loadout = loadout.equip(self.catalog, "headwear", "item_301_classic_cap_prism")
        stack = loadout.preview_stack(self.catalog)
        self.assertEqual(4, len(stack))
        self.assertEqual(sorted(a["z_index"] for a in stack), [a["z_index"] for a in stack])

    def test_total_unlocked_assets_by_xp(self):
        unlocked = [a for a in self.catalog["assets"] if a.get("default_unlocked") or a["xp_cost"] <= 3000]
        self.assertGreater(len(unlocked), 10)
        self.assertTrue(all(a["xp_cost"] <= 3000 or a.get("default_unlocked") for a in unlocked))

    def test_preview_stack_sorts_without_crashing(self):
        for demo in self.catalog["demo_loadouts"]:
            loadout = Loadout(demo["avatar_id"], demo["equipped"])
            stack = loadout.preview_stack(self.catalog)
            self.assertEqual(len(demo["equipped"]) + 1, len(stack))
            self.assertEqual(sorted(a["z_index"] for a in stack), [a["z_index"] for a in stack])


if __name__ == "__main__":
    unittest.main()
