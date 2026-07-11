import '../../domain/entities/property.dart';
import '../../domain/repositories/property_repository.dart';
import '../datasources/property_api.dart';

class PropertyRepositoryImpl implements PropertyRepository {
  final PropertyApi api;

  PropertyRepositoryImpl(this.api);

  @override
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
  }) {
    return api.getProperties(
      country: country,
      city: city,
      businessType: businessType,
      lifestyle: lifestyle,
      amenities: amenities,
      guests: guests,
      minPrice: minPrice,
      maxPrice: maxPrice,
      minRating: minRating,
    );
  }

  @override
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
  }) {
    return api.searchProperties(
      query,
      country: country,
      city: city,
      businessType: businessType,
      lifestyle: lifestyle,
      amenities: amenities,
      guests: guests,
      minPrice: minPrice,
      maxPrice: maxPrice,
      minRating: minRating,
    );
  }
}
