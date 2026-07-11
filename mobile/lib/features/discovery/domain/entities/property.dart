class Property {
  final int id;
  final String name;
  final String city;
  final String country;
  final String address;
  final String currency;
  final String phone;
  final String email;
  final String? logo;
  final double? minPrice;
  final double? maxPrice;
  final int availableUnitCount;
  final double averageRating;
  final int totalReviews;
  final double? latitude;
  final double? longitude;
  final String videoUrl;
  final String virtualTourUrl;
  final List<Map<String, dynamic>> mediaGallery;

  Property({
    required this.id,
    required this.name,
    required this.city,
    required this.country,
    required this.address,
    required this.currency,
    required this.phone,
    required this.email,
    required this.logo,
    required this.minPrice,
    required this.maxPrice,
    required this.availableUnitCount,
    required this.averageRating,
    required this.totalReviews,
    required this.latitude,
    required this.longitude,
    required this.videoUrl,
    required this.virtualTourUrl,
    required this.mediaGallery,
  });
}
