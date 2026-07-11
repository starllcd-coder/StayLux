import '../entities/review.dart';
import '../repositories/review_repository.dart';

class GetReviews {
  final ReviewRepository repository;

  GetReviews(this.repository);

  Future<List<Review>> call(int propertyId) {
    return repository.getReviews(propertyId);
  }
}