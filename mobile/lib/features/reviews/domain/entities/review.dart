class Review {
  final int id;
  final String customerName;
  final int propertyId;
  final int rating;
  final String title;
  final String comment;
  final String createdAt;

  Review({
    required this.id,
    required this.customerName,
    required this.propertyId,
    required this.rating,
    required this.title,
    required this.comment,
    required this.createdAt,
  });
}