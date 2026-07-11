import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/review_api.dart';
import '../../data/repositories/review_repository_impl.dart';
import '../../domain/entities/review.dart';
import '../../domain/usecases/create_review.dart';
import '../../domain/usecases/get_reviews.dart';

class ReviewState {
  final bool isLoading;
  final bool isSubmitting;
  final List<Review> reviews;
  final String? error;

  const ReviewState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.reviews = const [],
    this.error,
  });

  ReviewState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    List<Review>? reviews,
    String? error,
    bool clearError = false,
  }) {
    return ReviewState(
      isLoading: isLoading ?? this.isLoading,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      reviews: reviews ?? this.reviews,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final reviewControllerProvider =
    StateNotifierProvider<ReviewController, ReviewState>((ref) {
  return ReviewController();
});

class ReviewController extends StateNotifier<ReviewState> {
  ReviewController() : super(const ReviewState());

  final _repository = ReviewRepositoryImpl(ReviewApi(ApiClient()));

  Future<void> load(int propertyId) async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
    );

    try {
      final reviews = await GetReviews(_repository).call(propertyId);
      state = state.copyWith(
        isLoading: false,
        reviews: reviews,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<bool> create({
    required int propertyId,
    required int rating,
    required String title,
    required String comment,
  }) async {
    state = state.copyWith(
      isSubmitting: true,
      clearError: true,
    );

    try {
      await CreateReview(_repository).call(
        propertyId: propertyId,
        rating: rating,
        title: title,
        comment: comment,
      );

      final reviews = await GetReviews(_repository).call(propertyId);

      state = state.copyWith(
        isSubmitting: false,
        reviews: reviews,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      return false;
    }
  }
}