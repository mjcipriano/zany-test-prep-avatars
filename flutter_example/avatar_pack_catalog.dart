import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;

enum AvatarSlot {
  headwear,
  eyewear,
  faceAccessory,
  earAccessory,
  neckAccessory,
  chestBadge,
  jacketOrTopOverlay,
  backOrAura,
  backgroundFrame,
  sideLeft1,
  sideLeft2,
  sideRight1,
  sideRight2,
}

extension AvatarSlotJson on AvatarSlot {
  String get id => switch (this) {
        AvatarSlot.headwear => 'headwear',
        AvatarSlot.eyewear => 'eyewear',
        AvatarSlot.faceAccessory => 'face_accessory',
        AvatarSlot.earAccessory => 'ear_accessory',
        AvatarSlot.neckAccessory => 'neck_accessory',
        AvatarSlot.chestBadge => 'chest_badge',
        AvatarSlot.jacketOrTopOverlay => 'jacket_or_top_overlay',
        AvatarSlot.backOrAura => 'back_or_aura',
        AvatarSlot.backgroundFrame => 'background_frame',
        AvatarSlot.sideLeft1 => 'side_left_1',
        AvatarSlot.sideLeft2 => 'side_left_2',
        AvatarSlot.sideRight1 => 'side_right_1',
        AvatarSlot.sideRight2 => 'side_right_2',
      };

  bool get isSideSlot => id.startsWith('side_');

  static AvatarSlot parse(String value) => AvatarSlot.values.firstWhere(
        (slot) => slot.id == value,
        orElse: () => throw ArgumentError('Unknown avatar slot: $value'),
      );
}

class AvatarTargetBox {
  final double cx;
  final double cy;
  final double width;
  final double height;

  const AvatarTargetBox({
    required this.cx,
    required this.cy,
    required this.width,
    required this.height,
  });

  factory AvatarTargetBox.fromJson(Map<String, dynamic> json) => AvatarTargetBox(
        cx: (json['cx'] as num).toDouble(),
        cy: (json['cy'] as num).toDouble(),
        width: (json['w'] as num).toDouble(),
        height: (json['h'] as num).toDouble(),
      );
}

class AvatarPlacement {
  final String anchor;
  final AvatarTargetBox target;
  final Map<String, AvatarTargetBox> targetsBySlot;
  final String fit;
  final String scaleBasis;

  const AvatarPlacement({
    required this.anchor,
    required this.target,
    required this.targetsBySlot,
    required this.fit,
    required this.scaleBasis,
  });

  factory AvatarPlacement.fromJson(Map<String, dynamic> json) => AvatarPlacement(
        anchor: json['anchor'] as String,
        target: AvatarTargetBox.fromJson(Map<String, dynamic>.from(json['target'] as Map)),
        targetsBySlot: {
          for (final entry in Map<String, dynamic>.from(json['targets_by_slot'] ?? const {}).entries)
            entry.key: AvatarTargetBox.fromJson(Map<String, dynamic>.from(entry.value as Map)),
        },
        fit: (json['fit'] ?? 'contain') as String,
        scaleBasis: (json['scale_basis'] ?? 'target_box') as String,
      );

  AvatarTargetBox targetFor(AvatarSlot? slot) {
    if (slot == null) {
      return target;
    }
    return targetsBySlot[slot.id] ?? target;
  }
}

class AvatarCatalog {
  final String packId;
  final String styleVersion;
  final List<AvatarAsset> avatars;
  final List<AvatarItem> items;
  final List<AvatarPet> pets;
  final Map<String, AvatarCatalogAsset> assetsById;
  final List<Map<String, dynamic>> demoLoadouts;

  AvatarCatalog({
    required this.packId,
    required this.styleVersion,
    required this.avatars,
    required this.items,
    required this.pets,
    required this.assetsById,
    required this.demoLoadouts,
  });

  static Future<AvatarCatalog> load({
    String path = 'assets/avatar/manifest/avatar_catalog.json',
  }) async {
    final raw = await rootBundle.loadString(path);
    return AvatarCatalog.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  factory AvatarCatalog.fromJson(Map<String, dynamic> json) {
    final rawAssets = List<Map<String, dynamic>>.from(json['assets'] as List);
    final assets = rawAssets.map(AvatarCatalogAsset.fromJson).toList();
    return AvatarCatalog(
      packId: json['pack_id'] as String,
      styleVersion: json['style_version'] as String,
      avatars: assets.whereType<AvatarAsset>().toList(),
      items: assets.whereType<AvatarItem>().toList(),
      pets: assets.whereType<AvatarPet>().toList(),
      assetsById: {for (final asset in assets) asset.id: asset},
      demoLoadouts: List<Map<String, dynamic>>.from(json['demo_loadouts'] ?? const []),
    );
  }

  AvatarAsset avatar(String id) => assetsById[id] as AvatarAsset;

  AvatarCatalogAsset asset(String id) {
    final asset = assetsById[id];
    if (asset == null) {
      throw ArgumentError('Unknown avatar catalog asset: $id');
    }
    return asset;
  }

  EquippedAvatarLoadout demoLoadout(String id) {
    final raw = demoLoadouts.firstWhere((loadout) => loadout['id'] == id);
    return EquippedAvatarLoadout.fromJson(raw);
  }

  List<AvatarCatalogAsset> unlockedAssetsForXp(int xp) =>
      assetsById.values.where((asset) => asset.defaultUnlocked || asset.xpCost <= xp).toList();
}

sealed class AvatarCatalogAsset {
  final String id;
  final String name;
  final String type;
  final String category;
  final String slotType;
  final List<String> allowedSlots;
  final String rarity;
  final int xpCost;
  final String unlockCondition;
  final String assetPath;
  final String previewAssetPath;
  final Map<String, int> canvasSize;
  final Map<String, num> anchor;
  final double scale;
  final int zIndex;
  final List<String> tags;
  final String styleVersion;
  final bool defaultUnlocked;
  final Map<String, int> spriteSize;
  final bool trimmedSprite;
  final Map<String, int>? sourceCanvasSize;
  final AvatarPlacement placement;

  AvatarCatalogAsset({
    required this.id,
    required this.name,
    required this.type,
    required this.category,
    required this.slotType,
    required this.allowedSlots,
    required this.rarity,
    required this.xpCost,
    required this.unlockCondition,
    required this.assetPath,
    required this.previewAssetPath,
    required this.canvasSize,
    required this.anchor,
    required this.scale,
    required this.zIndex,
    required this.tags,
    required this.styleVersion,
    required this.spriteSize,
    required this.trimmedSprite,
    required this.sourceCanvasSize,
    required this.placement,
    this.defaultUnlocked = false,
  });

  bool canEquipIn(AvatarSlot slot) => allowedSlots.contains(slot.id);

  static AvatarCatalogAsset fromJson(Map<String, dynamic> json) {
    return switch (json['type'] as String) {
      'avatar' => AvatarAsset.fromJson(json),
      'pet' => AvatarPet.fromJson(json),
      'item' || 'frame' || 'aura' || 'background' => AvatarItem.fromJson(json),
      final type => throw ArgumentError('Unsupported avatar catalog asset type: $type'),
    };
  }
}

class AvatarAsset extends AvatarCatalogAsset {
  final String avatarType;
  final String bodyFrame;
  final List<String> compatibleSlots;

  AvatarAsset({
    required super.id,
    required super.name,
    required super.type,
    required super.category,
    required super.slotType,
    required super.allowedSlots,
    required super.rarity,
    required super.xpCost,
    required super.unlockCondition,
    required super.assetPath,
    required super.previewAssetPath,
    required super.canvasSize,
    required super.anchor,
    required super.scale,
    required super.zIndex,
    required super.tags,
    required super.styleVersion,
    required super.spriteSize,
    required super.trimmedSprite,
    required super.sourceCanvasSize,
    required super.placement,
    required super.defaultUnlocked,
    required this.avatarType,
    required this.bodyFrame,
    required this.compatibleSlots,
  });

  factory AvatarAsset.fromJson(Map<String, dynamic> json) => AvatarAsset(
        id: json['id'] as String,
        name: json['name'] as String,
        type: json['type'] as String,
        category: json['category'] as String,
        slotType: json['slot_type'] as String,
        allowedSlots: List<String>.from(json['allowed_slots'] as List),
        rarity: json['rarity'] as String,
        xpCost: json['xp_cost'] as int,
        unlockCondition: json['unlock_condition'] as String,
        assetPath: json['asset_path'] as String,
        previewAssetPath: (json['preview_asset_path'] ?? json['asset_path']) as String,
        canvasSize: Map<String, int>.from(json['canvas_size'] as Map),
        anchor: Map<String, num>.from(json['anchor'] as Map),
        scale: (json['scale'] as num).toDouble(),
        zIndex: json['z_index'] as int,
        tags: List<String>.from(json['tags'] as List),
        styleVersion: json['style_version'] as String,
        spriteSize: Map<String, int>.from((json['sprite_size'] ?? json['canvas_size']) as Map),
        trimmedSprite: json['trimmed_sprite'] as bool? ?? false,
        sourceCanvasSize: json['source_canvas_size'] == null
            ? null
            : Map<String, int>.from(json['source_canvas_size'] as Map),
        placement: AvatarPlacement.fromJson(Map<String, dynamic>.from(json['placement'] as Map)),
        defaultUnlocked: json['default_unlocked'] as bool,
        avatarType: json['avatar_type'] as String,
        bodyFrame: json['body_frame'] as String,
        compatibleSlots: List<String>.from(json['compatible_slots'] as List),
      );
}

class AvatarItem extends AvatarCatalogAsset {
  final String itemType;
  final bool overlaysAvatar;
  final bool mirrorWhenSide;
  final bool mirroredSupported;

  AvatarItem({
    required super.id,
    required super.name,
    required super.type,
    required super.category,
    required super.slotType,
    required super.allowedSlots,
    required super.rarity,
    required super.xpCost,
    required super.unlockCondition,
    required super.assetPath,
    required super.previewAssetPath,
    required super.canvasSize,
    required super.anchor,
    required super.scale,
    required super.zIndex,
    required super.tags,
    required super.styleVersion,
    required super.spriteSize,
    required super.trimmedSprite,
    required super.sourceCanvasSize,
    required super.placement,
    required this.itemType,
    required this.overlaysAvatar,
    required this.mirrorWhenSide,
    required this.mirroredSupported,
  });

  factory AvatarItem.fromJson(Map<String, dynamic> json) => AvatarItem(
        id: json['id'] as String,
        name: json['name'] as String,
        type: json['type'] as String,
        category: json['category'] as String,
        slotType: json['slot_type'] as String,
        allowedSlots: List<String>.from(json['allowed_slots'] as List),
        rarity: json['rarity'] as String,
        xpCost: json['xp_cost'] as int,
        unlockCondition: json['unlock_condition'] as String,
        assetPath: json['asset_path'] as String,
        previewAssetPath: (json['preview_asset_path'] ?? json['asset_path']) as String,
        canvasSize: Map<String, int>.from(json['canvas_size'] as Map),
        anchor: Map<String, num>.from(json['anchor'] as Map),
        scale: (json['scale'] as num).toDouble(),
        zIndex: json['z_index'] as int,
        tags: List<String>.from(json['tags'] as List),
        styleVersion: json['style_version'] as String,
        spriteSize: Map<String, int>.from((json['sprite_size'] ?? json['canvas_size']) as Map),
        trimmedSprite: json['trimmed_sprite'] as bool? ?? false,
        sourceCanvasSize: json['source_canvas_size'] == null
            ? null
            : Map<String, int>.from(json['source_canvas_size'] as Map),
        placement: AvatarPlacement.fromJson(Map<String, dynamic>.from(json['placement'] as Map)),
        itemType: json['item_type'] as String,
        overlaysAvatar: json['overlays_avatar'] as bool,
        mirrorWhenSide: json['mirror_when_side'] as bool,
        mirroredSupported: json['mirrored_supported'] as bool,
      );
}

class AvatarPet extends AvatarCatalogAsset {
  final String petSpecies;
  final String personality;
  final String animationHint;
  final bool mirroredSupported;

  AvatarPet({
    required super.id,
    required super.name,
    required super.type,
    required super.category,
    required super.slotType,
    required super.allowedSlots,
    required super.rarity,
    required super.xpCost,
    required super.unlockCondition,
    required super.assetPath,
    required super.previewAssetPath,
    required super.canvasSize,
    required super.anchor,
    required super.scale,
    required super.zIndex,
    required super.tags,
    required super.styleVersion,
    required super.spriteSize,
    required super.trimmedSprite,
    required super.sourceCanvasSize,
    required super.placement,
    required this.petSpecies,
    required this.personality,
    required this.animationHint,
    required this.mirroredSupported,
  });

  factory AvatarPet.fromJson(Map<String, dynamic> json) => AvatarPet(
        id: json['id'] as String,
        name: json['name'] as String,
        type: json['type'] as String,
        category: json['category'] as String,
        slotType: json['slot_type'] as String,
        allowedSlots: List<String>.from(json['allowed_slots'] as List),
        rarity: json['rarity'] as String,
        xpCost: json['xp_cost'] as int,
        unlockCondition: json['unlock_condition'] as String,
        assetPath: json['asset_path'] as String,
        previewAssetPath: (json['preview_asset_path'] ?? json['asset_path']) as String,
        canvasSize: Map<String, int>.from(json['canvas_size'] as Map),
        anchor: Map<String, num>.from(json['anchor'] as Map),
        scale: (json['scale'] as num).toDouble(),
        zIndex: json['z_index'] as int,
        tags: List<String>.from(json['tags'] as List),
        styleVersion: json['style_version'] as String,
        spriteSize: Map<String, int>.from((json['sprite_size'] ?? json['canvas_size']) as Map),
        trimmedSprite: json['trimmed_sprite'] as bool? ?? false,
        sourceCanvasSize: json['source_canvas_size'] == null
            ? null
            : Map<String, int>.from(json['source_canvas_size'] as Map),
        placement: AvatarPlacement.fromJson(Map<String, dynamic>.from(json['placement'] as Map)),
        petSpecies: json['pet_species'] as String,
        personality: json['personality'] as String,
        animationHint: json['animation_hint'] as String,
        mirroredSupported: json['mirrored_supported'] as bool,
      );
}

class EquippedAvatarLoadout {
  final String avatarId;
  final Map<AvatarSlot, String> equipped;

  const EquippedAvatarLoadout({
    required this.avatarId,
    required this.equipped,
  });

  factory EquippedAvatarLoadout.fromJson(Map<String, dynamic> json) {
    final rawEquipped = Map<String, dynamic>.from(json['equipped'] as Map);
    return EquippedAvatarLoadout(
      avatarId: json['avatar_id'] as String,
      equipped: {
        for (final entry in rawEquipped.entries)
          AvatarSlotJson.parse(entry.key): entry.value as String,
      },
    );
  }

  EquippedAvatarLoadout equip(AvatarCatalog catalog, AvatarSlot slot, String assetId) {
    final asset = catalog.asset(assetId);
    final avatar = catalog.avatar(avatarId);
    if (!avatar.compatibleSlots.contains(slot.id)) {
      throw ArgumentError('Avatar $avatarId does not support slot ${slot.id}');
    }
    if (!asset.canEquipIn(slot)) {
      throw ArgumentError('Asset $assetId cannot equip in slot ${slot.id}');
    }
    return EquippedAvatarLoadout(
      avatarId: avatarId,
      equipped: {...equipped, slot: assetId},
    );
  }

  EquippedAvatarLoadout unequip(AvatarSlot slot) {
    return EquippedAvatarLoadout(
      avatarId: avatarId,
      equipped: {...equipped}..remove(slot),
    );
  }

  List<AvatarCatalogAsset> previewStack(AvatarCatalog catalog) {
    final avatar = catalog.avatar(avatarId);
    final layers = <AvatarCatalogAsset>[
      for (final assetId in equipped.values) catalog.asset(assetId),
      avatar,
    ];
    layers.sort((a, b) => a.zIndex.compareTo(b.zIndex));
    return layers;
  }
}

typedef AvatarPackCatalog = AvatarCatalog;
typedef AvatarDef = AvatarAsset;
typedef ItemDef = AvatarItem;
