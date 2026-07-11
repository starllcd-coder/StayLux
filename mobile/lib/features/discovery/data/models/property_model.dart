import '../../../../core/utils/gcc_region.dart';
import '../../domain/entities/property.dart';

class PropertyModel extends Property {
  PropertyModel({
    required super.id,
    required super.name,
    required super.city,
    required super.country,
    required super.address,
    required super.currency,
    required super.phone,
    required super.email,
    required super.logo,
    required super.minPrice,
    required super.maxPrice,
    required super.availableUnitCount,
    required super.averageRating,
    required super.totalReviews,
    required super.latitude,
    required super.longitude,
    required super.videoUrl,
    required super.virtualTourUrl,
    required super.mediaGallery,
  });

  factory PropertyModel.fromJson(Map<String, dynamic> json) {
    return PropertyModel(
      id: _toInt(json["id"]),
      name: (json["display_name"] ?? json["name_en"] ?? "").toString(),
      city: (json["city"] ?? "").toString(),
      country: (json["country"] ?? "").toString(),
      address: (json["display_address"] ?? "").toString(),
      currency: (json["currency"] ?? currencyForCountry((json["country"] ?? "").toString())).toString(),
      phone: (json["phone"] ?? "").toString(),
      email: (json["email"] ?? "").toString(),
      logo: json["logo"]?.toString(),
      minPrice: _toDouble(json["min_price"]),
      maxPrice: _toDouble(json["max_price"]),
      availableUnitCount: _toInt(json["available_unit_count"]),
      averageRating: _toDouble(json["average_rating"]) ?? 0,
      totalReviews: _toInt(json["total_reviews"]),
      latitude: _toDouble(json["latitude"]),
      longitude: _toDouble(json["longitude"]),
      videoUrl: (json["video_url"] ?? "").toString(),
      virtualTourUrl: (json["virtual_tour_url"] ?? "").toString(),
      mediaGallery: _toMapList(json["media_gallery"]),
    );
  }

  static int _toInt(dynamic value) {
    if (value == null) return 0;
    if (value is int) return value;
    return int.tryParse(value.toString()) ?? 0;
  }

  static double? _toDouble(dynamic value) {
    if (value == null) return null;
    return double.tryParse(value.toString());
  }

  static List<Map<String, dynamic>> _toMapList(dynamic value) {
    if (value is! List) return const [];
    return value.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  }
}
