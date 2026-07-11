import '../../../../core/network/api_client.dart';
import '../../../discovery/data/models/property_model.dart';
import '../models/unit_model.dart';

class PropertyDetailsApi {
  final ApiClient client;

  PropertyDetailsApi(this.client);

  Future<PropertyModel> getPropertyDetails(int propertyId) async {
    final response = await client.get("/discovery/properties/$propertyId/");
    return PropertyModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<UnitModel>> getPropertyUnits(int propertyId) async {
    final response = await client.get("/discovery/properties/$propertyId/units/");
    final data = response.data;

    final List results;
    if (data is Map<String, dynamic>) {
      results = (data["results"] ?? []) as List;
    } else if (data is List) {
      results = data;
    } else {
      results = [];
    }

    return results
        .map((item) => UnitModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<PropertyModel>> getSimilarProperties(int propertyId) async {
    final response = await client.get("/discovery/properties/$propertyId/similar/");
    final data = response.data;

    final List results;
    if (data is Map<String, dynamic>) {
      results = (data["results"] ?? []) as List;
    } else if (data is List) {
      results = data;
    } else {
      results = [];
    }

    return results
        .map((item) => PropertyModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
