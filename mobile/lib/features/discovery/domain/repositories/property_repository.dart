import '../entities/property.dart';

abstract class PropertyRepository {
  Future<List<Property>> getProperties({
    String country = "",
    String city = "",
    String businessType = "",
    String lifestyle = "",
    String amenities = "",
    int? guests,
    double? minPrice,
    double? maxPrice,
    double? minRating,
  });

  Future<List<Property>> searchProperties(
    String query, {
    String country = "",
    String city = "",
    String businessType = "",
    String lifestyle = "",
    String amenities = "",
    int? guests,
    double? minPrice,
    double? maxPrice,
    double? minRating,
  });
}
