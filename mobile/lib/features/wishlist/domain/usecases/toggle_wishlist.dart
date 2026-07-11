import '../repositories/wishlist_repository.dart';

class ToggleWishlist {
  final WishlistRepository repository;

  ToggleWishlist(this.repository);

  Future<bool> call(int propertyId, {int? collectionId}) {
    return repository.toggleWishlist(propertyId, collectionId: collectionId);
  }
}
