import '../entities/property.dart';
import '../repositories/property_repository.dart';

class SearchProperties {
  final PropertyRepository repository;

  SearchProperties(this.repository);

  Future<List<Property>> call(
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
    return repository.searchProperties(
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
