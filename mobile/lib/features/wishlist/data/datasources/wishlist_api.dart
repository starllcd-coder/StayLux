import '../../../../core/network/api_client.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/storage/secure_storage_service.dart';
import 'dart:convert';
import '../models/wishlist_model.dart';

class WishlistApi {
  final ApiClient client;
  final SecureStorageService storage = SecureStorageService();

  WishlistApi(this.client);

  Future<List<WishlistItemModel>> getWishlist() async {
    try {
      final response = await client.get("/wishlist/");
      final List results = response.data as List;
      await storage.saveString(AppConstants.cacheWishlistKey, jsonEncode(results));
      return results
          .map((item) => WishlistItemModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (_) {
      final raw = await storage.getString(AppConstants.cacheWishlistKey);
      if (raw != null && raw.trim().isNotEmpty) {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          return decoded
              .whereType<Map>()
              .map((item) => WishlistItemModel.fromJson(Map<String, dynamic>.from(item)))
              .toList();
        }
      }
      rethrow;
    }
  }

  Future<bool> toggleWishlist(int propertyId, {int? collectionId}) async {
    final payload = <String, dynamic>{"property_id": propertyId};
    if (collectionId != null) payload["collection_id"] = collectionId;
    try {
      final response = await client.post(
        "/wishlist/toggle/",
        payload,
      );

      if (response.data["added"] == true) return true;
      if (response.data["removed"] == true) return false;
      return false;
    } catch (_) {
      await _enqueueWishlistOp(payload);
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> getCollections() async {
    final response = await client.get("/wishlist/collections/");
    final data = response.data;
    if (data is List) {
      return data.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    return const [];
  }

  Future<Map<String, dynamic>> createCollection(String name, {bool isPublic = false}) async {
    final response = await client.post(
      "/wishlist/collections/",
      {"name": name, "is_public": isPublic},
    );
    final data = response.data;
    if (data is Map<String, dynamic>) {
      return data;
    }
    return const {};
  }

  Future<Map<String, dynamic>> shareCollection(int id) async {
    final response = await client.post("/wishlist/collections/$id/share/", {});
    final data = response.data;
    if (data is Map<String, dynamic>) {
      return data;
    }
    return const {};
  }

  Future<Map<String, dynamic>> setPriceAlert(int itemId, {required bool enabled, double? targetPrice}) async {
    final payload = <String, dynamic>{"enabled": enabled};
    if (targetPrice != null) payload["target_price"] = targetPrice.toStringAsFixed(3);
    final response = await client.post("/wishlist/$itemId/price-alert/", payload);
    final data = response.data;
    if (data is Map<String, dynamic>) {
      return data;
    }
    return const {};
  }

  Future<void> flushPendingWishlistOps() async {
    final raw = await storage.getString(AppConstants.wishlistOpsQueueKey);
    if (raw == null || raw.trim().isEmpty) return;
    final decoded = jsonDecode(raw);
    if (decoded is! List) return;
    final remaining = <Map<String, dynamic>>[];
    for (final op in decoded) {
      if (op is! Map) continue;
      try {
        await client.post("/wishlist/toggle/", Map<String, dynamic>.from(op));
      } catch (_) {
        remaining.add(Map<String, dynamic>.from(op));
      }
    }
    await storage.saveString(AppConstants.wishlistOpsQueueKey, jsonEncode(remaining));
  }

  Future<void> _enqueueWishlistOp(Map<String, dynamic> payload) async {
    final raw = await storage.getString(AppConstants.wishlistOpsQueueKey);
    List<dynamic> items = [];
    if (raw != null && raw.trim().isNotEmpty) {
      final decoded = jsonDecode(raw);
      if (decoded is List) items = decoded;
    }
    items.add(payload);
    await storage.saveString(AppConstants.wishlistOpsQueueKey, jsonEncode(items));
  }
}
