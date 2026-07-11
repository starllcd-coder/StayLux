import '../entities/review.dart';

abstract class ReviewRepository {
  Future<List<Review>> getReviews(int propertyId);

  Future<Review> createReview({
    required int propertyId,
    required int rating,
    required String title,
    required String comment,
  });
}