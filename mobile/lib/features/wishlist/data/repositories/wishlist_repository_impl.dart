import '../../domain/entities/wishlist.dart';
import '../../domain/repositories/wishlist_repository.dart';
import '../datasources/wishlist_api.dart';

class WishlistRepositoryImpl implements WishlistRepository {
  final WishlistApi api;

  WishlistRepositoryImpl(this.api);

  @override
  Future<List<WishlistItem>> getWishlist() {
    return api.getWishlist();
  }

  @override
  Future<bool> toggleWishlist(int propertyId, {int? collectionId}) {
    return api.toggleWishlist(propertyId, collectionId: collectionId);
  }
}
