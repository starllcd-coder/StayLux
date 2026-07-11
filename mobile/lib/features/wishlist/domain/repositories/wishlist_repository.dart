import '../entities/wishlist.dart';

abstract class WishlistRepository {
  Future<List<WishlistItem>> getWishlist();
  Future<bool> toggleWishlist(int propertyId, {int? collectionId});
}
