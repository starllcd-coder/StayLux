class WishlistItem {
  final int id;
  final int propertyId;
  final String propertyName;
  final int? collectionId;
  final String collectionName;
  final bool priceAlertEnabled;
  final double? targetPrice;
  final double? lastKnownPrice;

  WishlistItem({
    required this.id,
    required this.propertyId,
    required this.propertyName,
    required this.collectionId,
    required this.collectionName,
    required this.priceAlertEnabled,
    required this.targetPrice,
    required this.lastKnownPrice,
  });
}
