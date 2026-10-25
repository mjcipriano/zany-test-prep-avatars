#!/usr/bin/env python3
"""Derive the Flutter compatibility manifests from the runtime catalog.

Writes ``manifest/flutter_avatar_catalog.json`` (camelCase header plus the flattened
``avatars`` / ``items`` / ``pets`` lists, identical to the catalog entries) and
``manifest/flutter_pubspec_snippet.yaml`` (every asset folder the catalog references,
in catalog order, plus the manifest files). Run it after any build script that changes
``assets/avatar/manifest/avatar_catalog.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pack_image_ops import ROOT, load_catalog  # noqa: E402


FLUTTER_CATALOG_PATH = ROOT / "manifest" / "flutter_avatar_catalog.json"
PUBSPEC_SNIPPET_PATH = ROOT / "manifest" / "flutter_pubspec_snippet.yaml"
MANIFEST_ASSETS = (
    "assets/avatar/manifest/avatar_catalog.json",
    "assets/avatar/manifest/avatar_catalog.schema.json",
    "assets/avatar/manifest/sprite_atlas.json",
    "manifest/flutter_avatar_catalog.json",
)


KNOWN_FOLDERS = (
    "assets/avatar/avatars/starter/",
    "assets/avatar/avatars/advanced/",
    "assets/avatar/items/headwear/",
    "assets/avatar/items/eyewear/",
    "assets/avatar/items/face_accessory/",
    "assets/avatar/items/ear_accessory/",
    "assets/avatar/items/neck_accessory/",
    "assets/avatar/items/chest_badge/",
    "assets/avatar/items/jacket_overlay/",
    "assets/avatar/items/back_aura/",
    "assets/avatar/items/background_frame/",
    "assets/avatar/items/floating_props/",
    "assets/avatar/pets/common/",
    "assets/avatar/pets/uncommon/",
    "assets/avatar/pets/rare/",
    "assets/avatar/pets/epic/",
    "assets/avatar/pets/legendary/",
    "assets/avatar/spritesheets/",
)


def asset_folders(catalog: dict) -> list[str]:
    """Known folders in their documented order, plus any new folder the catalog references."""
    folders = list(KNOWN_FOLDERS)
    for asset in catalog["assets"]:
        folder = Path(asset["asset_path"]).parent.as_posix() + "/"
        if folder not in folders:
            folders.insert(len(folders) - 1, folder)
    return folders


def build_flutter_catalog(catalog: dict) -> dict:
    return {
        "schemaVersion": catalog["schema_version"],
        "packId": catalog["pack_id"],
        "catalogPath": "assets/avatar/manifest/avatar_catalog.json",
        "composition": catalog["slots"],
        "avatars": catalog["avatars"],
        "items": catalog["items"],
        "pets": catalog["pets"],
        "placementContractVersion": catalog["placement_contract_version"],
        "evolutionContractVersion": catalog.get("evolution_contract_version"),
        "faceFitContractVersion": catalog.get("face_fit_contract_version"),
        "rig": catalog["rig"],
    }


def build_pubspec_snippet(catalog: dict) -> str:
    lines = ["# Add this to pubspec.yaml under flutter/assets:", "flutter:", "  assets:"]
    lines.extend(f"    - {folder}" for folder in asset_folders(catalog))
    lines.extend(f"    - {path}" for path in MANIFEST_ASSETS)
    return "\n".join(lines) + "\n"


def main() -> int:
    catalog = load_catalog()
    FLUTTER_CATALOG_PATH.write_text(json.dumps(build_flutter_catalog(catalog), indent=2) + "\n")
    PUBSPEC_SNIPPET_PATH.write_text(build_pubspec_snippet(catalog))
    print(
        f"Wrote {FLUTTER_CATALOG_PATH.relative_to(ROOT)} "
        f"({len(catalog['avatars'])} avatars, {len(catalog['items'])} items, {len(catalog['pets'])} pets) "
        f"and {PUBSPEC_SNIPPET_PATH.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
