import '../../../discovery/domain/entities/property.dart';
import '../entities/unit.dart';
import '../repositories/property_details_repository.dart';

class GetPropertyDetails {
  final PropertyDetailsRepository repository;

  GetPropertyDetails(this.repository);

  Future<Property> property(int propertyId) {
    return repository.getPropertyDetails(propertyId);
  }

  Future<List<Unit>> units(int propertyId) {
    return repository.getPropertyUnits(propertyId);
  }

  Future<List<Property>> similar(int propertyId) {
    return repository.getSimilarProperties(propertyId);
  }
}
