import 'package:flutter/widgets.dart';
import 'avatar_pack_catalog.dart';

class AvatarPreview extends StatelessWidget {
  final AvatarCatalog catalog;
  final EquippedAvatarLoadout loadout;
  final double size;

  const AvatarPreview({
    super.key,
    required this.catalog,
    required this.loadout,
    this.size = 96,
  });

  @override
  Widget build(BuildContext context) {
    final avatar = catalog.avatar(loadout.avatarId);
    final layers = <_PreviewLayer>[
      for (final entry in loadout.equipped.entries)
        _PreviewLayer(slot: entry.key, asset: catalog.asset(entry.value)),
      _PreviewLayer(asset: avatar),
    ]..sort((a, b) => a.asset.zIndex.compareTo(b.asset.zIndex));
    return SizedBox.square(
      dimension: size,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          for (final layer in layers) _AvatarLayer(layer: layer, size: size),
        ],
      ),
    );
  }
}

class _PreviewLayer {
  final AvatarSlot? slot;
  final AvatarCatalogAsset asset;

  const _PreviewLayer({
    this.slot,
    required this.asset,
  });
}

class _AvatarLayer extends StatelessWidget {
  final _PreviewLayer layer;
  final double size;

  const _AvatarLayer({
    required this.layer,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    final asset = layer.asset;
    final anchorX = ((asset.anchor['x'] ?? 256) / 512.0) * size;
    final anchorY = ((asset.anchor['y'] ?? 256) / 512.0) * size;
    final layerSize = size * asset.scale;
    final isSideAsset = asset.slotType == 'side';

    if (!isSideAsset || asset is AvatarAsset) {
      return Positioned.fill(
        child: Image.asset(asset.assetPath, fit: BoxFit.contain),
      );
    }

    final slotAnchor = switch (layer.slot) {
      AvatarSlot.sideLeft1 => const Offset(0.22, 0.48),
      AvatarSlot.sideLeft2 => const Offset(0.24, 0.74),
      AvatarSlot.sideRight1 => const Offset(0.78, 0.48),
      AvatarSlot.sideRight2 => const Offset(0.76, 0.74),
      _ => Offset(anchorX / size, anchorY / size),
    };

    return Positioned(
      left: slotAnchor.dx * size - layerSize / 2,
      top: slotAnchor.dy * size - layerSize / 2,
      width: layerSize,
      height: layerSize,
      child: Image.asset(asset.assetPath, fit: BoxFit.contain),
    );
  }
}
