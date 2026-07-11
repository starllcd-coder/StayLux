import '../../domain/entities/wishlist.dart';

class WishlistItemModel extends WishlistItem {
  WishlistItemModel({
    required super.id,
    required super.propertyId,
    required super.propertyName,
    required super.collectionId,
    required super.collectionName,
    required super.priceAlertEnabled,
    required super.targetPrice,
    required super.lastKnownPrice,
  });

  factory WishlistItemModel.fromJson(Map<String, dynamic> json) {
    return WishlistItemModel(
      id: json["id"] ?? 0,
      propertyId: json["property_id"] ?? 0,
      propertyName: (json["property_name"] ?? "").toString(),
      collectionId: json["collection"] == null ? null : int.tryParse(json["collection"].toString()),
      collectionName: (json["collection_name"] ?? "").toString(),
      priceAlertEnabled: json["price_alert_enabled"] == true,
      targetPrice: double.tryParse((json["target_price"] ?? "").toString()),
      lastKnownPrice: double.tryParse((json["last_known_price"] ?? "").toString()),
    );
  }
}
