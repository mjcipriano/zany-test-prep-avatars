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
    if (asset is AvatarAsset) {
      return Positioned.fill(
        child: Image.asset(asset.assetPath, fit: BoxFit.contain),
      );
    }

    final target = asset.placement.targetFor(layer.slot);
    final targetWidth = target.width * asset.scale * size;
    final targetHeight = target.height * asset.scale * size;
    final left = target.cx * size - targetWidth / 2;
    final top = target.cy * size - targetHeight / 2;

    return Positioned(
      left: left,
      top: top,
      width: targetWidth,
      height: targetHeight,
      child: Image.asset(asset.assetPath, fit: BoxFit.contain),
    );
  }
}
