import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/wishlist_api.dart';
import '../../data/repositories/wishlist_repository_impl.dart';
import '../../domain/entities/wishlist.dart';
import '../../domain/usecases/get_wishlist.dart';
import '../../domain/usecases/toggle_wishlist.dart';

class WishlistState {
  final bool isLoading;
  final List<WishlistItem> items;
  final List<Map<String, dynamic>> collections;
  final String? error;

  const WishlistState({
    this.isLoading = false,
    this.items = const [],
    this.collections = const [],
    this.error,
  });

  WishlistState copyWith({
    bool? isLoading,
    List<WishlistItem>? items,
    List<Map<String, dynamic>>? collections,
    String? error,
    bool clearError = false,
  }) {
    return WishlistState(
      isLoading: isLoading ?? this.isLoading,
      items: items ?? this.items,
      collections: collections ?? this.collections,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final wishlistControllerProvider =
    StateNotifierProvider<WishlistController, WishlistState>((ref) {
  return WishlistController();
});

class WishlistController extends StateNotifier<WishlistState> {
  WishlistController() : super(const WishlistState());

  final _repository = WishlistRepositoryImpl(WishlistApi(ApiClient()));

  Future<void> load() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _repository.api.flushPendingWishlistOps();
      final items = await GetWishlist(_repository).call();
      final collections = await _repository.api.getCollections();
      state = state.copyWith(
        isLoading: false,
        items: items,
        collections: collections,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> toggle(int propertyId, {int? collectionId}) async {
    state = state.copyWith(clearError: true);
    try {
      await ToggleWishlist(_repository).call(propertyId, collectionId: collectionId);
      await load();
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<Map<String, dynamic>> createCollection(String name, {bool isPublic = false}) async {
    final created = await _repository.api.createCollection(name, isPublic: isPublic);
    await load();
    return created;
  }

  Future<Map<String, dynamic>> shareCollection(int id) async {
    return _repository.api.shareCollection(id);
  }

  Future<void> setPriceAlert(int itemId, {required bool enabled, double? targetPrice}) async {
    await _repository.api.setPriceAlert(itemId, enabled: enabled, targetPrice: targetPrice);
    await load();
  }

  bool containsProperty(int propertyId) {
    return state.items.any((item) => item.propertyId == propertyId);
  }
}
