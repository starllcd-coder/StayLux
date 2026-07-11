import '../entities/review.dart';
import '../repositories/review_repository.dart';

class CreateReview {
  final ReviewRepository repository;

  CreateReview(this.repository);

  Future<Review> call({
    required int propertyId,
    required int rating,
    required String title,
    required String comment,
  }) {
    return repository.createReview(
      propertyId: propertyId,
      rating: rating,
      title: title,
      comment: comment,
    );
  }
}