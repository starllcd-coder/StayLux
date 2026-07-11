import '../../domain/entities/review.dart';
import '../../domain/repositories/review_repository.dart';
import '../datasources/review_api.dart';

class ReviewRepositoryImpl implements ReviewRepository {
  final ReviewApi api;

  ReviewRepositoryImpl(this.api);

  @override
  Future<List<Review>> getReviews(int propertyId) {
    return api.getReviews(propertyId);
  }

  @override
  Future<Review> createReview({
    required int propertyId,
    required int rating,
    required String title,
    required String comment,
  }) {
    return api.createReview(
      propertyId: propertyId,
      rating: rating,
      title: title,
      comment: comment,
    );
  }
}