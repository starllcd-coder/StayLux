import '../entities/wishlist.dart';
import '../repositories/wishlist_repository.dart';

class GetWishlist {
  final WishlistRepository repository;

  GetWishlist(this.repository);

  Future<List<WishlistItem>> call() {
    return repository.getWishlist();
  }
}