import '../entities/property.dart';
import '../repositories/property_repository.dart';

class GetProperties {
  final PropertyRepository repository;

  GetProperties(this.repository);

  Future<List<Property>> call({
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
    return repository.getProperties(
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
