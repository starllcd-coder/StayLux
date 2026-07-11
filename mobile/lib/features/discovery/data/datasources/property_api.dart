import '../../../../core/network/api_client.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/storage/secure_storage_service.dart';
import 'dart:convert';
import '../models/property_model.dart';

class PropertyApi {
  final ApiClient client;
  final SecureStorageService storage = SecureStorageService();

  PropertyApi(this.client);

  String _buildQuery({
    String q = "",
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
    final params = <String, String>{};
    if (q.trim().isNotEmpty) params["q"] = q.trim();
    if (country.trim().isNotEmpty) params["country"] = country.trim();
    if (city.trim().isNotEmpty) params["city"] = city.trim();
    if (businessType.trim().isNotEmpty) params["business_type"] = businessType.trim();
    if (lifestyle.trim().isNotEmpty) params["lifestyle"] = lifestyle.trim();
    if (amenities.trim().isNotEmpty) params["amenities"] = amenities.trim();
    if (guests != null && guests > 0) params["guests"] = guests.toString();
    if (minPrice != null && minPrice > 0) params["min_price"] = minPrice.toStringAsFixed(0);
    if (maxPrice != null && maxPrice > 0) params["max_price"] = maxPrice.toStringAsFixed(0);
    if (minRating != null && minRating > 0) params["min_rating"] = minRating.toStringAsFixed(1);
    if (params.isEmpty) return "";
    return "?${Uri(queryParameters: params).query}";
  }

  Future<List<PropertyModel>> getProperties({
    String country = "",
    String city = "",
    String businessType = "",
    String lifestyle = "",
    String amenities = "",
    int? guests,
    double? minPrice,
    double? maxPrice,
    double? minRating,
  }) async {
    final query = _buildQuery(
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
    try {
      final response = await client.get("/discovery/properties/$query");
      final data = response.data;

      final List results;
      if (data is Map<String, dynamic>) {
        results = (data["results"] ?? []) as List;
      } else if (data is List) {
        results = data;
      } else {
        results = [];
      }

      await storage.saveString(AppConstants.cacheDiscoveryKey, jsonEncode(results));
      return results
          .map((item) => PropertyModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (_) {
      final raw = await storage.getString(AppConstants.cacheDiscoveryKey);
      if (raw != null && raw.trim().isNotEmpty) {
        final data = jsonDecode(raw);
        if (data is List) {
          return data
              .whereType<Map>()
              .map((item) => PropertyModel.fromJson(Map<String, dynamic>.from(item)))
              .toList();
        }
      }
      rethrow;
    }
  }

  Future<List<PropertyModel>> searchProperties(
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
  }) async {
    final extraQuery = _buildQuery(
      q: query,
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
    final response = await client.get("/discovery/properties/search/$extraQuery");
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

  Future<List<String>> getSearchSuggestions(String query) async {
    final q = query.trim();
    if (q.length < 2) return const [];
    final encoded = Uri.encodeQueryComponent(q);
    final response = await client.get("/discovery/properties/suggestions/?q=$encoded&limit=8");
    final data = response.data;
    final List raw;
    if (data is Map<String, dynamic>) {
      raw = (data["results"] ?? []) as List;
    } else if (data is List) {
      raw = data;
    } else {
      raw = [];
    }
    return raw.map((e) => e.toString()).where((e) => e.trim().isNotEmpty).toList();
  }

  Future<List<PropertyModel>> getRecommendedProperties({
    String city = "",
    String country = "",
  }) async {
    final params = <String, String>{};
    if (city.trim().isNotEmpty) params["city"] = city.trim();
    if (country.trim().isNotEmpty) params["country"] = country.trim();
    final query = params.isEmpty ? "" : "?${Uri(queryParameters: params).query}";
    final response = await client.get("/discovery/properties/recommended/$query");
    final data = response.data;
    final List results;
    if (data is Map<String, dynamic>) {
      final raw = data["results"];
      results = raw is List ? raw : <dynamic>[];
    } else if (data is List) {
      results = data;
    } else {
      results = <dynamic>[];
    }
    return results
        .whereType<Map>()
        .map((item) => PropertyModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }
}
