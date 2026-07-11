import '../../../../core/network/api_client.dart';
import '../models/review_model.dart';

class ReviewApi {
  final ApiClient client;

  ReviewApi(this.client);

  Future<List<ReviewModel>> getReviews(int propertyId) async {
    final response = await client.get("/reviews/property/$propertyId/");
    final List results = (response.data["results"] ?? response.data) as List;

    return results
        .map((item) => ReviewModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<ReviewModel> createReview({
    required int propertyId,
    required int rating,
    required String title,
    required String comment,
  }) async {
    final response = await client.post(
      "/reviews/create/",
      {
        "property_profile": propertyId,
        "rating": rating,
        "title": title,
        "comment": comment,
      },
    );

    return ReviewModel.fromJson(response.data as Map<String, dynamic>);
  }
}