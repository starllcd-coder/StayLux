import '../../../discovery/domain/entities/property.dart';
import '../../domain/entities/unit.dart';
import '../../domain/repositories/property_details_repository.dart';
import '../datasources/property_details_api.dart';

class PropertyDetailsRepositoryImpl implements PropertyDetailsRepository {
  final PropertyDetailsApi api;

  PropertyDetailsRepositoryImpl(this.api);

  @override
  Future<Property> getPropertyDetails(int propertyId) {
    return api.getPropertyDetails(propertyId);
  }

  @override
  Future<List<Unit>> getPropertyUnits(int propertyId) {
    return api.getPropertyUnits(propertyId);
  }

  @override
  Future<List<Property>> getSimilarProperties(int propertyId) {
    return api.getSimilarProperties(propertyId);
  }
}
