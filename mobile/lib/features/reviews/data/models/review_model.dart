import '../../domain/entities/review.dart';

class ReviewModel extends Review {
  ReviewModel({
    required super.id,
    required super.customerName,
    required super.propertyId,
    required super.rating,
    required super.title,
    required super.comment,
    required super.createdAt,
  });

  factory ReviewModel.fromJson(Map<String, dynamic> json) {
    return ReviewModel(
      id: json["id"] ?? 0,
      customerName: (json["customer_name"] ?? "").toString(),
      propertyId: json["property_profile"] ?? 0,
      rating: json["rating"] ?? 0,
      title: (json["title"] ?? "").toString(),
      comment: (json["comment"] ?? "").toString(),
      createdAt: (json["created_at"] ?? "").toString(),
    );
  }
}