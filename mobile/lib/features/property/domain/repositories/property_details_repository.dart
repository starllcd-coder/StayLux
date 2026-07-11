import '../../../discovery/domain/entities/property.dart';
import '../entities/unit.dart';

abstract class PropertyDetailsRepository {
  Future<Property> getPropertyDetails(int propertyId);
  Future<List<Unit>> getPropertyUnits(int propertyId);
  Future<List<Property>> getSimilarProperties(int propertyId);
}
